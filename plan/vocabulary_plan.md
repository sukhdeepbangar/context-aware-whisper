# Vocabulary Hints Implementation Plan

Implementation plan for custom vocabulary support per [vocabulary_spec.md](../spec/vocabulary_spec.md).

## Overview

Add vocabulary hints feature to improve transcription of domain-specific terms like "Claude", "tmux", etc.

**Estimated scope:** ~150 lines of code across 5 files

## Prerequisites

- [x] Groq API supports `prompt` parameter
- [x] Verify pywhispercpp supports `initial_prompt` parameter (confirmed via documentation)

## Implementation Tasks

### Phase 1: Core Module

#### Task 1.1: Create vocabulary.py module
**File:** `src/context_aware_whisper/vocabulary.py`

Create new module with:
- `DEFAULT_VOCABULARY_PATH` constant
- `get_vocabulary_path()` function
- `load_vocabulary()` function

```python
"""
Vocabulary Module
Loads custom vocabulary hints from user file for transcription.
"""

from pathlib import Path
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_VOCABULARY_PATH = "~/.config/context-aware-whisper/vocabulary.txt"


def get_vocabulary_path() -> Path:
    """Get the vocabulary file path from env var or default."""
    custom_path = os.environ.get("CAW_VOCABULARY_FILE")
    if custom_path:
        return Path(custom_path).expanduser()
    return Path(DEFAULT_VOCABULARY_PATH).expanduser()


def load_vocabulary(file_path: Optional[Path] = None) -> Optional[str]:
    """
    Load vocabulary hints from file.

    Reads fresh every call (no caching) so user can edit anytime.

    Args:
        file_path: Path to vocabulary file. Uses default if None.

    Returns:
        Comma-separated vocabulary string, or None if file doesn't exist.
    """
    path = file_path or get_vocabulary_path()

    if not path.exists():
        return None

    try:
        words = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                words.append(line)

        if not words:
            return None

        prompt = ", ".join(words)
        logger.debug(f"Loaded vocabulary ({len(words)} terms)")
        return prompt

    except Exception as e:
        logger.warning(f"Failed to read vocabulary file {path}: {e}")
        return None
```

---

### Phase 2: Transcriber Updates

#### Task 2.1: Update Groq transcriber
**File:** `src/context_aware_whisper/transcriber.py`

**Changes:**
1. Import `load_vocabulary` from vocabulary module
2. Add `prompt` parameter to `transcribe()` method
3. Pass `prompt` to Groq API call

```python
# Add import
from context_aware_whisper.vocabulary import load_vocabulary

# Update transcribe method signature
def transcribe(
    self,
    audio_bytes: bytes,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    max_retries: int = 3
) -> str:

# Update API call (inside the method)
transcription = self.client.audio.transcriptions.create(
    file=("audio.wav", audio_bytes),
    model=self.model,
    language=language,
    prompt=prompt,
    response_format="text"
)
```

#### Task 2.2: Update local transcriber
**File:** `src/context_aware_whisper/local_transcriber.py`

**Changes:**
1. Import `load_vocabulary` from vocabulary module
2. Add `prompt` parameter to `transcribe()` method
3. Pass `initial_prompt` to whisper.cpp model

```python
# Add import
from context_aware_whisper.vocabulary import load_vocabulary

# Update transcribe method signature
def transcribe(
    self,
    audio_bytes: bytes,
    language: Optional[str] = None,
    prompt: Optional[str] = None
) -> str:

# Update model.transcribe call
segments = self._model.transcribe(temp_path, initial_prompt=prompt)
```

**Note:** Need to verify pywhispercpp parameter name. Check:
- `initial_prompt`
- `prompt`

---

### Phase 3: Integration

#### Task 3.1: Update main.py to load vocabulary
**File:** `src/context_aware_whisper/main.py`

**Changes:**
1. Import `load_vocabulary` function
2. Call `load_vocabulary()` before each transcription
3. Pass result to transcriber

```python
from context_aware_whisper.vocabulary import load_vocabulary

# In transcription flow:
vocab_prompt = load_vocabulary()
text = transcriber.transcribe(audio_bytes, language=config.language, prompt=vocab_prompt)
```

#### Task 3.2: Update config.py (optional)
**File:** `src/context_aware_whisper/config.py`

Add optional config field for custom vocabulary file path:

```python
# In Config dataclass
vocabulary_file: Optional[str] = None

# In from_env()
vocabulary_file=os.environ.get("CAW_VOCABULARY_FILE"),
```

Add to docstring:
```
CAW_VOCABULARY_FILE: Optional. Custom vocabulary file path
                     (default: ~/.config/context-aware-whisper/vocabulary.txt).
```

---

### Phase 4: Testing

#### Task 4.1: Create vocabulary tests
**File:** `tests/test_vocabulary.py`

