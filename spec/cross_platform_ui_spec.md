# Context-Aware Whisper: Cross-Platform & UI Specification

**Version**: 1.0
**Date**: January 2026
**Status**: Draft

---

## Overview

This specification describes two major features for Context-Aware Whisper:

1. **Cross-Platform Support** - Enable Context-Aware Whisper to run on Windows and Linux in addition to macOS
2. **Visual UI** - Add a recording indicator and transcription history panel

---

## Feature 1: Cross-Platform Support

### 1.1 Background

Context-Aware Whisper currently uses macOS-specific APIs:
- **Quartz CGEventTap** - For Fn/Globe key detection
- **osascript/AppleScript** - For typing text into applications

### 1.2 Requirements

#### 1.2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CP-1 | Application shall run on Windows 10/11 | Must |
| CP-2 | Application shall run on Linux (Ubuntu 22.04+, Fedora 38+) | Must |
| CP-3 | Hotkey detection shall work on all platforms | Must |
| CP-4 | Text output (typing) shall work on all platforms | Must |
| CP-5 | Clipboard operations shall work on all platforms | Must |
| CP-6 | Platform-specific features shall have clear documentation | Should |
| CP-7 | Platform shall be auto-detected at runtime | Must |

#### 1.2.2 Hotkey Requirements

| Platform | Primary Hotkey | Behavior |
|----------|---------------|----------|
| macOS | Fn/Globe key (keycode 63) | Hold to record, release to transcribe |
| Windows | Ctrl+Shift+Space | Hold to record, release to transcribe |
| Linux | Ctrl+Shift+Space | Hold to record, release to transcribe |

**Note**: The Fn key is handled at BIOS/firmware level on Windows/Linux and cannot be detected by software. Therefore, an alternative hotkey is required.

#### 1.2.3 Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| CP-NF-1 | macOS-specific dependencies shall be optional (not required on Windows/Linux) |
| CP-NF-2 | No degradation in performance on any platform |
| CP-NF-3 | Consistent user experience across platforms where possible |

### 1.3 Architecture

#### 1.3.1 Platform Abstraction Layer

```
src/context_aware_whisper/platform/
├── __init__.py          # Platform detection + factory functions
├── base.py              # Abstract base classes
├── macos/
│   ├── __init__.py
│   ├── hotkey_detector.py   # Fn key via CGEventTap
│   └── output_handler.py    # AppleScript
├── windows/
│   ├── __init__.py
│   ├── hotkey_detector.py   # pynput-based
│   └── output_handler.py    # pynput-based
└── linux/
    ├── __init__.py
    ├── hotkey_detector.py   # pynput-based
    └── output_handler.py    # pynput/xdotool
```

#### 1.3.2 Abstract Interfaces

```python
class HotkeyDetectorBase(ABC):
    def __init__(self, on_start: Callable, on_stop: Callable): ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_hotkey_description(self) -> str: ...

class OutputHandlerBase(ABC):
    def copy_to_clipboard(self, text: str) -> None: ...
    def type_text(self, text: str) -> None: ...
    def type_text_via_paste(self, text: str) -> None: ...
    def output(self, text: str, use_paste: bool = False) -> None: ...
```

#### 1.3.3 Factory Functions

```python
def get_platform() -> str:
    """Returns 'macos', 'windows', 'linux', or 'unknown'"""

def create_hotkey_detector(on_start, on_stop) -> HotkeyDetectorBase:
    """Creates platform-appropriate hotkey detector"""

def create_output_handler(type_delay: float = 0.0) -> OutputHandlerBase:
    """Creates platform-appropriate output handler"""

def is_mute_detector_available() -> bool:
    """Returns True only on macOS"""
```

### 1.4 Dependencies

#### 1.4.1 Core Dependencies (All Platforms)
- `pynput>=1.7.6` - Keyboard detection and simulation
- `pyperclip>=1.8.2` - Clipboard operations
- `sounddevice>=0.4.6` - Audio recording
- `groq>=0.4.0` - Transcription API

#### 1.4.2 Optional Dependencies (macOS Only)
- `pyobjc-core>=9.0`
- `pyobjc-framework-Cocoa>=9.0`
- `pyobjc-framework-AVFoundation>=9.0`

---

## Feature 2: Visual UI

### 2.1 Background

Current feedback mechanisms:
- Console output (`[Recording]`, `[Transcribing]`, etc.)
- macOS system notifications via osascript (inconsistent visibility)
- No transcription history

### 2.2 Requirements

#### 2.2.1 Recording Indicator Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| UI-1 | Display visual indicator when recording | Must |
| UI-2 | Indicator shall be always-on-top | Must |
| UI-3 | Indicator shall be positioned at top-center of screen | Must |
| UI-4 | Indicator shall show different states: idle, recording, transcribing, success, error | Must |
| UI-5 | Indicator shall be minimal and non-intrusive (~60x24 pixels) | Should |
| UI-6 | Indicator shall be semi-transparent when idle | Should |

