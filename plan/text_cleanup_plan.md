# Text Cleanup/Sanitization - Implementation Plan

This document provides a detailed step-by-step guide to add text cleanup/disfluency removal. For architecture and specifications, see `../spec/spec.md#module-6-text_cleanuppy`.

---

## Overview

**Goal:** Remove speech disfluencies (um, uh, false starts, repetitions) from transcriptions before output.

**Problem:**
Natural speech contains disfluencies that degrade written output:
- "Hey, um, can you... sorry, can you send this?" → "Can you send this?"
- "I I think we should" → "I think we should"

**Approach:** Create a `TextCleaner` class with configurable cleanup modes (off, light, standard, aggressive) that sits between transcription and output in the pipeline.

---

## Master Todo Checklist

### Phase 1: Core Module
- [x] 1.1 Add `TextCleanupError` to `exceptions.py`
- [x] 1.2 Create `text_cleanup.py` with `CleanupMode` enum
- [x] 1.3 Implement `TextCleaner.__init__()` with mode selection
- [x] 1.4 Implement `clean_light()` - remove obvious fillers
- [x] 1.5 Implement `clean_standard()` - fillers + repetitions + false starts
- [x] 1.6 Implement `clean_aggressive()` - LLM-based cleanup
- [x] 1.7 Implement main `clean()` method with mode dispatch
- [x] 1.8 Add helper methods for context-aware rules

### Phase 2: Configuration
- [x] 2.1 Add `VALID_CLEANUP_MODES` to `config.py`
- [x] 2.2 Add `text_cleanup` field to `Config` dataclass
- [x] 2.3 Add `preserve_intentional` field to `Config` dataclass
- [x] 2.4 Update `Config.from_env()` to load new options
- [x] 2.5 Update `Config.validate()` with cleanup mode validation
- [x] 2.6 Update `.env.example` with new environment variables

### Phase 3: Integration
- [x] 3.1 Add `TextCleaner` import to `main.py`
- [x] 3.2 Create `get_text_cleaner()` factory function
- [x] 3.3 Initialize `TextCleaner` in `HandFreeApp.__init__()`
- [x] 3.4 Integrate cleanup in `handle_stop()` after transcription
- [x] 3.5 Add cleanup mode to startup banner
- [x] 3.6 Update `__init__.py` exports

### Phase 4: Testing
- [x] 4.1 Create `tests/test_text_cleanup.py`
- [x] 4.2 Write unit tests for `clean_light()`
- [x] 4.3 Write unit tests for `clean_standard()`
- [x] 4.4 Write edge case tests
- [x] 4.5 Write property-based tests with Hypothesis
- [x] 4.6 Add integration test for end-to-end flow

### Phase 5: Verification
- [x] 5.1 Run all tests: `pytest tests/test_text_cleanup.py -v`
- [x] 5.2 Manual test with `HANDFREE_TEXT_CLEANUP=off`
- [x] 5.3 Manual test with `HANDFREE_TEXT_CLEANUP=light`
- [x] 5.4 Manual test with `HANDFREE_TEXT_CLEANUP=standard`
- [x] 5.5 Performance benchmark (<5ms for standard mode)
- [x] 5.6 End-to-end test with real speech

---

## Detailed Implementation

---

## Phase 1: Core Module

### Step 1.1: Add TextCleanupError

**File:** `src/handfree/exceptions.py`

Add after `OutputHandlerError`:

```python
class TextCleanupError(HandFreeError):
    """Error cleaning transcribed text."""
    pass
```

### Step 1.2: Create text_cleanup.py

**File:** `src/handfree/text_cleanup.py`

```python
"""
Text Cleanup Module
Removes speech disfluencies from transcribed text.
"""

import re
from enum import Enum, auto
from typing import Optional, Set, List

from handfree.exceptions import TextCleanupError


class CleanupMode(Enum):
    """Text cleanup aggressiveness levels."""
    OFF = auto()        # No cleanup
    LIGHT = auto()      # Only obvious fillers (um, uh, ah)
    STANDARD = auto()   # Fillers + repetitions + false starts
    AGGRESSIVE = auto() # LLM-powered cleanup (requires API)
```

