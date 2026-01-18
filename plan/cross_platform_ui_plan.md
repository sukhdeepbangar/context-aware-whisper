# HandFree: Cross-Platform & UI Implementation Plan

**Related Spec**: [cross_platform_ui_spec.md](../spec/cross_platform_ui_spec.md)
**Date**: January 2026
**Status**: Not Started

---

## Overview

This plan implements two features in priority order:
1. **Phase 1-2**: Visual UI (Recording Indicator + History)
2. **Phase 3-4**: Cross-Platform Support (Windows + Linux)
3. **Phase 5**: Polish and Documentation

**Rationale for UI first**: Provides immediate value on macOS while cross-platform architecture is developed.

---

## Phase 1: Recording Indicator

**Goal**: Add always-on-top visual indicator showing recording state

### Step 1.1: Create UI Module Structure
- [ ] 1.1.1 Create `src/handfree/ui/__init__.py`
- [ ] 1.1.2 Create `src/handfree/ui/indicator.py` with `RecordingIndicator` class stub
- [ ] 1.1.3 Create `src/handfree/ui/app.py` with `HandFreeUI` class stub
- [ ] 1.1.4 Update `src/handfree/__init__.py` to export UI classes

### Step 1.2: Implement Recording Indicator
- [ ] 1.2.1 Implement tkinter window setup (no decorations, always-on-top)
- [ ] 1.2.2 Position window at top-center of screen
- [ ] 1.2.3 Implement `set_state()` with color/text changes for each state
- [ ] 1.2.4 Add semi-transparency (alpha = 0.9)
- [ ] 1.2.5 Implement `show()` and `hide()` methods
- [ ] 1.2.6 Add rounded rectangle drawing for indicator background

**States to implement**:
| State | Color | Text |
|-------|-------|------|
| idle | #333333 | (hidden) |
| recording | #FF3B30 | REC |
| transcribing | #FF9500 | ... |
| success | #34C759 | OK |
| error | #FF3B30 | ERR |

### Step 1.3: Implement UI Controller
- [ ] 1.3.1 Implement `HandFreeUI.start()` to run UI in daemon thread
- [ ] 1.3.2 Implement `HandFreeUI._run_ui()` with tkinter mainloop
- [ ] 1.3.3 Implement thread-safe `set_state()` using `root.after()`
- [ ] 1.3.4 Implement `stop()` to cleanly shutdown UI thread

### Step 1.4: Integrate with Main Application
- [ ] 1.4.1 Import `HandFreeUI` in `main.py`
- [ ] 1.4.2 Initialize UI in `HandFreeApp.__init__()`
- [ ] 1.4.3 Call `ui.start()` in `HandFreeApp.run()`
- [ ] 1.4.4 Update state machine to call `ui.set_state()`:
  - `handle_unmute()` → `ui.set_state("recording")`
  - `handle_mute()` start → `ui.set_state("transcribing")`
  - `handle_mute()` success → `ui.set_state("success")` then `ui.set_state("idle")`
  - `handle_mute()` error → `ui.set_state("error")` then `ui.set_state("idle")`
- [ ] 1.4.5 Call `ui.stop()` in cleanup

### Step 1.5: Testing
- [ ] 1.5.1 Manual test: indicator appears when Fn pressed
- [ ] 1.5.2 Manual test: indicator shows correct state colors
- [ ] 1.5.3 Manual test: indicator disappears/dims when idle
- [ ] 1.5.4 Create unit tests for `RecordingIndicator` state logic (mocked tkinter)

---

## Phase 2: Transcription History

**Goal**: Persist transcriptions and display in history panel

### Step 2.1: Create Storage Module
- [x] 2.1.1 Create `src/handfree/storage/__init__.py`
- [x] 2.1.2 Create `src/handfree/storage/history_store.py`
- [x] 2.1.3 Implement `HistoryStore.__init__()` with JSONL file storage
- [x] 2.1.4 Implement JSONL format: one JSON object per line at `~/.handfree/history.jsonl`
- [x] 2.1.5 Implement `add()` method
- [x] 2.1.6 Implement `get_recent()` method
- [x] 2.1.7 Implement `search()` method
- [x] 2.1.8 Implement cleanup to limit entries to 1000

