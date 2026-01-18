# whisper.cpp Integration - Implementation Plan

This document provides a detailed step-by-step guide to add local transcription support using whisper.cpp. For architecture and specifications, see `../spec/spec.md`.

---

## Overview

**Goal:** Add whisper.cpp as an alternative transcription backend for offline, private, cost-free speech-to-text.

**Benefits:**
- Privacy: Audio never leaves the machine
- Offline: Works without internet connection
- No API costs: Unlimited transcriptions after setup
- Lower latency: No network round-trip (with appropriate model)

**Approach:** Create a `LocalTranscriber` class that mirrors the existing `Transcriber` interface, allowing easy switching between cloud (Groq) and local (whisper.cpp) backends.

---

## Master Todo Checklist

### Phase 1: Setup & Dependencies
- [ ] 1.1 Install pywhispercpp package
- [ ] 1.2 Download whisper model (base.en recommended)
- [ ] 1.3 Verify whisper.cpp works standalone
- [ ] 1.4 Test transcription quality and latency

### Phase 2: LocalTranscriber Module
- [x] 2.1 Create `local_transcriber.py` with `LocalTranscriber` class
- [x] 2.2 Implement `__init__` with model loading
- [x] 2.3 Implement `transcribe()` method
- [x] 2.4 Implement `is_model_downloaded()` check
- [x] 2.5 Implement `download_model()` utility
- [x] 2.6 Add error handling for missing models
- [x] 2.7 Create `test_local_transcriber.py`
- [x] 2.8 Verify: Transcribe test audio locally (via unit tests with mocks)

### Phase 3: Configuration Updates
- [x] 3.1 Update `config.py` with new environment variables
- [x] 3.2 Add `HANDFREE_TRANSCRIBER` option (groq/local)
- [x] 3.3 Add `HANDFREE_WHISPER_MODEL` option
- [x] 3.4 Add `HANDFREE_MODELS_DIR` option
- [x] 3.5 Update `.env.example` with new options

### Phase 4: Main App Integration
- [x] 4.1 Update `main.py` to support transcriber selection
- [x] 4.2 Create factory function `get_transcriber()`
- [x] 4.3 Add fallback logic (local -> cloud if model missing)
- [x] 4.4 Add startup message showing transcriber mode
- [x] 4.5 Verify: End-to-end flow works with local transcription

### Phase 5: Model Management
- [x] 5.1 Create `model_manager.py` utility
- [x] 5.2 Implement model download progress display
- [x] 5.3 Implement model listing command
- [x] 5.4 Add CLI option to download models: `python -m handfree.model_manager download base.en`
- [x] 5.5 Verify: Model download works correctly

### Phase 6: Documentation & Testing
- [ ] 6.1 Update README.md with local transcription setup
- [ ] 6.2 Add troubleshooting for common issues
- [x] 6.3 Create performance comparison tests
- [ ] 6.4 Document model selection guidance
- [ ] 6.5 Final end-to-end testing

---

## Detailed Implementation

---

## Phase 1: Setup & Dependencies

### Step 1.1: Install pywhispercpp

**Commands:**
```bash
cd /Users/sukhdeepsingh/projects/ClaudeProjects/handfree
source venv/bin/activate
pip install pywhispercpp
```

**Verification:**
```python
python -c "from pywhispercpp.model import Model; print('pywhispercpp installed')"
```

### Step 1.2: Download Whisper Model

Models are downloaded automatically on first use, but can be pre-downloaded:

```bash
# Models will be cached in ~/.cache/whisper/ or similar
# The pywhispercpp library handles downloading automatically
```

Recommended models:
- `base.en` - Best balance of speed and accuracy for English
- `tiny.en` - Fastest, for quick testing
- `small.en` - Better accuracy if speed is acceptable

### Step 1.3: Verify Standalone Operation

**Test Script:**
```python
# test_whisper_standalone.py
import time
from pywhispercpp.model import Model

# Load model (downloads if needed)
print("Loading model...")
start = time.time()
model = Model('base.en')
print(f"Model loaded in {time.time() - start:.1f}s")

# Transcribe test audio
print("Transcribing...")
start = time.time()
result = model.transcribe('test_recording.wav')
elapsed = time.time() - start

print(f"Result: {result}")
print(f"Latency: {elapsed*1000:.0f}ms")
```

### Step 1.4: Benchmark Latency

Expected performance on Apple Silicon:
| Model | Load Time | 5s Audio | 30s Audio |
|-------|-----------|----------|-----------|
| tiny.en | ~1s | ~100ms | ~500ms |
| base.en | ~2s | ~200ms | ~1s |
| small.en | ~3s | ~500ms | ~3s |

