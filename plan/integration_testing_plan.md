# Integration Testing - Implementation Plan

Step-by-step guide to implement functional/integration testing for Context-Aware Whisper.

**Spec:** [../spec/integration_testing_spec.md](../spec/integration_testing_spec.md)

---

## Master Todo Checklist

### Phase 1: Test Infrastructure
- [x] 1.1 Create `tests/integration/` directory structure
- [x] 1.2 Add hardware detection fixtures to `conftest.py`
- [x] 1.3 Add custom pytest markers to `pyproject.toml`
- [x] 1.4 Create `tests/integration/conftest.py` with integration fixtures

### Phase 2: Audio Fixtures
- [x] 2.1 Create `tests/fixtures/audio/` directory
- [x] 2.2 Create `manifest.json` schema
- [x] 2.3 Record/generate initial fixtures (hello_world, silence, noise)
- [x] 2.4 Implement `audio_generator.py` for CI fallback
- [x] 2.5 Set up Git LFS for `.wav` files (optional)

### Phase 3: Integration Tests
- [x] 3.1 Implement `test_audio_recorder_integration.py`
- [x] 3.2 Implement `test_local_transcriber_integration.py`
- [x] 3.3 Implement `test_output_handler_integration.py`
- [x] 3.4 Implement `test_e2e_flow_integration.py`

### Phase 4: CI/CD Updates
- [x] 4.1 Update `.github/workflows/test.yml` with integration jobs
- [x] 4.2 Configure model caching for CI
- [x] 4.3 Add artifact uploads for test failures

### Phase 5: Verification Tools
- [x] 5.1 Create `scripts/verify_feature.py`
- [x] 5.2 Document verification workflow
- [x] 5.3 Add verification checklist to PR template

---

## Phase 1: Test Infrastructure

### Step 1.1: Create Directory Structure

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
touch tests/integration/conftest.py
```

### Step 1.2: Add Hardware Detection to conftest.py

**File:** `tests/conftest.py`

Add after existing fixtures:

```python
import subprocess
import sys
from pathlib import Path

