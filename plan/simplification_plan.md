# Context-Aware Whisper Codebase Simplification Plan

**Created:** 2026-01-18
**Status:** Planned
**Target:** 40% code reduction (6,675 → ~4,000 lines)

## Overview

The Context-Aware Whisper codebase has grown complex for its core functionality. This plan details an aggressive cleanup while preserving:
- History feature (simplified)
- Multi-platform support (macOS/Windows/Linux)
- All working functionality

---

## Phase 1: Remove Deprecated/Legacy Code

**Risk:** Low
**Reduction:** ~400 lines

### Tasks

- [ ] **1.1** Delete `src/context_aware_whisper/mute_detector.py` (98 lines)
  - Marked as deprecated in code
  - Replaced by hotkey detection

- [ ] **1.2** Delete `src/context_aware_whisper/hotkey_detector.py` (107 lines)
  - Legacy macOS-only implementation
  - Replaced by `platform/macos/hotkey_detector.py`

- [ ] **1.3** Delete `src/context_aware_whisper/output_handler.py` (168 lines)
  - Legacy macOS-only implementation
  - Replaced by `platform/macos/output_handler.py`

- [ ] **1.4** Update `src/context_aware_whisper/__init__.py`
  - Remove lines 39-41:
    ```python
    # Legacy imports for backward compatibility
    from context_aware_whisper.output_handler import OutputHandler, get_clipboard_content
    from context_aware_whisper.hotkey_detector import HotkeyDetector
    ```
  - Remove lines 52-56:
    ```python
    # Mute detector (macOS only, deprecated)
    try:
        from context_aware_whisper.mute_detector import MuteDetector
    except ImportError:
        MuteDetector = None
    ```
  - Remove from `__all__`:
    - `MuteDetector`
    - `HotkeyDetector`
    - `OutputHandler`
    - `get_clipboard_content`

- [ ] **1.5** Delete `tests/test_mute_detector.py`

- [ ] **1.6** Verify: `python -c "import context_aware_whisper"`

- [ ] **1.7** Verify: `python -m pytest tests/ -x`

---

## Phase 2: Remove Disabled UI Code

**Risk:** Low
**Reduction:** ~782 lines

### Tasks

- [ ] **2.1** Delete `src/context_aware_whisper/ui/indicator.py` (593 lines)
  - Currently disabled in `app.py:111-116`
  - Comment says "TEMPORARILY DISABLED"
  - Not used - subprocess indicator is active

- [ ] **2.2** Delete `src/context_aware_whisper/ui/native_indicator.py` (189 lines)
  - Disabled due to crashes
  - Comment: "causes trace trap crash"

- [ ] **2.3** Update `src/context_aware_whisper/ui/__init__.py`
  - Remove `RecordingIndicator` import and export
  - Keep only: `Context-Aware WhisperUI`, `HistoryPanel`, `MenuBarApp`

- [ ] **2.4** Update `src/context_aware_whisper/ui/app.py`
  - Remove import: `from context_aware_whisper.ui.indicator import RecordingIndicator`
  - Remove unused variables: `self._indicator`, `self._native_indicator`
  - Remove disabled indicator logic (lines 111-116)
  - Simplify `set_state()` method to only use subprocess indicator

- [ ] **2.5** Update `src/context_aware_whisper/__init__.py`
  - Remove `RecordingIndicator` from UI imports
  - Remove from `__all__`

- [ ] **2.6** Delete related tests for removed indicator classes

- [ ] **2.7** Verify: `python -c "import context_aware_whisper"`

- [ ] **2.8** Verify: `python -m pytest tests/ -x`

---

## Phase 3: Simplify History Module

**Risk:** Medium
**Reduction:** ~230 lines (632 → ~400)

### Tasks

- [ ] **3.1** Simplify `src/context_aware_whisper/storage/history_store.py` (224 → ~150 lines)
  - Remove excessive method overloads
  - Simplify query methods
  - Remove unused pagination logic if present
  - Keep core: `add()`, `get_recent()`, `get_by_id()`, `delete()`

- [ ] **3.2** Simplify `src/context_aware_whisper/ui/history.py` (408 → ~250 lines)
  - Remove keyboard shortcut complexity
  - Simplify UI layout code
  - Keep core: list view, copy button, delete button