### Step 1.3: Implement TextCleaner.__init__()

```python
class TextCleaner:
    """
    Cleans speech disfluencies from transcribed text.

    Pipeline: Transcriber → TextCleaner → OutputHandler
    """

    # Filler words for light mode
    FILLERS_LIGHT: Set[str] = {
        "um", "uh", "ah", "er", "hmm", "mm", "mhm",
    }

    # Additional fillers for standard mode
    FILLERS_STANDARD: Set[str] = FILLERS_LIGHT | {
        "like", "you know", "i mean", "so", "basically",
        "actually", "literally", "right", "okay", "well",
        "anyway", "you see", "kind of", "sort of",
    }

    # Markers indicating false starts
    CORRECTION_MARKERS: List[str] = [
        "sorry", "i mean", "no wait", "actually",
        "let me rephrase", "correction", "rather",
    ]

    def __init__(
        self,
        mode: CleanupMode = CleanupMode.STANDARD,
        api_key: Optional[str] = None,
        preserve_intentional: bool = True,
    ):
        """
        Initialize text cleaner.

        Args:
            mode: Cleanup aggressiveness level
            api_key: Groq API key (required for AGGRESSIVE mode)
            preserve_intentional: Preserve intentional patterns
        """
        self.mode = mode
        self.api_key = api_key
        self.preserve_intentional = preserve_intentional

        # Pre-compile regex patterns for performance
        self._compile_patterns()
```

### Step 1.4: Implement clean_light()

```python
def clean_light(self, text: str) -> str:
    """Remove only obvious filler words (um, uh, ah)."""
    if not text:
        return text

    result = text

    # Remove standalone fillers with word boundaries
    for filler in sorted(self.FILLERS_LIGHT, key=len, reverse=True):
        pattern = rf'\b{re.escape(filler)}\b,?\s*'
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)

    return self._normalize_whitespace(result)
```

### Step 1.5: Implement clean_standard()

```python
def clean_standard(self, text: str) -> str:
    """Remove fillers, repetitions, and false starts."""
    if not text:
        return text

    result = text

    # Step 1: Remove false starts (text before correction markers)
    result = self._remove_false_starts(result)

    # Step 2: Remove filler words/phrases (context-aware)
    result = self._remove_fillers(result)

    # Step 3: Remove word repetitions
    result = self._remove_repetitions(result)

    # Step 4: Clean up orphaned ellipses
    result = self._clean_ellipses(result)

    return self._normalize_whitespace(result)
```

### Step 1.6: Implement clean_aggressive()

```python
LLM_PROMPT = """Clean this speech transcription by removing disfluencies.

Remove: filler words (um, uh, like, you know), false starts, repetitions, incomplete sentences before corrections.
Preserve: core meaning, natural tone, intentional emphasis.

Input: {text}

Output only the cleaned text, nothing else:"""

def clean_aggressive(self, text: str) -> str:
    """Use LLM for intelligent cleanup."""
    if not text:
        return text

    if not self.api_key:
        # Fall back to standard if no API key
        return self.clean_standard(text)

    try:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": self.LLM_PROMPT.format(text=text)}
            ],
            max_tokens=len(text) * 2,
            temperature=0.1,
        )

        cleaned = response.choices[0].message.content.strip()

        # Sanity check: if too much removed, fall back
        if len(cleaned) < len(text) * 0.3:
            return self.clean_standard(text)

        return cleaned

    except Exception as e:
        import logging
        logging.warning(f"LLM cleanup failed, using rule-based: {e}")
        return self.clean_standard(text)
```

### Step 1.7: Implement main clean() method

```python
def clean(self, text: str) -> str:
    """
    Clean speech disfluencies from text.

    Args:
        text: Raw transcription text

    Returns:
        Cleaned text with disfluencies removed
    """
    if self.mode == CleanupMode.OFF:
        return text
    elif self.mode == CleanupMode.LIGHT:
        return self.clean_light(text)
    elif self.mode == CleanupMode.STANDARD:
        return self.clean_standard(text)
    elif self.mode == CleanupMode.AGGRESSIVE:
        return self.clean_aggressive(text)
    else:
        return text
```

### Step 1.8: Add helper methods