# =============================================================================
# HARDWARE DETECTION FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def has_microphone() -> bool:
    """Check if a microphone is available."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        return len(input_devices) > 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def has_whisper_model() -> bool:
    """Check if whisper.cpp model is available."""
    model_path = Path.home() / ".cache" / "whisper" / "ggml-base.en.bin"
    return model_path.exists()


@pytest.fixture(scope="session")
def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    import os
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"]
    return any(os.environ.get(var) for var in ci_vars)


@pytest.fixture(scope="session")
def has_accessibility_permission() -> bool:
    """Check if accessibility permission is granted (macOS)."""
    if sys.platform != "darwin":
        return True
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to return name of first process'],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# =============================================================================
# AUTO-SKIP FIXTURE
# =============================================================================

@pytest.fixture(autouse=True)
def _auto_skip_by_marker(request, has_microphone, has_whisper_model, has_accessibility_permission):
    """Automatically skip tests based on markers."""
    if request.node.get_closest_marker("requires_microphone") and not has_microphone:
        pytest.skip("No microphone available")

    if request.node.get_closest_marker("requires_whisper") and not has_whisper_model:
        pytest.skip("Whisper model not downloaded")

    if request.node.get_closest_marker("requires_macos") and sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    if request.node.get_closest_marker("requires_accessibility") and not has_accessibility_permission:
        pytest.skip("Accessibility permission not granted")
```

### Step 1.3: Add Markers to pyproject.toml

**File:** `pyproject.toml`

Update `[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "integration: marks tests as integration tests (may require hardware)",
    "requires_microphone: marks tests requiring microphone access",
    "requires_whisper: marks tests requiring whisper.cpp model",
    "requires_macos: marks tests requiring macOS-specific features",
    "requires_accessibility: marks tests requiring accessibility permissions",
    "slow: marks tests as slow (> 5 seconds)",
]
addopts = "-v --tb=short"
```

### Step 1.4: Integration conftest.py

**File:** `tests/integration/conftest.py`

```python
"""Integration test fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def audio_fixtures_dir() -> Path:
    """Path to audio fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "audio"


@pytest.fixture
def fixture_manifest(audio_fixtures_dir):
    """Load fixture manifest."""
    import json
    manifest_path = audio_fixtures_dir / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {"fixtures": []}
```

---

## Phase 2: Audio Fixtures

### Step 2.1: Create Directory

```bash
mkdir -p tests/fixtures/audio
```

### Step 2.2: Create manifest.json

**File:** `tests/fixtures/audio/manifest.json`

```json
{
  "version": "1.0",
  "fixtures": [
    {
      "filename": "hello_world.wav",
      "duration_sec": 2.0,
      "sample_rate": 16000,
      "expected_text": "Hello world",
      "expected_text_normalized": "hello world",
      "tolerance": 0.85,
      "category": "short"
    },
    {
      "filename": "silence.wav",
      "duration_sec": 3.0,
      "sample_rate": 16000,
      "expected_text": "",
      "tolerance": 1.0,
      "category": "edge_case"
    },
    {
      "filename": "short_phrase.wav",
      "duration_sec": 3.0,
      "sample_rate": 16000,
      "expected_text": "This is a test",
      "expected_text_normalized": "this is a test",
      "tolerance": 0.75,
      "category": "short"
    }
  ]
}
```

### Step 2.3: Generate Initial Fixtures

**Option A: Record manually**
- Use Audacity or QuickTime to record clear speech
- Export as 16kHz mono WAV

**Option B: Use macOS TTS**
```bash
say -v Alex -o hello_world.aiff "Hello world"
ffmpeg -i hello_world.aiff -ar 16000 -ac 1 tests/fixtures/audio/hello_world.wav
```

### Step 2.4: Create audio_generator.py

**File:** `tests/fixtures/audio_generator.py`

```python
#!/usr/bin/env python
"""Generate test audio fixtures programmatically."""

import subprocess
import tempfile
from pathlib import Path
import numpy as np
from scipy.io import wavfile

FIXTURES_DIR = Path(__file__).parent / "audio"
SAMPLE_RATE = 16000


def generate_silence(filename: str, duration_sec: float) -> Path:
    """Generate silent audio."""
    output = FIXTURES_DIR / filename
    samples = int(SAMPLE_RATE * duration_sec)
    audio = np.zeros(samples, dtype=np.int16)
    wavfile.write(str(output), SAMPLE_RATE, audio)
    return output


def generate_noise(filename: str, duration_sec: float, level: float = 0.1) -> Path:
    """Generate white noise."""
    output = FIXTURES_DIR / filename
    samples = int(SAMPLE_RATE * duration_sec)
    audio = (np.random.randn(samples) * 32767 * level).astype(np.int16)
    wavfile.write(str(output), SAMPLE_RATE, audio)
    return output


def generate_tts(filename: str, text: str, voice: str = "Alex") -> Path:
    """Generate audio using macOS TTS."""
    output = FIXTURES_DIR / filename

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        subprocess.run(["say", "-v", voice, "-o", tmp.name, text], check=True)
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp.name,
            "-ar", str(SAMPLE_RATE), "-ac", "1",
            str(output)
        ], check=True, capture_output=True)

    return output


def generate_all():
    """Generate all standard fixtures."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating silence.wav...")
    generate_silence("silence.wav", 3.0)

    print("Generating noise.wav...")
    generate_noise("noise.wav", 3.0, 0.05)

    print("Generating hello_world.wav...")
    generate_tts("hello_world.wav", "Hello world")

    print("Generating short_phrase.wav...")
    generate_tts("short_phrase.wav", "This is a test")

    print("Done!")


if __name__ == "__main__":
    generate_all()
```

---

## Phase 3: Integration Tests

### Step 3.1: AudioRecorder Integration

**File:** `tests/integration/test_audio_recorder_integration.py`

```python
"""Integration tests for AudioRecorder with real hardware."""

import time
import io
import pytest
import numpy as np
from scipy.io import wavfile

from context_aware_whisper.audio_recorder import AudioRecorder