```python
"""Tests for vocabulary module."""

import pytest
from pathlib import Path
from context_aware_whisper.vocabulary import load_vocabulary, get_vocabulary_path


class TestLoadVocabulary:
    """Tests for load_vocabulary function."""

    def test_file_exists_returns_prompt(self, tmp_path):
        """Returns comma-separated string when file exists."""
        vocab_file = tmp_path / "vocabulary.txt"
        vocab_file.write_text("Claude\ntmux\nkubectl\n")

        result = load_vocabulary(vocab_file)

        assert result == "Claude, tmux, kubectl"

    def test_file_missing_returns_none(self, tmp_path):
        """Returns None when file doesn't exist."""
        vocab_file = tmp_path / "nonexistent.txt"

        result = load_vocabulary(vocab_file)

        assert result is None

    def test_ignores_comments(self, tmp_path):
        """Ignores lines starting with #."""
        vocab_file = tmp_path / "vocabulary.txt"
        vocab_file.write_text("# This is a comment\nClaude\n# Another comment\ntmux\n")

        result = load_vocabulary(vocab_file)

        assert result == "Claude, tmux"

    def test_ignores_empty_lines(self, tmp_path):
        """Ignores empty lines."""
        vocab_file = tmp_path / "vocabulary.txt"
        vocab_file.write_text("Claude\n\n\ntmux\n")

        result = load_vocabulary(vocab_file)

        assert result == "Claude, tmux"

    def test_trims_whitespace(self, tmp_path):
        """Trims leading/trailing whitespace."""
        vocab_file = tmp_path / "vocabulary.txt"
        vocab_file.write_text("  Claude  \n\ttmux\t\n")

        result = load_vocabulary(vocab_file)

        assert result == "Claude, tmux"

    def test_empty_file_returns_none(self, tmp_path):
        """Returns None for empty file."""
        vocab_file = tmp_path / "vocabulary.txt"
        vocab_file.write_text("")

        result = load_vocabulary(vocab_file)

        assert result is None

    def test_only_comments_returns_none(self, tmp_path):
        """Returns None when file has only comments."""
        vocab_file = tmp_path / "vocabulary.txt"
        vocab_file.write_text("# Just a comment\n# Another one\n")

        result = load_vocabulary(vocab_file)

        assert result is None


class TestGetVocabularyPath:
    """Tests for get_vocabulary_path function."""

    def test_default_path(self, monkeypatch):
        """Returns default path when env var not set."""
        monkeypatch.delenv("CAW_VOCABULARY_FILE", raising=False)

        result = get_vocabulary_path()

        assert result == Path("~/.config/context-aware-whisper/vocabulary.txt").expanduser()

    def test_env_override(self, monkeypatch):
        """Uses CAW_VOCABULARY_FILE when set."""
        monkeypatch.setenv("CAW_VOCABULARY_FILE", "/custom/path/vocab.txt")

        result = get_vocabulary_path()

        assert result == Path("/custom/path/vocab.txt")
```

#### Task 4.2: Update transcriber tests
**Files:** `tests/test_transcriber.py`, `tests/test_local_transcriber.py`

Add tests verifying `prompt` parameter is passed correctly.

---

### Phase 5: Documentation

#### Task 5.1: Create example vocabulary file
**File:** `examples/vocabulary.txt`

```txt
# Example vocabulary file for Context-Aware Whisper
# Copy to: ~/.config/context-aware-whisper/vocabulary.txt
#
# Add words/phrases that are often misrecognized.
# One entry per line. Lines starting with # are comments.

# AI/ML terms
Claude
Anthropic
OpenAI
GPT
LLM
MLX

# Development tools
tmux
kubectl
pytest
nginx
Redis
Docker

# Programming
async
await
TypeScript
JavaScript
Python

# Add your custom terms below:
```

#### Task 5.2: Update README
Add section explaining vocabulary feature and how to use it.

#### Task 5.3: Update spec/README.md
Add vocabulary spec to the quick links table.

---

## Task Checklist

| # | Task | File | Status |
|---|------|------|--------|
| 1.1 | Create vocabulary.py module | `src/.../vocabulary.py` | [x] |
| 2.1 | Update Groq transcriber | `src/.../transcriber.py` | [x] |
| 2.2 | Update local transcriber | `src/.../local_transcriber.py` | [x] |
| 3.1 | Update main.py integration | `src/.../main.py` | N/A (no main.py, transcriber called directly) |
| 3.2 | Update config.py (optional) | `src/.../config.py` | [x] |
| 4.1 | Create vocabulary tests | `tests/test_vocabulary.py` | [x] |
| 4.2 | Update transcriber tests | `tests/test_*.py` | [x] |
| 5.1 | Create example vocabulary file | `examples/vocabulary.txt` | [x] |
| 5.2 | Update README | `README.md` | [ ] |
| 5.3 | Update spec README | `spec/README.md` | [ ] |

## Verification Steps

1. **Unit tests pass:**
   ```bash
   pytest tests/test_vocabulary.py -v
   ```

2. **Manual test with vocabulary:**
   ```bash
   # Create vocabulary file
   mkdir -p ~/.config/context-aware-whisper
   echo -e "Claude\ntmux\nkubectl" > ~/.config/context-aware-whisper/vocabulary.txt

   # Run transcription and verify "Claude" is recognized correctly
   ```

3. **Test without vocabulary file:**
   - Remove/rename vocabulary file
   - Verify transcription still works

4. **Test file editing:**
   - Start app
   - Edit vocabulary file
   - New transcription should use updated vocabulary

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| pywhispercpp doesn't support initial_prompt | Medium | Check API, may need alternative approach |
| Large vocabulary degrades quality | Low | Document recommended max entries (~50-100) |
| File read latency | Low | File reads are fast (<1ms for small files) |

## Dependencies

- No new package dependencies required
- Uses standard library: `pathlib`, `os`, `logging`