```python
def _compile_patterns(self) -> None:
    """Pre-compile regex patterns for performance."""
    self._repetition_pattern = re.compile(
        r'\b(\w+)(?:\s+\1){1,3}\b',
        re.IGNORECASE
    )
    self._ellipsis_pattern = re.compile(r'\.{2,}')

def _remove_false_starts(self, text: str) -> str:
    """Remove text before correction markers."""
    result = text

    for marker in self.CORRECTION_MARKERS:
        # Pattern: "X... sorry, Y" -> "Y"
        pattern = rf'[^.!?]*?\.\.\.\s*{re.escape(marker)},?\s*'
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # Pattern: "X, sorry, X" (where X repeats) -> "X"
        pattern = rf'([^,]+),\s*{re.escape(marker)},?\s*\1'
        result = re.sub(pattern, r'\1', result, flags=re.IGNORECASE)

    return result

def _remove_fillers(self, text: str) -> str:
    """Remove filler words with context awareness."""
    result = text

    for filler in sorted(self.FILLERS_STANDARD, key=len, reverse=True):
        if self.preserve_intentional and filler == "like":
            # Preserve "like" as verb: "I like pizza"
            # Remove "like" as filler: "It's like really good"
            pattern = rf'(?<!\bI\s)\b{re.escape(filler)}\b(?!\s+(?:to|the|a|my|your|this|that|it\b))'
            result = re.sub(pattern + r',?\s*', '', result, flags=re.IGNORECASE)
        else:
            pattern = rf'\b{re.escape(filler)}\b,?\s*'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

    return result

def _remove_repetitions(self, text: str) -> str:
    """Remove consecutive word repetitions."""
    if self.preserve_intentional:
        # Preserve emphasis: "very very important"
        emphasis_words = {'very', 'really', 'so', 'much', 'too', 'super'}

        def replace_repetition(match):
            word = match.group(1).lower()
            if word in emphasis_words:
                return match.group(0)  # Keep intentional emphasis
            return match.group(1)  # Remove stutter

        return self._repetition_pattern.sub(replace_repetition, text)
    else:
        return self._repetition_pattern.sub(r'\1', text)

def _clean_ellipses(self, text: str) -> str:
    """Clean up orphaned ellipses."""
    result = re.sub(r'^\s*\.{2,}\s*', '', text)
    result = re.sub(r'\.\s+\.{2,}\s*', '. ', result)
    return result

def _normalize_whitespace(self, text: str) -> str:
    """Normalize whitespace and punctuation."""
    result = re.sub(r' +', ' ', text)
    result = re.sub(r'\s+([.,!?])', r'\1', result)
    return result.strip()
```

---

## Phase 2: Configuration

### Step 2.1-2.5: Update config.py

**File:** `src/handfree/config.py`

Add after `VALID_WHISPER_MODELS`:

```python
# Valid text cleanup modes
VALID_CLEANUP_MODES = ["off", "light", "standard", "aggressive"]
```

Add fields to `Config` dataclass:

```python
@dataclass
class Config:
    # ... existing fields ...

    # Text cleanup settings
    text_cleanup: str = "standard"  # off, light, standard, aggressive
    preserve_intentional: bool = True
```

Update `from_env()`:

```python
return cls(
    # ... existing fields ...
    text_cleanup=os.environ.get("HANDFREE_TEXT_CLEANUP", "standard").lower(),
    preserve_intentional=parse_bool(os.environ.get("HANDFREE_PRESERVE_INTENTIONAL", "true"), True),
)
```

Update `validate()`:

```python
# Validate text cleanup mode
if self.text_cleanup not in VALID_CLEANUP_MODES:
    raise ValueError(
        f"HANDFREE_TEXT_CLEANUP must be one of: {', '.join(VALID_CLEANUP_MODES)}. "
        f"Got: {self.text_cleanup}"
    )

# Warn if aggressive mode without API key
if self.text_cleanup == "aggressive" and not self.groq_api_key:
    warnings.append(
        "HANDFREE_TEXT_CLEANUP=aggressive requires GROQ_API_KEY. "
        "Will fall back to 'standard' mode."
    )
```

### Step 2.6: Update .env.example