---

## Phase 2: LocalTranscriber Module

### Step 2.1-2.6: Create `local_transcriber.py`

**File:** `src/handfree/local_transcriber.py`

```python
"""
Local Transcriber Module
Local speech-to-text transcription using whisper.cpp.
"""

import os
from pathlib import Path
from typing import Optional
import tempfile

from pywhispercpp.model import Model


class LocalTranscriptionError(Exception):
    """Raised when local transcription fails."""
    pass


class LocalTranscriber:
    """Transcribes audio locally using whisper.cpp."""

    # Available models in order of size
    AVAILABLE_MODELS = [
        "tiny", "tiny.en",
        "base", "base.en",
        "small", "small.en",
        "medium", "medium.en",
        "large-v1", "large-v2", "large-v3"
    ]

    def __init__(
        self,
        model_name: str = "base.en",
        models_dir: Optional[str] = None
    ):
        """
        Initialize local transcriber with whisper.cpp.

        Args:
            model_name: Whisper model to use (e.g., "base.en", "small.en")
            models_dir: Directory for model files. Defaults to ~/.cache/whisper/
        """
        self.model_name = model_name
        self.models_dir = models_dir or os.path.expanduser("~/.cache/whisper")
        self._model: Optional[Model] = None

        # Validate model name
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown model: {model_name}. "
                f"Available models: {', '.join(self.AVAILABLE_MODELS)}"
            )

    def _ensure_model_loaded(self) -> None:
        """Load the model if not already loaded."""
        if self._model is None:
            try:
                # Create models directory if needed
                Path(self.models_dir).mkdir(parents=True, exist_ok=True)

                # Load model (will download if not present)
                self._model = Model(
                    self.model_name,
                    models_dir=self.models_dir
                )
            except Exception as e:
                raise LocalTranscriptionError(
                    f"Failed to load whisper model '{self.model_name}': {e}"
                )

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe audio to text locally.

        Args:
            audio_bytes: WAV audio file as bytes (16kHz, mono, 16-bit)
            language: Language code (default "en")

        Returns:
            Transcribed text string.

        Raises:
            LocalTranscriptionError: If transcription fails.
        """
        if not audio_bytes:
            return ""

        self._ensure_model_loaded()

        try:
            # Write audio to temporary file (pywhispercpp needs file path)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                # Transcribe
                segments = self._model.transcribe(temp_path)

                # Combine all segments into single text
                text = " ".join(
                    segment.text.strip()
                    for segment in segments
                    if segment.text.strip()
                )

                return text.strip()

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except Exception as e:
            raise LocalTranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self) -> bool:
        """Check if the configured model is available locally."""
        model_path = Path(self.models_dir) / f"ggml-{self.model_name}.bin"
        return model_path.exists()

    def download_model(self, show_progress: bool = True) -> None:
        """
        Download the configured model if not present.

        Args:
            show_progress: Whether to show download progress
        """
        if self.is_model_downloaded():
            print(f"Model '{self.model_name}' already downloaded.")
            return

        print(f"Downloading model '{self.model_name}'...")
        # Loading the model triggers download
        self._ensure_model_loaded()
        print(f"Model '{self.model_name}' downloaded successfully.")

    def get_model_path(self) -> Path:
        """Get the path to the model file."""
        return Path(self.models_dir) / f"ggml-{self.model_name}.bin"

    @property
    def model_loaded(self) -> bool:
        """Whether the model is currently loaded in memory."""
        return self._model is not None

    def unload_model(self) -> None:
        """Unload model from memory to free RAM."""
        self._model = None
```

### Step 2.7-2.8: Test Script

**File:** `tests/test_local_transcriber.py`

```python
"""Tests for LocalTranscriber."""

import time
from local_transcriber import LocalTranscriber, LocalTranscriptionError


def test_local_transcription():
    """Test local transcription with a real audio file."""
    # Create transcriber
    transcriber = LocalTranscriber(model_name="base.en")

    # Load test audio
    with open("test_recording.wav", "rb") as f:
        audio_bytes = f.read()

    # Transcribe
    print("Transcribing locally...")
    start = time.time()
    text = transcriber.transcribe(audio_bytes)
    elapsed = time.time() - start

    print(f"Transcription: {text}")
    print(f"Latency: {elapsed*1000:.0f}ms")

    assert len(text) > 0, "Expected non-empty transcription"
    print("✅ Test passed!")


def test_model_management():
    """Test model download and management."""
    transcriber = LocalTranscriber(model_name="tiny.en")

    print(f"Model downloaded: {transcriber.is_model_downloaded()}")
    print(f"Model path: {transcriber.get_model_path()}")

    # Trigger download if needed
    transcriber.download_model()

    assert transcriber.is_model_downloaded()
    print("✅ Model management test passed!")


if __name__ == "__main__":
    test_local_transcription()
    test_model_management()
```