@pytest.mark.integration
@pytest.mark.requires_microphone
class TestAudioRecorderIntegration:

    def test_real_recording_short(self):
        """Record 0.5s of actual audio."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)

        recorder.start_recording()
        time.sleep(0.5)
        wav_bytes = recorder.stop_recording()

        assert wav_bytes[:4] == b'RIFF'

        wav_io = io.BytesIO(wav_bytes)
        rate, data = wavfile.read(wav_io)

        assert rate == 16000
        duration = len(data) / rate
        assert 0.4 < duration < 0.6

    def test_multiple_cycles(self):
        """Test multiple start/stop cycles."""
        recorder = AudioRecorder()

        for _ in range(3):
            recorder.start_recording()
            time.sleep(0.2)
            wav_bytes = recorder.stop_recording()
            assert len(wav_bytes) > 0
```

### Step 3.2: LocalTranscriber Integration

**File:** `tests/integration/test_local_transcriber_integration.py`

```python
"""Integration tests for LocalTranscriber with whisper.cpp."""

import time
import pytest
from pathlib import Path


@pytest.mark.integration
@pytest.mark.requires_whisper
class TestLocalTranscriberIntegration:

    @pytest.fixture
    def transcriber(self):
        from context_aware_whisper.local_transcriber import LocalTranscriber
        return LocalTranscriber(model_name="base.en")

    def test_transcribe_fixture(self, transcriber, audio_fixtures_dir):
        """Transcribe hello_world fixture."""
        audio_path = audio_fixtures_dir / "hello_world.wav"
        if not audio_path.exists():
            pytest.skip("Fixture not found")

        result = transcriber.transcribe(audio_path.read_bytes())
        assert "hello" in result.lower() or "world" in result.lower()

    def test_transcribe_silence(self, transcriber, audio_fixtures_dir):
        """Silent audio should return minimal text."""
        audio_path = audio_fixtures_dir / "silence.wav"
        if not audio_path.exists():
            pytest.skip("Fixture not found")

        result = transcriber.transcribe(audio_path.read_bytes())
        assert len(result.strip()) < 20

    def test_latency_acceptable(self, transcriber, audio_fixtures_dir):
        """Transcription should complete within 2s for short audio."""
        audio_path = audio_fixtures_dir / "hello_world.wav"
        if not audio_path.exists():
            pytest.skip("Fixture not found")

        start = time.time()
        transcriber.transcribe(audio_path.read_bytes())
        elapsed = time.time() - start

        assert elapsed < 2.0
```

### Step 3.3: OutputHandler Integration

**File:** `tests/integration/test_output_handler_integration.py`

```python
"""Integration tests for OutputHandler."""

import pytest
import pyperclip

from context_aware_whisper.output_handler import OutputHandler


@pytest.mark.integration
class TestClipboardIntegration:

    @pytest.fixture(autouse=True)
    def preserve_clipboard(self):
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""
        yield
        try:
            pyperclip.copy(original)
        except Exception:
            pass

    def test_unicode_roundtrip(self):
        """Test clipboard preserves unicode."""
        handler = OutputHandler()
        test_text = "Hello cafe 2+2=4"

        handler.copy_to_clipboard(test_text)
        assert pyperclip.paste() == test_text
```

### Step 3.4: E2E Flow Integration

**File:** `tests/integration/test_e2e_flow_integration.py`

```python
"""End-to-end integration tests."""

import pytest
import pyperclip


@pytest.mark.integration
@pytest.mark.requires_whisper
class TestE2EFlow:

    def test_audio_to_clipboard(self, audio_fixtures_dir):
        """Test: audio file -> transcription -> clipboard."""
        from context_aware_whisper.local_transcriber import LocalTranscriber
        from context_aware_whisper.output_handler import OutputHandler

        audio_path = audio_fixtures_dir / "hello_world.wav"
        if not audio_path.exists():
            pytest.skip("Fixture not found")

        transcriber = LocalTranscriber(model_name="base.en")
        output = OutputHandler()

        text = transcriber.transcribe(audio_path.read_bytes())
        assert text

        output.copy_to_clipboard(text)
        assert pyperclip.paste() == text
```

---

## Phase 4: CI/CD Updates

### Step 4.1: GitHub Actions Workflow

**File:** `.github/workflows/test.yml`

Add integration job:

```yaml
  integration-tests:
    name: Integration Tests
    runs-on: macos-latest
    needs: unit-tests

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[all]"

      - name: Generate fixtures
        run: python tests/fixtures/audio_generator.py
        continue-on-error: true

      - name: Download whisper model
        run: python -m context_aware_whisper.model_manager download tiny.en
        continue-on-error: true

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v -m "integration and not requires_microphone"
        env:
          CAW_WHISPER_MODEL: tiny.en
```

---

## Phase 5: Verification Tools

### Step 5.1: Create verify_feature.py

**File:** `scripts/verify_feature.py`

```python
#!/usr/bin/env python
"""Run targeted tests based on changed files."""

import subprocess
import sys


def get_changed_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n')


def run_tests():
    changed = get_changed_files()
    tests = ["tests/"]

    for f in changed:
        if "transcriber" in f:
            tests.append("tests/integration/test_local_transcriber_integration.py")
        if "audio_recorder" in f:
            tests.append("tests/integration/test_audio_recorder_integration.py")

    cmd = ["pytest", "-v"] + list(set(tests))
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(run_tests())
```

---

## Running Tests

```bash
# Unit tests only (fast, no hardware)
pytest tests/ -m "not integration"

# Integration tests (needs hardware/model)
pytest tests/integration/ -m integration

# Specific integration test
pytest tests/integration/test_local_transcriber_integration.py -v

# Skip hardware-dependent tests
pytest tests/integration/ -m "integration and not requires_microphone"

# Generate audio fixtures
python tests/fixtures/audio_generator.py
```

---

## Verification Checklist

After every feature/bug fix:

- [ ] `pytest tests/ -m "not integration"` passes
- [ ] `pytest tests/integration/ -m integration` passes (if hardware available)
- [ ] Manual smoke test: Fn key → speak → verify text output