### Step 2.2: Implement History Panel
- [x] 2.2.1 Create `src/handfree/ui/history.py`
- [x] 2.2.2 Implement `HistoryPanel` as tkinter Toplevel window
- [x] 2.2.3 Add scrollable frame for entries
- [x] 2.2.4 Implement `_create_entry_widget()` for individual entry display
- [x] 2.2.5 Implement `add_entry()` method
- [x] 2.2.6 Implement `toggle()`, `show()`, `hide()` methods
- [x] 2.2.7 Add copy button functionality for each entry

### Step 2.3: Integrate History with UI Controller
- [x] 2.3.1 Add `HistoryStore` to `HandFreeUI`
- [x] 2.3.2 Add `HistoryPanel` to `HandFreeUI`
- [x] 2.3.3 Implement `add_transcription()` method (saves to store + updates panel)
- [x] 2.3.4 Implement `toggle_history()` method
- [x] 2.3.5 Load recent history on startup

### Step 2.4: Integrate with Main Application
- [x] 2.4.1 Call `ui.add_transcription()` after successful transcription in `handle_stop()`
- [x] 2.4.2 Add history toggle hotkey listener (Ctrl+H or Cmd+H)
- [x] 2.4.3 Pass recording duration to `add_transcription()`

### Step 2.5: Testing
- [x] 2.5.1 Unit tests for `HistoryStore` CRUD operations (42 tests passing)
- [ ] 2.5.2 Manual test: transcription appears in history after speaking
- [ ] 2.5.3 Manual test: history persists after app restart
- [ ] 2.5.4 Manual test: copy button copies text to clipboard
- [ ] 2.5.5 Manual test: Ctrl+H/Cmd+H toggles history panel

---

## Phase 3: Platform Abstraction

**Goal**: Create abstraction layer to support multiple platforms

### Step 3.1: Create Platform Module Structure
- [x] 3.1.1 Create `src/handfree/platform/__init__.py`
- [x] 3.1.2 Create `src/handfree/platform/base.py` with abstract classes
- [x] 3.1.3 Create `src/handfree/platform/macos/__init__.py`
- [x] 3.1.4 Create `src/handfree/platform/windows/__init__.py`
- [x] 3.1.5 Create `src/handfree/platform/linux/__init__.py`

### Step 3.2: Define Abstract Interfaces
- [x] 3.2.1 Define `HotkeyDetectorBase` ABC:
  - `__init__(on_start, on_stop)`
  - `start()` abstract
  - `stop()` abstract
  - `get_hotkey_description()` abstract
  - `is_recording` property
- [x] 3.2.2 Define `OutputHandlerBase` ABC:
  - `copy_to_clipboard(text)` abstract
  - `type_text(text)` abstract
  - `type_text_via_paste(text)` abstract
  - `output(text, use_paste)` concrete method
- [x] 3.2.3 Add `PlatformNotSupportedError` to `exceptions.py`

### Step 3.3: Implement Platform Factory
- [x] 3.3.1 Implement `get_platform()` function (returns "macos", "windows", "linux")
- [x] 3.3.2 Implement `create_hotkey_detector()` factory
- [x] 3.3.3 Implement `create_output_handler()` factory
- [x] 3.3.4 Implement `is_mute_detector_available()` function

### Step 3.4: Move macOS Code
- [x] 3.4.1 Move `hotkey_detector.py` → `platform/macos/hotkey_detector.py`
- [x] 3.4.2 Update class to inherit from `HotkeyDetectorBase`
- [x] 3.4.3 Rename class to `MacOSHotkeyDetector`
- [x] 3.4.4 Add `get_hotkey_description()` returning "Fn/Globe key"
- [x] 3.4.5 Move `mute_detector.py` → `platform/macos/mute_detector.py`
- [x] 3.4.6 Move `output_handler.py` → `platform/macos/output_handler.py`
- [x] 3.4.7 Update class to inherit from `OutputHandlerBase`
- [x] 3.4.8 Rename class to `MacOSOutputHandler`