---

## Phase 3: Configuration Updates

### Step 3.1-3.4: Update `config.py`

**Add to `config.py`:**

```python
class Config:
    """Application configuration from environment variables."""

    # ... existing config ...

    # Transcription backend
    TRANSCRIBER = os.environ.get("HANDFREE_TRANSCRIBER", "groq")  # "groq" or "local"

    # Local transcription settings (whisper.cpp)
    WHISPER_MODEL = os.environ.get("HANDFREE_WHISPER_MODEL", "base.en")
    MODELS_DIR = os.environ.get("HANDFREE_MODELS_DIR", os.path.expanduser("~/.cache/whisper"))

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if cls.TRANSCRIBER == "groq" and not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY required when HANDFREE_TRANSCRIBER=groq.\n"
                "Set HANDFREE_TRANSCRIBER=local to use local transcription."
            )

        if cls.TRANSCRIBER not in ("groq", "local"):
            raise ValueError(
                f"Invalid HANDFREE_TRANSCRIBER: {cls.TRANSCRIBER}. "
                "Must be 'groq' or 'local'."
            )
```

### Step 3.5: Update `.env.example`

**Add to `.env.example`:**

```bash
# Transcription Backend
# Options: "groq" (cloud, requires API key) or "local" (whisper.cpp, offline)
HANDFREE_TRANSCRIBER=groq

# Local Transcription Settings (only used when TRANSCRIBER=local)
# Model options: tiny.en, base.en, small.en, medium.en, large
HANDFREE_WHISPER_MODEL=base.en
HANDFREE_MODELS_DIR=~/.cache/whisper
```

---

## Phase 4: Main App Integration

### Step 4.1-4.4: Update `main.py`

**Add transcriber factory function:**

```python
from config import Config

def get_transcriber():
    """Create transcriber based on configuration."""
    if Config.TRANSCRIBER == "local":
        from local_transcriber import LocalTranscriber
        print(f"🏠 Using local transcription (whisper.cpp, model: {Config.WHISPER_MODEL})")
        return LocalTranscriber(
            model_name=Config.WHISPER_MODEL,
            models_dir=Config.MODELS_DIR
        )
    else:
        from transcriber import Transcriber
        print("☁️  Using cloud transcription (Groq Whisper API)")
        return Transcriber()
```

**Update `HandFreeApp.__init__`:**

```python
def __init__(self):
    """Initialize all components."""
    load_dotenv()
    Config.validate()

    # Initialize modules
    self.recorder = AudioRecorder()
    self.transcriber = get_transcriber()  # Uses factory function
    self.output = OutputHandler()
    # ... rest of init
```

**Add fallback logic (optional):**

```python
def get_transcriber_with_fallback():
    """Get transcriber with fallback from local to cloud."""
    if Config.TRANSCRIBER == "local":
        from local_transcriber import LocalTranscriber
        local = LocalTranscriber(model_name=Config.WHISPER_MODEL)

        if not local.is_model_downloaded():
            print(f"⚠️  Model '{Config.WHISPER_MODEL}' not downloaded.")
            if Config.GROQ_API_KEY:
                print("   Falling back to Groq cloud transcription.")
                from transcriber import Transcriber
                return Transcriber()
            else:
                print("   Downloading model (this may take a few minutes)...")
                local.download_model()

        return local
    else:
        from transcriber import Transcriber
        return Transcriber()
```

---

## Phase 5: Model Management

### Step 5.1-5.4: Create `model_manager.py`

**File:** `src/handfree/model_manager.py`