#### 2.2.2 State Definitions

| State | Color | Text | Behavior |
|-------|-------|------|----------|
| idle | Dark gray / hidden | - | Hidden or very dim |
| recording | Red (#FF3B30) | "REC" | Visible, optional pulse animation |
| transcribing | Orange (#FF9500) | "..." | Visible |
| success | Green (#34C759) | "OK" | Flash briefly, then return to idle |
| error | Red (#FF3B30) | "ERR" | Flash briefly, then return to idle |

#### 2.2.3 History Panel Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| UI-10 | Store transcription history persistently | Must |
| UI-11 | Display scrollable list of recent transcriptions | Must |
| UI-12 | Show timestamp and text for each entry | Must |
| UI-13 | Allow copying individual entries to clipboard | Must |
| UI-14 | Toggle history panel with hotkey (Ctrl+H) | Should |
| UI-15 | Support searching through history | Nice to have |
| UI-16 | Limit stored entries to prevent unbounded growth | Must |

#### 2.2.4 Storage Requirements

| ID | Requirement |
|----|-------------|
| UI-20 | Use SQLite for persistence |
| UI-21 | Store in `~/.context_aware_whisper/history.db` |
| UI-22 | Schema: id, text, timestamp, duration_seconds, language |
| UI-23 | Keep maximum 1000 entries (delete oldest when exceeded) |

### 2.3 UI Framework

**Selected**: tkinter

**Rationale**:
- Built into Python standard library (no extra dependencies)
- Cross-platform (works on macOS, Windows, Linux)
- Lightweight and fast startup
- Sufficient for minimal indicator UI

**Alternatives Considered**:
- PyQt/PySide: Too heavy (~100MB), licensing concerns
- Dear PyGui: Extra dependency, less mature
- Native overlays: Requires platform-specific code

### 2.4 Architecture

#### 2.4.1 File Structure

```
src/context_aware_whisper/
├── ui/
│   ├── __init__.py
│   ├── indicator.py      # RecordingIndicator class
│   ├── history.py        # HistoryPanel class
│   └── app.py            # Context-Aware WhisperUI controller
├── storage/
│   ├── __init__.py
│   └── history_store.py  # HistoryStore class (SQLite)
```

#### 2.4.2 Component Interfaces

```python
class RecordingIndicator:
    def __init__(self, width: int = 60, height: int = 24): ...
    def set_state(self, state: str) -> None: ...
    def show(self) -> None: ...
    def hide(self) -> None: ...

class HistoryPanel:
    def __init__(self, on_copy: Callable[[str], None]): ...
    def add_entry(self, entry: TranscriptionEntry) -> None: ...
    def toggle(self) -> None: ...
    def show(self) -> None: ...
    def hide(self) -> None: ...

class HistoryStore:
    def __init__(self, db_path: Path = None): ...
    def add(self, text: str, duration: float, language: str = None) -> int: ...
    def get_recent(self, limit: int = 50) -> List[TranscriptionRecord]: ...
    def search(self, query: str) -> List[TranscriptionRecord]: ...

class Context-Aware WhisperUI:
    def start(self) -> None: ...  # Starts UI in separate thread
    def set_state(self, state: str) -> None: ...  # Thread-safe
    def add_transcription(self, text: str, duration: float) -> None: ...
    def toggle_history(self) -> None: ...
    def stop(self) -> None: ...
```

### 2.5 Threading Model

- UI runs in separate daemon thread
- State updates via `root.after()` for thread-safety
- Main application thread handles hotkey detection and audio recording

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAW_HOTKEY` | Platform default | Custom hotkey (e.g., "ctrl+shift+r") |
| `CAW_UI_ENABLED` | `true` | Enable visual UI |
| `CAW_UI_POSITION` | `top-center` | Indicator position (top-center, top-right, bottom-center) |
| `CAW_HISTORY_ENABLED` | `true` | Enable transcription history |
| `CAW_HISTORY_MAX` | `1000` | Maximum history entries |

---

## Success Criteria

### Cross-Platform
1. Application starts and runs on Windows 10/11
2. Application starts and runs on Ubuntu 22.04
3. Hotkey (Ctrl+Shift+Space) triggers recording on Windows/Linux
4. Transcribed text is typed correctly on all platforms
5. Existing macOS functionality unchanged

### UI
1. Recording indicator appears at top-center when recording starts
2. Indicator shows correct state transitions
3. Transcriptions are saved to SQLite database
4. History panel shows recent transcriptions
5. Copy button works in history panel
6. History persists across application restarts
