# Focus Preservation Fix Plan

**Issue:** When pressing Fn key to record, focus is stolen from the active text area, causing transcript to not be pasted in the correct location.

**Root Cause:** All previous approaches failed because the main app's tkinter window inherently steals focus when shown, even with NSWindow hacks applied after window creation.

**Date:** 2026-01-18
**Status:** COMPLETED - Subprocess Approach Implemented

---

## Previous Attempts (All Failed)

| Approach | Why It Failed |
|----------|---------------|
| Tkinter MacWindowStyle 'noActivates' | Doesn't prevent activation |
| PyObjC setCanBecomeKey_(False) | Applied too late, after window already created |
| NSPanel with NSNonactivatingPanelMask | Causes trace trap crash with tkinter |
| NSApplicationActivationPolicyProhibited | Makes entire app invisible, breaks other UI |

## New Solution: Subprocess Overlay

**Key Insight:** A subprocess that sets `NSApplicationActivationPolicyProhibited` BEFORE creating any windows truly cannot steal focus. The main app can't do this because tkinter is already running.

### Architecture

```
Main Process (Context-Aware Whisper)                 Subprocess (Indicator)
        |                                        |
        | -- spawn subprocess -----------------> |
        |                                        | set NSApplicationActivationPolicyProhibited
        |                                        | create floating overlay window
        | <-- ready signal --------------------- |
        |                                        |
        | -- "recording" ---------------------> |
        |                                        | show indicator at center-top
        | -- "idle" --------------------------> |
        |                                        | hide indicator
        | -- "exit" --------------------------> |
        |                                        | terminate
```

---

## Implementation Plan

### Phase 1: Create Subprocess Indicator Script

**File:** `src/context_aware_whisper/ui/subprocess_indicator.py` (NEW)

**Tasks:**
- [x] Set `NSApplicationActivationPolicyProhibited` IMMEDIATELY on import
- [x] Create PyObjC NSPanel with non-activating style
- [x] Position at screen center-top (80x30 pixels)
- [x] Implement state display (recording=red pulse, transcribing=orange, etc.)
- [x] Read commands from stdin: `recording`, `transcribing`, `idle`, `exit`
- [x] Simple event loop using select() on stdin + NSRunLoop

**Key Code Pattern:**
```python
#!/usr/bin/env python3
"""Subprocess indicator - MUST be run as separate process."""
import sys

# CRITICAL: Set policy BEFORE any other AppKit imports
if sys.platform == "darwin":
    from AppKit import NSApp, NSApplicationActivationPolicyProhibited
    NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

# Now safe to create windows...
from AppKit import NSPanel, NSMakeRect, ...

class IndicatorPanel:
    def __init__(self):
        style = NSWindowStyleMaskBorderless | NSNonactivatingPanelMask
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(...)
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setCanBecomeKey_(False)
        # ...
```

### Phase 2: Create Subprocess Client

**File:** `src/context_aware_whisper/ui/subprocess_indicator_client.py` (NEW)

**Tasks:**
- [x] `SubprocessIndicator` class
- [x] `start()` - spawn subprocess, wait for ready
- [x] `set_state(state)` - write command to subprocess stdin
- [x] `stop()` - send exit, cleanup process
- [x] Handle subprocess crashes gracefully

**Interface:**
```python
class SubprocessIndicator:
    def start(self) -> bool:
        """Launch subprocess. Returns True if successful."""

    def set_state(self, state: str) -> None:
        """Send state to subprocess: 'recording', 'transcribing', 'idle', 'error', 'success'"""

    def stop(self) -> None:
        """Terminate subprocess cleanly."""
```

### Phase 3: Integrate with UI Controller

**File:** `src/context_aware_whisper/ui/app.py` (MODIFY)

**Tasks:**
- [x] Add `_subprocess_indicator: Optional[SubprocessIndicator]`
- [x] In `start()`: Create and start subprocess indicator
- [x] In `set_state()`: Forward state to subprocess indicator
- [x] In `stop()`: Cleanup subprocess

**Changes to Context-Aware WhisperUI:**
```python
def start(self) -> None:
    # ... existing code ...

    # Launch subprocess indicator (replaces disabled tkinter indicator)
    if sys.platform == "darwin":
        try:
            from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator
            self._subprocess_indicator = SubprocessIndicator()
            self._subprocess_indicator.start()
        except Exception as e:
            print(f"[Warning] Subprocess indicator failed: {e}")
            self._subprocess_indicator = None

def set_state(self, state: str) -> None:
    # ... existing code ...

    # Forward to subprocess indicator
    if self._subprocess_indicator:
        try:
            self._subprocess_indicator.set_state(state)
        except Exception:
            pass
```

---

## Visual Design

| Property | Value |
|----------|-------|
| Position | Center-top of screen |
| Size | 80x30 pixels |
| Corner radius | 6px |
| Background | Dark (#1C1C1E, 0.9 alpha) |

| State | Appearance |
|-------|------------|
| recording | Red pulsing bar/dots |
| transcribing | Orange indicator |
| success | Green flash, then hide |
| error | Red flash, then hide |
| idle | Hidden |

---

## Files Summary

### Create
| File | Purpose |
|------|---------|
| `src/context_aware_whisper/ui/subprocess_indicator.py` | Standalone subprocess that shows overlay |
| `src/context_aware_whisper/ui/subprocess_indicator_client.py` | Client wrapper for main app |

### Modify
| File | Changes |
|------|---------|
| `src/context_aware_whisper/ui/app.py` | Integrate subprocess indicator |

---

## Testing

### Automated Tests
- [x] Test subprocess launches and responds
- [x] Test state changes propagate correctly
- [x] Test subprocess crash handling
- [x] Test rapid state changes (debouncing)

### Manual Testing Checklist

**Apps to test:**
- [ ] TextEdit - cursor in document
- [ ] VS Code - cursor in editor
- [ ] Terminal - command line input
- [ ] Safari/Chrome - text field
- [ ] Slack/Discord - message input

**Test procedure:**
1. Open app and place cursor in text input
2. Type a few characters to confirm focus
3. Press and hold Fn key
4. **CRITICAL**: Verify cursor remains in text input (type more to confirm)
5. Verify indicator appears at center-top
6. Speak some text
7. Release Fn key
8. Verify transcript appears at cursor position
9. Verify original app still has focus

---

## Success Criteria

- [ ] Focus NEVER stolen from text area when Fn pressed
- [ ] Indicator appears at center-top during recording
- [ ] Indicator visible above all other windows
- [ ] Cursor position preserved during recording
- [ ] Transcribed text inserted at correct cursor location
- [ ] Works across all tested apps
- [ ] No crashes or instability
- [ ] Subprocess cleans up properly on app exit

---

## Rollback Plan

If subprocess approach fails:
1. Keep subprocess indicator disabled
2. Fall back to menu bar animation only (already working)
3. Document limitation in README
