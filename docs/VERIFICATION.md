# Verification Workflow

Guide for verifying feature implementations and bug fixes in HandFree.

---

## Quick Reference

```bash
# After making changes, run:
python scripts/verify_feature.py

# Or run specific test types:
python scripts/verify_feature.py --unit        # Unit tests only
python scripts/verify_feature.py --integration # Integration tests only
python scripts/verify_feature.py --all         # Everything
```

---

## Verification Process

### 1. Automated Verification

Run the verification tool after completing your changes:

```bash
python scripts/verify_feature.py
```

The tool automatically:
- Detects which files you changed
- Maps changes to relevant tests
- Runs targeted tests
- Reports results

### 2. Test Categories

| Category | Command | Description | Hardware Needed |
|----------|---------|-------------|-----------------|
| Unit | `--unit` | Fast, isolated tests | None |
| Integration | `--integration` | Cross-module tests | Varies |
| All | `--all` | Complete test suite | Varies |

### 3. Manual Smoke Test

After automated tests pass, perform a quick manual check:

1. **Start the app:**
   ```bash
   python main.py
   ```

2. **Test basic flow:**
   - Press and hold the Fn key (macOS) or Ctrl+Shift+Space
   - Speak: "Hello world, this is a test"
   - Release the key
   - Verify text appears at cursor position
   - Verify text is in clipboard

3. **Check for errors:**
   - No errors in console
   - Recording indicator appears/disappears correctly

---

## What to Verify by Change Type

### Audio Changes (`audio_recorder.py`)

```bash
python scripts/verify_feature.py --file audio_recorder.py
```

Manual checks:
- [ ] Recording starts without delay
- [ ] Recording stops cleanly
- [ ] Audio quality is acceptable

### Transcription Changes (`local_transcriber.py`, `transcriber.py`)

```bash
python scripts/verify_feature.py --file local_transcriber.py
```

Manual checks:
- [ ] Transcription completes in reasonable time
- [ ] Text accuracy is acceptable
- [ ] No hanging or timeouts

### UI Changes (`ui/`, `subprocess_indicator.py`)

```bash
python scripts/verify_feature.py --file subprocess_indicator.py
```

Manual checks:
- [ ] Indicator appears during recording
- [ ] Indicator disappears after recording
- [ ] Focus is preserved (app doesn't steal focus)

### Output Changes (`output_handler.py`)

```bash
python scripts/verify_feature.py --file output_handler.py
```

Manual checks:
- [ ] Text appears at cursor position
- [ ] Clipboard contains transcribed text
- [ ] Unicode characters preserved

---

## Troubleshooting

### Tests Won't Run

```bash
# Ensure dependencies are installed
pip install -e ".[all]"

# Check pytest is available
python -m pytest --version
```

### Integration Tests Skip

Integration tests auto-skip when hardware/models unavailable:

```bash
# Check whisper model
ls ~/.cache/whisper/ggml-base.en.bin

# Download if missing
python -m handfree.model_manager download base.en
```

### Microphone Tests Skip

```bash
# On CI, microphone tests always skip
# Locally, ensure microphone permission is granted
```

---

## CI/CD Integration

GitHub Actions runs tests automatically on push/PR:

| Job | Tests | Runner |
|-----|-------|--------|
| `unit-tests` | Unit tests | ubuntu, macos, windows |
| `integration-tests` | Fixture-based integration | macos-latest |

To run locally what CI runs:

```bash
# Unit tests (what runs on all platforms)
pytest tests/ -m "not integration"

# Integration tests (what runs on macOS)
pytest tests/integration/ -m "integration and not requires_microphone"
```

---

## Checklist for Pull Requests

Before submitting a PR, ensure:

- [ ] `python scripts/verify_feature.py` passes
- [ ] Manual smoke test completed
- [ ] No new console errors or warnings
- [ ] Documentation updated if needed