### Step 3.5: Update Main Application
- [x] 3.5.1 Update imports to use platform factory
- [x] 3.5.2 Replace direct class instantiation with factory calls
- [x] 3.5.3 Update banner to show platform-specific hotkey description
- [x] 3.5.4 Add error handling for unsupported platforms

### Step 3.6: Testing
- [x] 3.6.1 Verify all existing tests still pass (159 tests passing)
- [x] 3.6.2 Add unit tests for platform detection (43 new tests)
- [x] 3.6.3 Add unit tests for factory functions
- [ ] 3.6.4 Manual test: app still works on macOS with Fn key

---

## Phase 4: Windows/Linux Support

**Goal**: Implement platform-specific code for Windows and Linux

### Step 4.1: Windows Hotkey Detector
- [x] 4.1.1 Create `platform/windows/hotkey_detector.py`
- [x] 4.1.2 Implement `WindowsHotkeyDetector` using pynput
- [x] 4.1.3 Use Ctrl+Shift+Space as hotkey
- [x] 4.1.4 Implement hold-to-record, release-to-transcribe logic
- [x] 4.1.5 Implement `get_hotkey_description()` returning "Ctrl+Shift+Space"

### Step 4.2: Windows Output Handler
- [x] 4.2.1 Create `platform/windows/output_handler.py`
- [x] 4.2.2 Implement `WindowsOutputHandler` using pynput.keyboard.Controller
- [x] 4.2.3 Implement `copy_to_clipboard()` using pyperclip
- [x] 4.2.4 Implement `type_text()` using keyboard.type()
- [x] 4.2.5 Implement `type_text_via_paste()` using Ctrl+V

### Step 4.3: Linux Implementation
- [x] 4.3.1 Create `platform/linux/hotkey_detector.py` (similar to Windows)
- [x] 4.3.2 Create `platform/linux/output_handler.py` (similar to Windows)
- [x] 4.3.3 Add xdotool/wtype fallback for typing if pynput fails on Wayland (37 new tests)

### Step 4.4: Update Dependencies
- [x] 4.4.1 Update `pyproject.toml`:
  - Move pyobjc packages to `[project.optional-dependencies.macos]`
  - Add pynput to core dependencies
  - Add hypothesis to dev dependencies
  - Update classifiers for cross-platform support
- [x] 4.4.2 Update `requirements.txt` for development
- [x] 4.4.3 Add dependency structure tests (test_dependencies.py)

### Step 4.5: Testing
- [ ] 4.5.1 Test on Windows 10/11 (VM or physical)
- [ ] 4.5.2 Test on Ubuntu 22.04 (VM or physical)
- [ ] 4.5.3 Verify Ctrl+Shift+Space triggers recording
- [ ] 4.5.4 Verify text is typed correctly
- [ ] 4.5.5 Verify clipboard operations work

---

## Phase 5: Polish and Documentation

**Goal**: Configuration options, refinements, and documentation

### Step 5.1: Configuration
- [x] 5.1.1 Add `HANDFREE_UI_ENABLED` env var (default: true)
- [x] 5.1.2 Add `HANDFREE_UI_POSITION` env var (default: top-center)
- [x] 5.1.3 Add `HANDFREE_HISTORY_ENABLED` env var (default: true)
- [x] 5.1.4 Add `HANDFREE_HOTKEY` env var for custom hotkey (optional)
- [x] 5.1.5 Update `config.py` to load new settings
- [x] 5.1.6 Add `HANDFREE_HISTORY_MAX` env var (default: 1000)
- [x] 5.1.7 Update `main.py` to use `Config.from_env()` consistently
- [x] 5.1.8 Add 75+ unit tests for new configuration (test_config.py)

### Step 5.2: UI Refinements
- [x] 5.2.1 Add success/error flash animation (brief green/red, then fade)
- [x] 5.2.2 Platform-specific transparency handling
- [x] 5.2.3 Ensure UI works on multi-monitor setups (use primary display)
- [x] 5.2.4 Add keyboard shortcut hints in history panel

