# UI Improvements Specification

**Version:** 1.0
**Date:** 2026-01-17
**Status:** Approved for Implementation

---

## 1. Overview

This specification defines six UI/UX improvements for Context-Aware Whisper on macOS:

1. Remove duplicate system notifications during recording
2. Replace static "REC" indicator with animated audio visualizer bars
3. Change history hotkey from Cmd+H to Cmd+Shift+H
4. Add persistent menu bar icon for app visibility and control
5. Fix text output to use one-shot paste without polluting clipboard
6. Preserve focus during recording (Fn key should not steal focus from text areas)

---

## 2. Requirements

### 2.1 Remove Sidebar Notification

**Current Behavior:**
- When recording starts, macOS displays a system notification banner via `osascript`
- This duplicates the tkinter top-center indicator

**Required Behavior:**
- Only the top-center tkinter indicator should be visible during recording
- No macOS system notifications should appear

**Acceptance Criteria:**
- [ ] No notification banner appears when Fn key is pressed
- [ ] No notification banner appears when Fn key is released
- [ ] Top-center indicator continues to work normally

---

### 2.2 Animated Recording Indicator

**Current Behavior:**
- Static red rectangle (#FF3B30) with "REC" text
- 60x24 pixels, positioned top-center

**Required Behavior:**
- 4 vertical animated bars that pulse up/down like an audio visualizer
- Dark background for better visibility
- Smooth animation at ~12 FPS

**Visual Specification:**

```
┌─────────────────────────────────────┐
│         Recording Indicator         │
├─────────────────────────────────────┤
│  Background: #1C1C1E (dark slate)   │
│  Dimensions: 60x24 pixels           │
│                                     │
│  Bars:                              │
│    Count: 4                         │
│    Width: 6px each                  │
│    Gap: 3px between bars            │
│    Min Height: 4px                  │
│    Max Height: 16px                 │
│    Colors: #FF3B30, #FF6B5B,        │
│            #FF9500, #FF6B5B         │
│                                     │
│  Animation:                         │
│    Frame Rate: 12.5 FPS (80ms)      │
│    Motion: Random bounce up/down    │
│    Each bar moves independently     │
└─────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] 4 bars visible when recording state is active
- [ ] Bars animate smoothly with varying heights
- [ ] Animation stops when recording ends
- [ ] Other states (transcribing, success, error) unchanged

---

### 2.3 History Hotkey Change

**Current Behavior:**
- Cmd+H toggles history panel
- Conflicts with macOS "Hide Application" system shortcut

**Required Behavior:**
- Cmd+Shift+H toggles history panel
- No conflict with system shortcuts

**Affected Components:**
1. Hotkey detector (detection logic)
2. History panel (UI hints and key bindings)

**Acceptance Criteria:**
- [ ] Cmd+H no longer triggers history panel
- [ ] Cmd+Shift+H opens/closes history panel
- [ ] History panel footer shows "Cmd+Shift+H: Toggle"
- [ ] In-window binding (when panel focused) uses Cmd+Shift+H

---

### 2.4 Menu Bar Icon

**Purpose:**
- Provide persistent visibility that app is running
- Quick access to controls without terminal

**Required Behavior:**

| State | Icon | Menu Status |
|-------|------|-------------|
| Idle | Microphone (gray/white) | "Status: Idle" |
| Recording | Microphone (red) | "Status: Recording..." |

**Menu Structure:**
```
┌────────────────────┐
│ Status: Idle       │  ← Dynamic status text
├────────────────────┤
│ Show History       │  ← Opens history panel
├────────────────────┤
│ Quit Context-Aware Whisper      │  ← Graceful shutdown
└────────────────────┘
```

**Technical Requirements:**
- Use `rumps` library for menu bar integration
- Must coordinate with existing tkinter event loop
- Icon must update in real-time when recording starts/stops

**Acceptance Criteria:**
- [ ] Menu bar icon appears when app starts
- [ ] Icon turns red during recording
- [ ] "Show History" opens history panel
- [ ] "Quit" stops the app gracefully
- [ ] App continues to work with existing hotkey detection

---

### 2.5 Text Output Fix

**Current Behavior:**
1. Text is copied to clipboard (persists after output)
2. Text is typed character-by-character via AppleScript `keystroke`
3. Character-by-character typing is slow and causes issues in some apps

**Required Behavior:**
1. Text is pasted instantly using Cmd+V
2. Original clipboard content is restored after paste
3. User's clipboard is not polluted with transcribed text

**Flow:**
```
1. Save current clipboard content
2. Copy transcribed text to clipboard
3. Simulate Cmd+V to paste
4. Wait 50ms for paste to complete
5. Restore original clipboard content
```

**Acceptance Criteria:**
- [ ] Transcribed text appears instantly (not character-by-character)
- [ ] Clipboard contains original content after transcription
- [ ] Works in all text input fields
- [ ] Handles empty original clipboard gracefully

---

### 2.6 Preserve Focus During Recording

**Current Behavior:**
- When holding the Fn key to start recording, focus is stolen from the active text area
- This causes the transcript to be lost or pasted in the wrong location
- User has to click back into the text field after recording

**Required Behavior:**
- Holding the Fn key should NOT steal focus from any application
- The recording indicator should appear without taking focus
- Focus should remain on whatever text area the user was typing in
- When recording ends, the transcribed text should appear at the original cursor position

**Root Cause (Investigation Needed):**
- The tkinter indicator window may be taking focus when shown
- The hotkey detection mechanism may be interrupting the active application

**Possible Solutions:**
1. Set indicator window to not take focus (`-topmost` without activation)
2. Use `overrideredirect(True)` to prevent window manager focus
3. Ensure Quartz event tap doesn't modify event flow
4. Use a lower-level display method that doesn't create a focusable window

**Acceptance Criteria:**
- [ ] Focus remains in text area when Fn key is pressed
- [ ] Recording indicator appears without stealing focus
- [ ] Cursor position is preserved during recording
- [ ] Transcribed text appears at correct cursor location
- [ ] Works in Terminal, TextEdit, VS Code, browser text fields

---

## 3. Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| rumps | >=0.4.0 | macOS menu bar integration |

### Existing Dependencies (unchanged)

- pyobjc-framework-Quartz (hotkey detection)
- pyperclip (clipboard operations)
- tkinter (UI indicators)

---

## 4. File Changes Summary

| File | Action | Changes |
|------|--------|---------|
| `src/context_aware_whisper/platform/macos/hotkey_detector.py` | Modify | Remove `_show_indicator()`, add Shift flag detection |
| `src/context_aware_whisper/ui/indicator.py` | Modify | Add bar animation system |
| `src/context_aware_whisper/ui/history.py` | Modify | Update hotkey hints to Cmd+Shift+H |
| `src/context_aware_whisper/ui/menubar.py` | Create | New menu bar component |
| `src/context_aware_whisper/ui/app.py` | Modify | Integrate menu bar |
| `src/context_aware_whisper/platform/base.py` | Modify | Update output() method |
| `src/context_aware_whisper/platform/macos/output_handler.py` | Modify | Add type_text_instant() |
| `main.py` | Modify | Connect menu bar callbacks |
| `pyproject.toml` | Modify | Add rumps dependency |

---

## 5. Testing Requirements

### Unit Tests
- [ ] Test bar animation state transitions
- [ ] Test Cmd+Shift+H detection
- [ ] Test clipboard save/restore in output handler

### Integration Tests
- [ ] Full recording flow with animated indicator
- [ ] Menu bar icon state changes
- [ ] History toggle via new hotkey

### Manual Tests
- [ ] Visual verification of bar animation
- [ ] Menu bar icon color changes
- [ ] Paste works in various applications (Terminal, TextEdit, VS Code, browser)
