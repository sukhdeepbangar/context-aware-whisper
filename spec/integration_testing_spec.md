# Integration Testing Specification

Specification for functional/integration testing of Context-Aware Whisper application with real hardware and whisper.cpp.

---

## Overview

**Goal:** Test actual functionality after features/bug fixes, beyond mocked unit tests.

**Scope:**
- Integration test suite with real hardware/API when available
- Test audio fixtures for reproducible transcription testing
- Focus on whisper.cpp local transcription (Groq to be removed)

---

## 1. Test Audio Fixture System

### 1.1 Fixture Categories

| Category | Duration | Purpose | Files |
|----------|----------|---------|-------|
| **Short** | 1-3 sec | Quick smoke tests, CI | `hello_world.wav`, `short_phrase.wav` |
| **Medium** | 10-15 sec | Typical dictation | `sentence.wav`, `paragraph.wav` |
| **Long** | 30-60 sec | Extended dictation | `long_dictation.wav` |
| **Edge Cases** | Various | Boundary conditions | `silence.wav`, `noise.wav`, `low_volume.wav` |
| **Special** | 5-10 sec | Punctuation, numbers | `numbers_dates.wav`, `technical_terms.wav` |

### 1.2 Fixture Storage

**Location:** `tests/fixtures/audio/`

**Manifest Schema (`manifest.json`):**
```json
{
  "fixtures": [
    {
      "filename": "hello_world.wav",
      "duration_sec": 2.0,
      "sample_rate": 16000,
      "expected_text": "Hello world",
      "expected_text_normalized": "hello world",
      "tolerance": 0.85,
      "category": "short",
      "notes": "Clear voice, neutral accent"
    }
  ]
}
```

### 1.3 Audio Requirements

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Sample Rate | 16000 Hz | Whisper standard |
| Channels | 1 (mono) | Whisper requirement |
| Bit Depth | 16-bit int | Standard for speech |
| Format | WAV | No compression artifacts |

---

## 2. Test Markers

### 2.1 Custom Pytest Markers

| Marker | Purpose | Skip Condition |
|--------|---------|----------------|
| `@pytest.mark.integration` | Integration tests | Manual opt-in |
| `@pytest.mark.requires_microphone` | Needs mic access | No input devices |
| `@pytest.mark.requires_whisper` | Needs whisper model | Model not downloaded |
| `@pytest.mark.requires_macos` | macOS-specific | Not Darwin platform |
| `@pytest.mark.requires_accessibility` | Needs a11y permission | Permission denied |
| `@pytest.mark.slow` | Takes > 5 seconds | Optional skip |

### 2.2 Auto-skip Behavior

Tests automatically skip when hardware/resources unavailable:
- No microphone → skip `requires_microphone` tests
- No whisper model → skip `requires_whisper` tests
- Not macOS → skip `requires_macos` tests
- CI environment → skip hardware-dependent tests

---

## 3. Integration Test Scenarios

### 3.1 AudioRecorder Integration

| Test | Description | Requires |
|------|-------------|----------|
| `test_real_recording_short` | Record 0.5s, validate WAV | Microphone |
| `test_real_recording_medium` | Record 5s, validate duration | Microphone |
| `test_multiple_cycles` | 3 start/stop cycles | Microphone |
| `test_captures_audio_levels` | Verify non-zero RMS | Microphone |

### 3.2 LocalTranscriber Integration

| Test | Description | Requires |
|------|-------------|----------|
| `test_transcribe_hello_world` | Transcribe fixture, verify text | Whisper model |
| `test_transcribe_silence` | Silent audio → empty result | Whisper model |
| `test_transcribe_with_fixtures` | All fixtures against manifest | Whisper model |
| `test_model_loading_latency` | Load time < 5s | Whisper model |
| `test_latency_benchmarks` | RTF < 1.0 | Whisper model |

### 3.3 OutputHandler Integration

| Test | Description | Requires |
|------|-------------|----------|
| `test_clipboard_roundtrip_unicode` | Unicode preservation | None |
| `test_clipboard_large_text` | 100KB text | None |
| `test_type_text_basic` | Keystroke typing | Accessibility |

### 3.4 End-to-End Flow

| Test | Description | Requires |
|------|-------------|----------|
| `test_complete_flow_with_fixture` | Audio file → transcription → clipboard | Whisper model |
| `test_complete_flow_real_recording` | Mic → transcription → clipboard | Microphone + Whisper |
| `test_state_transitions` | IDLE → RECORDING → TRANSCRIBING → IDLE | Whisper model |

---

## 4. Hardware Detection

### 4.1 Detection Functions

```python
def has_microphone() -> bool:
    """Check for available input devices via sounddevice."""

def has_whisper_model() -> bool:
    """Check for ~/.cache/whisper/ggml-base.en.bin"""

def has_accessibility_permission() -> bool:
    """Check via osascript System Events access."""

def is_ci_environment() -> bool:
    """Check CI, GITHUB_ACTIONS, etc. env vars."""
```

### 4.2 Skip Fixtures

```python
@pytest.fixture
def skip_if_no_microphone(has_microphone):
    if not has_microphone:
        pytest.skip("No microphone available")

@pytest.fixture
def skip_if_no_whisper(has_whisper_model):
    if not has_whisper_model:
        pytest.skip("Whisper model not downloaded")
```

---

## 5. CI/CD Integration

### 5.1 Test Tiers

| Tier | Tests | When | Where |
|------|-------|------|-------|
| Unit | All unit tests | Every PR | All runners |
| Integration (no HW) | Fixture-based transcription | Every PR | macOS runner |
| Integration (full) | All integration | Manual/Release | Local only |

### 5.2 GitHub Actions Jobs

1. **unit-tests**: Run on ubuntu, macos, windows
2. **integration-tests-macos**: Run fixture-based tests on macOS
3. **integration-tests-with-fixtures**: Download model, run transcription tests

### 5.3 Model Caching

- Use `tiny.en` model in CI (75MB, fastest)
- Cache model between runs via actions/cache
- Fallback to generated audio if fixtures missing

---

## 6. Verification Process

### 6.1 After Feature/Bug Fix

1. Run unit tests: `pytest tests/ -m "not integration"`
2. Run integration tests: `pytest tests/integration/ -m "integration"`
3. Manual smoke test with real speech

### 6.2 Smoke Test Checklist

- [ ] Start app: `python main.py`
- [ ] Press and hold Fn key
- [ ] Speak: "Hello world, this is a test"
- [ ] Release Fn key
- [ ] Verify text appears at cursor
- [ ] Verify text in clipboard
- [ ] No errors in console

---

## 7. Directory Structure

```
tests/
  conftest.py                 # Hardware detection fixtures
  integration/
    __init__.py
    conftest.py               # Integration-specific fixtures
    test_audio_recorder_integration.py
    test_local_transcriber_integration.py
    test_output_handler_integration.py
    test_e2e_flow_integration.py
  fixtures/
    audio/
      manifest.json           # Fixture metadata
      hello_world.wav
      silence.wav
      ...
    audio_generator.py        # Programmatic generation
```

---

## 8. Success Criteria

| Metric | Target |
|--------|--------|
| Integration test coverage | All major flows |
| Fixture count | 5+ audio files |
| CI pass rate | 100% for non-hardware tests |
| Skip behavior | Graceful, informative messages |
| Transcription accuracy | 85%+ word match on fixtures |
| Transcription latency | < 1s for short audio (RTF < 1.0) |
