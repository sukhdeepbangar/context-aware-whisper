# Vocabulary Hints Specification

Custom vocabulary support for improving transcription accuracy of domain-specific terms, proper nouns, and technical jargon.

## Problem Statement

Whisper models often misrecognize uncommon words:
- "Claude" → "cloud"
- "tmux" → "team axe"
- "kubectl" → "cube control"
- "Anthropic" → "anthropic" (wrong casing)

## Solution

Provide vocabulary hints to the Whisper model via its **initial prompt** feature. The model uses this context to bias transcription toward expected words.

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| V1 | Load vocabulary from a user-editable file | Must |
| V2 | Read file fresh on every transcription (no caching) | Must |
| V3 | Support both Groq and local whisper.cpp backends | Must |
| V4 | Graceful handling when file doesn't exist | Must |
| V5 | Support comments in vocabulary file | Should |
| V6 | Ignore empty lines and whitespace | Should |
| V7 | Log when vocabulary is loaded (debug level) | Should |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NF1 | File read should add < 1ms latency |
| NF2 | No impact when vocabulary file is absent |
| NF3 | File format should be simple and human-readable |

## Design

### Vocabulary File Location

```
~/.config/context-aware-whisper/vocabulary.txt
```

Alternative paths checked in order:
1. `$CAW_VOCABULARY_FILE` (env var override)
2. `~/.config/context-aware-whisper/vocabulary.txt` (default)

### File Format

Plain text, one word/phrase per line:

```txt
# Technical terms
Claude
tmux
kubectl
pytest

# Company names
Anthropic
OpenAI
Groq

# Project-specific terms
context-aware-whisper
pywhispercpp
```

**Format rules:**
- Lines starting with `#` are comments (ignored)
- Empty lines are ignored
- Leading/trailing whitespace is trimmed
- One word or phrase per line
- No length limit per line
- UTF-8 encoding

### Prompt Construction

Words are joined into a comma-separated prompt string:

```
Input file:
  Claude
  tmux
  kubectl

Generated prompt:
  "Claude, tmux, kubectl"
```

This prompt is passed to Whisper's `prompt` (Groq) or `initial_prompt` (whisper.cpp) parameter.

## Architecture

### Component Changes

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│  - Passes vocabulary_file path to transcriber               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    vocabulary.py (NEW)                       │
│  - load_vocabulary(file_path) -> Optional[str]              │
│  - Reads file, parses lines, returns prompt string          │
│  - Returns None if file doesn't exist                       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    transcriber.py       │     │  local_transcriber.py   │
│  - Add prompt param     │     │  - Add initial_prompt   │
│  - Call load_vocabulary │     │  - Call load_vocabulary │
└─────────────────────────┘     └─────────────────────────┘
```

### New Module: `vocabulary.py`

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
        logger.debug(f"Loaded vocabulary ({len(words)} terms): {prompt[:50]}...")
        return prompt

    except Exception as e:
        logger.warning(f"Failed to read vocabulary file {path}: {e}")
        return None
```

### Transcriber Interface Changes

#### `transcriber.py` (Groq)

```python
def transcribe(
    self,
    audio_bytes: bytes,
    language: Optional[str] = None,
    prompt: Optional[str] = None,  # NEW
    max_retries: int = 3
) -> str:
    ...
    transcription = self.client.audio.transcriptions.create(
        file=("audio.wav", audio_bytes),
        model=self.model,
        language=language,
        prompt=prompt,  # NEW - vocabulary hints
        response_format="text"
    )
```

#### `local_transcriber.py` (whisper.cpp)

```python
def transcribe(
    self,
    audio_bytes: bytes,
    language: Optional[str] = None,
    prompt: Optional[str] = None  # NEW
) -> str:
    ...
    segments = self._model.transcribe(
        temp_path,
        initial_prompt=prompt  # NEW - vocabulary hints
    )
```

### Config Changes

Add to `config.py`:

```python
@dataclass
class Config:
    ...
    # Vocabulary file path (optional override)
    vocabulary_file: Optional[str] = None
```

Environment variable: `CAW_VOCABULARY_FILE`

## API Reference

### `vocabulary.load_vocabulary()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | `Optional[Path]` | `None` | Custom path, or use default |

| Returns | Description |
|---------|-------------|
| `str` | Comma-separated vocabulary prompt |
| `None` | File doesn't exist or is empty |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CAW_VOCABULARY_FILE` | Custom vocabulary file path | `~/.config/context-aware-whisper/vocabulary.txt` |

## Example Vocabulary File

```txt
# ~/.config/context-aware-whisper/vocabulary.txt
# Custom vocabulary for speech recognition
# Edit this file anytime - changes take effect on next transcription

# AI/ML terms
Claude
Anthropic
OpenAI
GPT
LLM

# Development tools
tmux
kubectl
pytest
nginx
Redis

# Programming terms
async
await
TypeScript
JavaScript

# Your custom terms below:
```

## Testing

### Unit Tests

1. `test_load_vocabulary_file_exists` - Returns comma-separated string
2. `test_load_vocabulary_file_missing` - Returns None
3. `test_load_vocabulary_with_comments` - Ignores comment lines
4. `test_load_vocabulary_empty_lines` - Ignores empty lines
5. `test_load_vocabulary_whitespace` - Trims whitespace
6. `test_load_vocabulary_empty_file` - Returns None
7. `test_load_vocabulary_custom_path` - Uses provided path
8. `test_load_vocabulary_env_override` - Uses CAW_VOCABULARY_FILE

### Integration Tests

1. Groq transcriber uses vocabulary prompt
2. Local transcriber uses vocabulary prompt
3. Transcription works when vocabulary file missing

## Security Considerations

- File is read-only (no write operations)
- Path traversal: Only reads from specified path
- Large file handling: Read line-by-line, not entire file to memory
- Encoding: UTF-8 only, reject invalid encoding

## Future Enhancements

1. **Hot-reload notification**: Log when file changes detected
2. **Vocabulary validation**: Warn on unusually long entries
3. **Multiple vocabulary files**: Domain-specific vocabularies
4. **GUI editor**: In-app vocabulary management