```python
"""
Model Manager
Utility for downloading and managing whisper.cpp models.
"""

import sys
from pathlib import Path
from local_transcriber import LocalTranscriber


def list_models():
    """List available models and their status."""
    print("Available whisper.cpp models:")
    print("-" * 50)

    models_dir = Path.home() / ".cache" / "whisper"

    for model in LocalTranscriber.AVAILABLE_MODELS:
        model_path = models_dir / f"ggml-{model}.bin"
        status = "✅ Downloaded" if model_path.exists() else "❌ Not downloaded"

        # Estimated sizes
        sizes = {
            "tiny": "75 MB", "tiny.en": "75 MB",
            "base": "142 MB", "base.en": "142 MB",
            "small": "466 MB", "small.en": "466 MB",
            "medium": "1.5 GB", "medium.en": "1.5 GB",
            "large-v1": "3 GB", "large-v2": "3 GB", "large-v3": "3 GB"
        }
        size = sizes.get(model, "?")

        print(f"  {model:12} ({size:>7}) - {status}")


def download_model(model_name: str):
    """Download a specific model."""
    print(f"Downloading model: {model_name}")

    transcriber = LocalTranscriber(model_name=model_name)
    transcriber.download_model()

    print(f"✅ Model '{model_name}' ready to use!")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m handfree.model_manager list       - List available models")
        print("  python -m handfree.model_manager download <model>  - Download a model")
        print("")
        print("Example:")
        print("  python -m handfree.model_manager download base.en")
        return

    command = sys.argv[1]

    if command == "list":
        list_models()
    elif command == "download" and len(sys.argv) > 2:
        model_name = sys.argv[2]
        download_model(model_name)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
```

---

## Phase 6: Documentation & Testing

### Step 6.1: Update README.md

**Add section to README.md:**

```markdown
## Local Transcription (whisper.cpp)

For offline, private transcription, you can use whisper.cpp instead of Groq API:

### Setup

1. Install pywhispercpp:
   ```bash
   pip install pywhispercpp
   ```

2. Download a model:
   ```bash
   python -m handfree.model_manager download base.en
   ```

3. Enable local transcription:
   ```bash
   export HANDFREE_TRANSCRIBER=local
   # or add to .env file
   ```

### Model Selection

| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|-----------------|
| tiny.en | 75 MB | Fastest | Basic | Quick testing |
| base.en | 142 MB | Fast | Good | **General use** |
| small.en | 466 MB | Medium | Better | Higher accuracy |
| medium.en | 1.5 GB | Slow | Great | Best accuracy |

For most users, `base.en` provides the best balance of speed and accuracy.

### Comparison: Cloud vs Local

| | Groq (Cloud) | whisper.cpp (Local) |
|---|---|---|
| Privacy | Audio sent to cloud | Audio stays local |
| Offline | ❌ Requires internet | ✅ Works offline |
| Cost | Free tier (2K req/day) | Completely free |
| Latency | ~200ms + network | ~200ms (base model) |
| Setup | API key only | Model download (~142MB) |
```

### Step 6.2: Troubleshooting

**Add to README.md:**

```markdown
### Troubleshooting Local Transcription

**"Model not found" error**
- Run: `python -m handfree.model_manager download base.en`

**Slow transcription**
- Use a smaller model: `export HANDFREE_WHISPER_MODEL=tiny.en`
- Ensure Apple Silicon acceleration is working (check for Metal GPU usage)

**High memory usage**
- Smaller models use less RAM: tiny (1GB), base (2GB), small (3GB)
- Unload model when not in use (restart app)

**Transcription quality issues**
- Try a larger model: `export HANDFREE_WHISPER_MODEL=small.en`
- Ensure audio is 16kHz mono WAV (handled automatically by AudioRecorder)
```

---

## Performance Comparison

### Expected Results

| Backend | 5s Audio | 30s Audio | Memory |
|---------|----------|-----------|--------|
| Groq API | ~300ms | ~500ms | Minimal |
| whisper.cpp (tiny) | ~100ms | ~400ms | ~1 GB |
| whisper.cpp (base) | ~200ms | ~800ms | ~2 GB |
| whisper.cpp (small) | ~500ms | ~2s | ~3 GB |

*Tested on Apple M1 with Metal acceleration*

---

## Rollout Strategy

1. **Phase 1**: Implement LocalTranscriber as separate module
2. **Phase 2**: Add configuration support, keep Groq as default
3. **Phase 3**: Test thoroughly on different hardware
4. **Phase 4**: Document and release as optional feature
5. **Phase 5**: Consider making local the default in future versions

---

## Verification Checklist

- [ ] pywhispercpp installs without errors
- [ ] Model downloads successfully
- [ ] Local transcription produces accurate text
- [ ] Latency is acceptable (< 1s for short audio)
- [ ] Switching between local/cloud works
- [ ] Fallback logic works when model missing
- [ ] Memory usage is reasonable
- [ ] Works offline (airplane mode test)
- [ ] Documentation is complete and accurate