- [ ] **3.3** Update tests to match simplified API

- [ ] **3.4** Verify history panel still works via menu bar

---

## Phase 4: Simplify Configuration

**Risk:** Medium
**Reduction:** ~140 lines (220 → ~80)

### Tasks

- [ ] **4.1** Identify essential config options to keep:
  ```
  GROQ_API_KEY
  CAW_TRANSCRIBER (groq/local)
  CAW_WHISPER_MODEL
  CAW_TEXT_CLEANUP
  CAW_HISTORY_ENABLED
  ```

- [ ] **4.2** Remove non-essential options from `src/context_aware_whisper/config.py`:
  - `CAW_UI_POSITION` - use default "top-center"
  - `CAW_SAMPLE_RATE` - hardcode 16000
  - `CAW_TYPE_DELAY` - hardcode 0
  - `CAW_CUSTOM_HOTKEY` - remove (rarely used)
  - `CAW_USE_PASTE` - remove (deprecated)
  - `CAW_SKIP_CLIPBOARD` - remove
  - `CAW_PRESERVE_INTENTIONAL` - remove
  - `CAW_HISTORY_MAX_ENTRIES` - hardcode reasonable default

- [ ] **4.3** Remove excessive validation logic
  - Remove `VALID_UI_POSITIONS` list and validation
  - Remove `VALID_SAMPLE_RATES` validation
  - Keep only transcriber and model validation

- [ ] **4.4** Simplify `Config` dataclass to essential fields only

- [ ] **4.5** Update code that references removed config options:
  - `ui/app.py` - remove indicator_position parameter
  - `audio_recorder.py` - hardcode sample rate
  - `output_handler` - remove type_delay usage

- [ ] **4.6** Update `.env.example` to show only essential options

- [ ] **4.7** Verify: `python -m context_aware_whisper` works with simplified config

---

## Phase 5: Simplify Platform Layer

**Risk:** Medium
**Reduction:** ~500 lines

### Tasks

- [ ] **5.1** Simplify `src/context_aware_whisper/platform/__init__.py` (283 → ~100 lines)
  - Remove `PLATFORM_ERROR_MESSAGES` dict (inline messages)
  - Simplify `create_hotkey_detector()` factory
  - Simplify `create_output_handler()` factory
  - Remove verbose logging
  - Keep platform detection logic

- [ ] **5.2** Simplify `src/context_aware_whisper/platform/base.py` (181 → ~80 lines)
  - Remove verbose docstrings (keep essential ones)
  - Simplify abstract method signatures
  - Remove redundant type hints comments

- [ ] **5.3** Simplify `src/context_aware_whisper/platform/linux/output_handler.py` (478 → ~200 lines)
  - Keep primary output method per display server:
    - Wayland: wtype
    - X11: xdotool
  - Remove excessive fallback chains
  - Remove clipboard restoration complexity
  - Simplify error handling

- [ ] **5.4** Review and simplify other platform handlers if needed:
  - `platform/macos/output_handler.py` (162 lines) - likely OK
  - `platform/windows/output_handler.py` (149 lines) - likely OK

- [ ] **5.5** Verify cross-platform imports work:
  ```bash
  python -c "from context_aware_whisper.platform import create_hotkey_detector, create_output_handler"
  ```

---

## Phase 6: Simplify Exceptions

**Risk:** Low
**Reduction:** ~50 lines (75 → ~25)

### Tasks

- [ ] **6.1** Consolidate `src/context_aware_whisper/exceptions.py` to 4 exceptions:
  ```python
  class Context-Aware WhisperError(Exception):
      """Base exception for all Context-Aware Whisper errors."""
      pass

  class ConfigurationError(Context-Aware WhisperError):
      """Configuration-related errors."""
      pass

  class TranscriptionError(Context-Aware WhisperError):
      """Transcription-related errors (includes local transcription)."""
      pass

  class OutputError(Context-Aware WhisperError):
      """Output-related errors (typing, clipboard)."""
      pass
  ```