```bash
# Text Cleanup Settings
# Removes speech disfluencies (um, uh, false starts, etc.)
# Options: off, light, standard, aggressive
HANDFREE_TEXT_CLEANUP=standard

# Preserve intentional patterns like "I like pizza" vs filler "like"
HANDFREE_PRESERVE_INTENTIONAL=true
```

---

## Phase 3: Integration

### Step 3.1-3.4: Update main.py

Add import:
```python
from handfree.text_cleanup import TextCleaner, CleanupMode
```

Add factory function:
```python
def get_text_cleaner(config: Config) -> TextCleaner:
    """Create text cleaner based on configuration."""
    mode_map = {
        "off": CleanupMode.OFF,
        "light": CleanupMode.LIGHT,
        "standard": CleanupMode.STANDARD,
        "aggressive": CleanupMode.AGGRESSIVE,
    }
    mode = mode_map.get(config.text_cleanup, CleanupMode.STANDARD)

    return TextCleaner(
        mode=mode,
        api_key=config.groq_api_key if mode == CleanupMode.AGGRESSIVE else None,
        preserve_intentional=config.preserve_intentional,
    )
```

Update `HandFreeApp.__init__()`:
```python
# Initialize text cleaner
self.text_cleaner = get_text_cleaner(config)
```

Update `handle_stop()` (after line 246):
```python
text = self.transcriber.transcribe(audio_bytes, language=self.language)
if text:
    # Clean disfluencies
    if self.config.text_cleanup != "off":
        original_text = text
        text = self.text_cleaner.clean(text)
        if text != original_text:
            logger.debug(f"Text cleaned: '{original_text}' -> '{text}'")

    print(f"[Transcription] {text}")
    # ... rest of output handling
```

### Step 3.5: Update startup banner

```python
print(f"  Text cleanup: {self.config.text_cleanup}")
```

### Step 3.6: Update __init__.py

```python
from handfree.text_cleanup import TextCleaner, CleanupMode
from handfree.exceptions import TextCleanupError

__all__ = [
    # ... existing exports ...
    "TextCleaner",
    "CleanupMode",
    "TextCleanupError",
]
```

---

## Phase 4: Testing

### Step 4.1: Create test file

**File:** `tests/test_text_cleanup.py`

```python
"""Tests for text cleanup module."""

import pytest
from handfree.text_cleanup import TextCleaner, CleanupMode


class TestCleanupModeOff:
    """Tests for disabled cleanup."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.OFF)

    def test_returns_unchanged(self):
        text = "Um, I I think, you know, like..."
        assert self.cleaner.clean(text) == text


class TestCleanupModeLight:
    """Tests for light cleanup mode."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.LIGHT)

    def test_removes_um(self):
        assert self.cleaner.clean("Um, hello there") == "hello there"

    def test_removes_uh(self):
        assert self.cleaner.clean("I uh think so") == "I think so"

    def test_removes_multiple_fillers(self):
        assert self.cleaner.clean("Um, uh, hello") == "hello"

    def test_preserves_like(self):
        # Light mode doesn't remove "like"
        result = self.cleaner.clean("It's like really good")
        assert "like" in result


class TestCleanupModeStandard:
    """Tests for standard cleanup mode."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    def test_removes_filler_like(self):
        result = self.cleaner.clean("It's like really good")
        assert result == "It's really good"

    def test_preserves_verb_like(self):
        result = self.cleaner.clean("I like this feature")
        assert result == "I like this feature"

    def test_removes_you_know(self):
        result = self.cleaner.clean("It's, you know, important")
        assert result == "It's important"

    def test_removes_repetitions(self):
        assert self.cleaner.clean("I I think so") == "I think so"

    def test_removes_triple_repetitions(self):
        assert self.cleaner.clean("the the the thing") == "the thing"

    def test_preserves_emphasis_repetitions(self):
        result = self.cleaner.clean("This is very very important")
        assert "very very" in result

    def test_removes_false_starts_with_sorry(self):
        result = self.cleaner.clean("Can you... sorry, can you send this?")
        assert result == "can you send this?"

    def test_complex_disfluency(self):
        result = self.cleaner.clean(
            "Hey, um, can you... sorry, can you send this?"
        )
        assert "um" not in result.lower()
        assert "send this" in result.lower()


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    def test_empty_string(self):
        assert self.cleaner.clean("") == ""

    def test_none_as_empty(self):
        assert self.cleaner.clean(None or "") == ""

    def test_only_fillers(self):
        result = self.cleaner.clean("Um uh")
        assert isinstance(result, str)

    def test_whitespace_normalization(self):
        result = self.cleaner.clean("Hello   world")
        assert result == "Hello world"

    def test_punctuation_preservation(self):
        result = self.cleaner.clean("Hello, um, world!")
        assert "!" in result


class TestPreserveIntentional:
    """Tests for preserve_intentional flag."""

    def test_preserve_intentional_true(self):
        cleaner = TextCleaner(
            mode=CleanupMode.STANDARD,
            preserve_intentional=True
        )
        result = cleaner.clean("I like pizza")
        assert result == "I like pizza"

    def test_preserve_intentional_false(self):
        cleaner = TextCleaner(
            mode=CleanupMode.STANDARD,
            preserve_intentional=False
        )
        # With preserve_intentional=False, more aggressive removal
        result = cleaner.clean("very very important")
        assert result == "very important"
```

