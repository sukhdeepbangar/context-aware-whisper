# Subprocess Recording Indicator Specification

**Version:** 1.0
**Date:** 2026-01-18
**Status:** Proposed

---

## Overview

A recording indicator overlay that runs in a separate subprocess to prevent focus stealing on macOS. The subprocess sets `NSApplicationActivationPolicyProhibited` before creating any windows, ensuring it can never receive focus.

## Requirements

### Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | Display visual indicator at center-top of screen during recording |
| FR2 | Indicator must NOT steal focus from any application |
| FR3 | Show different visual states: recording, transcribing, success, error |
| FR4 | Indicator must be visible above all other windows |
| FR5 | Graceful degradation if subprocess fails to start |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR1 | State change latency < 50ms |
| NFR2 | Memory usage < 30MB for subprocess |
| NFR3 | CPU usage < 1% when idle |
| NFR4 | No visible flicker during state transitions |

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Process (Context-Aware Whisper)                  │
│                                                              │
│  ┌──────────────┐    ┌───────────────────────────────────┐ │
│  │ Context-Aware WhisperUI   │───>│ SubprocessIndicator (Client)       │ │
│  │              │    │                                    │ │
│  │ set_state()  │    │ - start()                         │ │
│  │ stop()       │    │ - set_state(state)                │ │
│  └──────────────┘    │ - stop()                          │ │
│                      └──────────────┬────────────────────┘ │
└─────────────────────────────────────│──────────────────────┘
                                      │ stdin pipe
                                      │ (commands)
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Subprocess (Indicator)                      │
│                                                              │
│  NSApplicationActivationPolicyProhibited (set at startup)   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ IndicatorPanel (NSPanel)                             │  │
│  │                                                      │  │
│  │ - NSNonactivatingPanelMask (cannot activate)        │  │
│  │ - NSFloatingWindowLevel (above all windows)         │  │
│  │ - setCanBecomeKey_(False)                           │  │
│  │ - setCanBecomeMain_(False)                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### IPC Protocol

**Transport:** stdin pipe (subprocess.Popen with stdin=PIPE)

**Commands (newline-delimited):**
```
recording\n     # Show recording state
transcribing\n  # Show transcribing state
success\n       # Flash success, then hide
error\n         # Flash error, then hide
idle\n          # Hide indicator
exit\n          # Terminate subprocess
```

**Response (stdout):**
```
ready\n         # Subprocess initialized and ready
```

## Visual Design

### Geometry

| Property | Value |
|----------|-------|
| Width | 80px |
| Height | 30px |
| Corner Radius | 6px |
| Position | Center of screen, 40px from top |

### Color Palette

| State | Background | Content |
|-------|------------|---------|
| recording | #1C1C1E (90% alpha) | Red pulsing dots (#FF3B30) |
| transcribing | #1C1C1E (90% alpha) | Orange animated dots (#FF9500) |
| success | #1C1C1E (90% alpha) | Green checkmark (#34C759) |
| error | #1C1C1E (90% alpha) | Red X (#FF3B30) |

### Animation

**Recording State:**
- 3 dots pulsing sequentially
- 150ms delay between dot pulses
- Continuous loop while in recording state

**Transcribing State:**
- 3 dots animating left-to-right
- 100ms delay between dot movements
- Continuous loop while in transcribing state

**Success/Error States:**
- Display for 800ms
- Fade out over 200ms
- Transition to hidden

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Subprocess fails to start | Log warning, continue without indicator |
| Subprocess crashes | Log warning, attempt restart once |
| Subprocess unresponsive | Kill after 2s timeout, restart |
| Invalid command | Subprocess ignores, logs to stderr |

## Testing Strategy

### Unit Tests
- Command parsing
- State transitions
- IPC protocol

### Integration Tests
- Subprocess lifecycle (start/stop)
- State propagation latency
- Crash recovery

### Manual Tests
- Focus preservation in 5+ apps
- Visual appearance verification
- Multi-monitor support

## Security Considerations

- Subprocess runs with same privileges as parent
- No external network access
- No file system access beyond code
- IPC via stdin only (no sockets)

## Future Enhancements

1. **Cross-platform support**: Implement Windows/Linux subprocess indicators
2. **Configurable position**: Allow user to choose indicator position
3. **Custom themes**: Support light/dark mode and custom colors
4. **Accessibility**: Add VoiceOver announcements for state changes