- [ ] **6.2** Remove unused exceptions:
  - `MuteDetectionError` (deprecated feature)
  - `TextCleanupError` (rarely caught)
  - `PlatformNotSupportedError` (can use ConfigurationError)
  - `LocalTranscriptionError` (merge into TranscriptionError)
  - `AudioRecordingError` (merge into Context-Aware WhisperError)

- [ ] **6.3** Update `src/context_aware_whisper/__init__.py` exports

- [ ] **6.4** Search codebase for removed exceptions and update:
  ```bash
  grep -r "MuteDetectionError\|TextCleanupError\|PlatformNotSupportedError" src/
  ```

- [ ] **6.5** Update tests that reference removed exceptions

---

## Phase 7: Test Cleanup

**Risk:** Low
**Reduction:** ~8,000 lines (18,000 → ~10,000)

### Tasks

- [ ] **7.1** Delete tests for removed code:
  - `tests/test_mute_detector.py` (if not done in Phase 1)
  - Tests for `indicator.py` classes
  - Tests for `native_indicator.py` classes

- [ ] **7.2** Delete low-value tests:
  - `tests/test_documentation.py` (~789 lines)
    - Tests that documentation files exist
    - Low value, documentation can be verified manually

- [ ] **7.3** Consolidate platform hotkey detector tests:
  - Merge into single `tests/test_hotkey_detectors.py`
  - Use `@pytest.mark.parametrize` for platform differences
  - Current files:
    - `test_macos_hotkey_detector.py` (677 lines)
    - `test_windows_hotkey_detector.py` (684 lines)
    - `test_linux_hotkey_detector.py` (742 lines)
  - Target: ~800 lines combined

- [ ] **7.4** Consolidate platform output handler tests:
  - Merge into single `tests/test_output_handlers.py`
  - Use parametrization for platform differences
  - Current files:
    - `test_macos_output_handler.py`
    - `test_windows_output_handler.py`
    - `test_linux_output_handler.py` (616 lines)
  - Target: ~600 lines combined

- [ ] **7.5** Review and simplify integration tests:
  - `test_e2e.py` (861 lines) - keep but review for redundancy
  - `test_text_cleanup_integration.py` (626 lines) - keep

- [ ] **7.6** Run full test suite: `python -m pytest tests/`

---

## Final Verification

### Tasks

- [ ] **8.1** Verify import: `python -c "import context_aware_whisper"`

- [ ] **8.2** Run all tests: `python -m pytest tests/`

- [ ] **8.3** Manual test on macOS:
  - Start app: `python -m context_aware_whisper`
  - Verify menu bar icon (🎙️) appears
  - Press Fn/Globe key to start recording
  - Speak and release to transcribe
  - Verify text is pasted to active app
  - Click menu bar → Show History
  - Verify history panel opens with transcription

- [ ] **8.4** Count final line counts:
  ```bash
  find src/context_aware_whisper -name "*.py" | xargs wc -l
  find tests -name "*.py" | xargs wc -l
  ```

- [ ] **8.5** Update spec/README.md if needed

- [ ] **8.6** Commit changes with message:
  ```
  refactor: simplify codebase - 40% reduction

  - Remove deprecated mute_detector, legacy handlers
  - Remove disabled UI indicator implementations
  - Simplify configuration (15 options → 5)
  - Simplify platform layer and exceptions
  - Consolidate and reduce test code
  ```

---

## Summary

| Phase | Description | Lines Removed | Risk |
|-------|-------------|---------------|------|
| 1 | Remove deprecated/legacy code | ~400 | Low |
| 2 | Remove disabled UI code | ~782 | Low |
| 3 | Simplify history module | ~230 | Medium |
| 4 | Simplify configuration | ~140 | Medium |
| 5 | Simplify platform layer | ~500 | Medium |
| 6 | Simplify exceptions | ~50 | Low |
| 7 | Test cleanup | ~8,000 | Low |
| **Total** | | **~10,000** | |

### Expected Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Production code | 6,675 lines | ~4,000 lines | -40% |
| Test code | 18,000 lines | ~10,000 lines | -44% |
| Config options | 15+ | 5 | -67% |
| Exception types | 8 | 4 | -50% |
| Total files | ~35 | ~28 | -20% |