### Step 5.3: Error Handling
- [x] 5.3.1 Graceful degradation if UI fails to initialize
- [x] 5.3.2 Clear error messages for platform-specific features
- [x] 5.3.3 Log platform detection and selected handlers
- [x] 5.3.4 Add new exception types (UIInitializationError, HotkeyDetectorError, OutputHandlerError)
- [x] 5.3.5 Add debug mode via HANDFREE_DEBUG environment variable
- [x] 5.3.6 Add 38 unit tests for error handling (test_error_handling.py)

### Step 5.4: Documentation
- [ ] 5.4.1 Update README.md with cross-platform instructions
- [ ] 5.4.2 Document Windows installation steps
- [ ] 5.4.3 Document Linux installation steps (including dependencies)
- [ ] 5.4.4 Update environment variables table
- [ ] 5.4.5 Add screenshots of UI indicator and history panel

### Step 5.5: Final Testing
- [ ] 5.5.1 Run full test suite on macOS
- [ ] 5.5.2 Run full test suite on Windows
- [ ] 5.5.3 Run full test suite on Linux
- [ ] 5.5.4 End-to-end test: record, transcribe, verify in history
- [ ] 5.5.5 Test upgrade path from previous version

---

## Files Summary

### New Files to Create

| File | Phase | Description |
|------|-------|-------------|
| `src/handfree/ui/__init__.py` | 1 | UI package |
| `src/handfree/ui/indicator.py` | 1 | Recording indicator |
| `src/handfree/ui/app.py` | 1 | UI controller |
| `src/handfree/ui/history.py` | 2 | History panel |
| `src/handfree/storage/__init__.py` | 2 | Storage package |
| `src/handfree/storage/history_store.py` | 2 | SQLite storage |
| `src/handfree/platform/__init__.py` | 3 | Platform factory |
| `src/handfree/platform/base.py` | 3 | Abstract interfaces |
| `src/handfree/platform/macos/__init__.py` | 3 | macOS package |
| `src/handfree/platform/macos/hotkey_detector.py` | 3 | Move from src/ |
| `src/handfree/platform/macos/mute_detector.py` | 3 | Move from src/ |
| `src/handfree/platform/macos/output_handler.py` | 3 | Move from src/ |
| `src/handfree/platform/windows/__init__.py` | 4 | Windows package |
| `src/handfree/platform/windows/hotkey_detector.py` | 4 | pynput-based |
| `src/handfree/platform/windows/output_handler.py` | 4 | pynput-based |
| `src/handfree/platform/linux/__init__.py` | 4 | Linux package |
| `src/handfree/platform/linux/hotkey_detector.py` | 4 | pynput-based |
| `src/handfree/platform/linux/output_handler.py` | 4 | pynput-based |

### Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `main.py` | 1, 3 | Add UI integration, use platform factory |
| `src/handfree/__init__.py` | 1, 3 | Export new classes |
| `src/handfree/config.py` | 5 | Add UI/platform config |
| `src/handfree/exceptions.py` | 3 | Add PlatformNotSupportedError |
| `pyproject.toml` | 4 | Update dependencies |
| `requirements.txt` | 4 | Update dependencies |
| `README.md` | 5 | Cross-platform docs |

---

## Progress Tracking

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Recording Indicator | Complete | UI indicator with states (idle, recording, transcribing, success, error) |
| Phase 2: Transcription History | Complete | JSONL-based storage, history panel UI, integrated with main app, history toggle hotkey (Cmd+H/Ctrl+H) |
| Phase 3: Platform Abstraction | Complete | Platform factory with macOS/Windows/Linux implementations, 43 new tests |
| Phase 4: Windows/Linux Support | Complete | All implementations done including xdotool/wtype fallback for Wayland (4.3.3), pending: VM testing (4.5) |
| Phase 5: Polish | In Progress | Step 5.1 (Configuration) complete with 75+ tests; Step 5.2 (UI Refinements) complete with 29 new tests; Step 5.3 (Error Handling) complete with 38 new tests; remaining: documentation (5.4), final testing (5.5) |