### Step 4.5: Property-based tests with Hypothesis

```python
from hypothesis import given, strategies as st

class TestPropertyBased:
    """Property-based tests."""

    def setup_method(self):
        self.cleaner = TextCleaner(mode=CleanupMode.STANDARD)

    @given(st.text(min_size=0, max_size=1000))
    def test_never_crashes(self, text):
        """Cleanup should never crash on any input."""
        result = self.cleaner.clean(text)
        assert isinstance(result, str)

    @given(st.text(min_size=1, max_size=500))
    def test_output_not_much_longer(self, text):
        """Output should not be significantly longer than input."""
        result = self.cleaner.clean(text)
        # Allow small increase for whitespace normalization
        assert len(result) <= len(text) + 10
```

---

## Phase 5: Verification

### Step 5.1: Run all tests

```bash
cd /Users/sukhdeepsingh/projects/ClaudeProjects/handfree
source venv/bin/activate
pytest tests/test_text_cleanup.py -v
```

### Step 5.2-5.4: Manual tests

```bash
# Test with cleanup off
HANDFREE_TEXT_CLEANUP=off python main.py
# Speak: "Um, hello"
# Expected: "Um, hello" (unchanged)

# Test with light mode
HANDFREE_TEXT_CLEANUP=light python main.py
# Speak: "Um, uh, hello there"
# Expected: "hello there"

# Test with standard mode (default)
HANDFREE_TEXT_CLEANUP=standard python main.py
# Speak: "Hey, um, can you, like, you know, send this?"
# Expected: "Hey, can you send this?"
```

### Step 5.5: Performance benchmark

```python
import time
from handfree.text_cleanup import TextCleaner, CleanupMode

cleaner = TextCleaner(mode=CleanupMode.STANDARD)
text = "Um, I I think, you know, like, we should, basically, actually do this."

# Benchmark
iterations = 1000
start = time.perf_counter()
for _ in range(iterations):
    cleaner.clean(text)
elapsed = time.perf_counter() - start

avg_ms = (elapsed / iterations) * 1000
print(f"Average cleanup time: {avg_ms:.2f}ms")
# Target: <5ms
```

### Step 5.6: End-to-end test

1. Start HandFree with default settings
2. Record speech with intentional disfluencies
3. Verify cleaned output appears in active app
4. Check that meaning is preserved

---

## Performance Targets

| Mode | Target | Max Acceptable |
|------|--------|----------------|
| OFF | 0ms | 0ms |
| LIGHT | <2ms | <5ms |
| STANDARD | <5ms | <20ms |
| AGGRESSIVE | <500ms | <1000ms |

---

## Files Summary

### New Files
- `src/handfree/text_cleanup.py`
- `tests/test_text_cleanup.py`

### Modified Files
- `src/handfree/exceptions.py` - Add `TextCleanupError`
- `src/handfree/config.py` - Add cleanup config options
- `src/handfree/__init__.py` - Export new classes
- `main.py` - Integrate cleanup in pipeline
- `.env.example` - Document new env vars
