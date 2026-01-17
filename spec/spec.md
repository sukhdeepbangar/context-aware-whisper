# HandFree - Architecture & Specifications

## Overview
A macOS Python application that uses AirPods mute/unmute gestures to trigger fast speech-to-text transcription via Groq Whisper API.

**User Flow:**
1. User unmutes AirPods → App starts recording audio
2. User speaks naturally
3. User mutes AirPods → App stops recording, sends to Groq Whisper API (~200ms)
4. Transcription is copied to clipboard AND typed into the active app

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HANDFREE APP                                    │
│                                                                             │
│  ┌──────────────────┐                                                       │
│  │   Main Loop      │◄─────── Ctrl+C Signal Handler                        │
│  │   (main.py)      │                                                       │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│           │ initializes & coordinates                                       │
│           ▼                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        EVENT BUS / CALLBACKS                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│           │                    │                    │                       │
│           ▼                    ▼                    ▼                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  Mute Detector  │  │  Audio Recorder │  │  Output Handler │            │
│  │  (PyObjC/       │  │  (sounddevice)  │  │  (pyautogui/    │            │
│  │   AVFAudio)     │  │                 │  │   clipboard)    │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                    │                    │                       │
│           │ mute/unmute        │ audio bytes        │ text output          │
│           │ events             │                    │                       │
│           ▼                    ▼                    ▼                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     macOS System Layer                               │   │
│  │  • AVAudioApplication (mute notifications)                          │   │
│  │  • CoreAudio (microphone input)                                     │   │
│  │  • Accessibility API (keystroke injection)                          │   │
│  │  • NSPasteboard (clipboard)                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS (audio upload)
                                    ▼
                         ┌─────────────────────┐
                         │   Groq Whisper API  │
                         │   (cloud)           │
                         │                     │
                         │   Model: whisper-   │
                         │   large-v3-turbo    │
                         └─────────────────────┘
```

---

## State Machine

```
                          ┌──────────────┐
                          │              │
                          │    IDLE      │◄──────────────────────┐
                          │              │                       │
                          └──────┬───────┘                       │
                                 │                               │
                    [AirPods unmuted]                            │
                                 │                               │
                                 ▼                               │
                          ┌──────────────┐                       │
                          │              │                       │
                          │  RECORDING   │                       │
                          │              │           [transcription complete]
                          └──────┬───────┘                       │
                                 │                               │
                      [AirPods muted]                            │
                                 │                               │
                                 ▼                               │
                          ┌──────────────┐                       │
                          │              │                       │
                          │ TRANSCRIBING │───────────────────────┘
                          │              │
                          └──────────────┘
```

**State Descriptions:**
- **IDLE**: Waiting for user to unmute AirPods. No audio capture.
- **RECORDING**: Actively capturing audio from microphone into buffer.
- **TRANSCRIBING**: Audio sent to Groq API, waiting for response, then outputting text.

---

## Module Specifications

### Module 1: `mute_detector.py`

**Purpose:** Detect AirPods mute/unmute gestures using macOS AVFAudio framework.

**Dependencies:**
- `pyobjc-framework-AVFAudio`
- `pyobjc-framework-Cocoa` (for NSNotificationCenter, NSRunLoop)

**Key Classes/APIs Used:**
```python
from AVFAudio import AVAudioApplication, AVAudioSession
from Foundation import NSNotificationCenter, NSRunLoop, NSDefaultRunLoopMode
```

**Interface:**
```python
class MuteDetector:
    def __init__(self, on_mute: Callable, on_unmute: Callable):
        """
        Initialize mute detector with callbacks.

        Args:
            on_mute: Called when user mutes (press AirPods stem)
            on_unmute: Called when user unmutes
        """

    def start(self) -> None:
        """
        Start listening for mute state changes.
        Must be called from main thread.
        Sets up audio session and registers for notifications.
        """

    def stop(self) -> None:
        """
        Stop listening and clean up resources.
        Unregisters notification observer.
        """

    @property
    def is_muted(self) -> bool:
        """Current mute state."""
```

**Technical Details:**
- Uses `AVAudioApplication.shared.isInputMuted` to check current state
- Subscribes to `AVAudioApplication.inputMuteStateChangeNotification`
- Requires active audio session for notifications to work
- Audio session category: `.playAndRecord` with mode `.default`

**Notification Payload:**
```python
# The notification userInfo contains:
{
    "AVAudioApplicationMuteStateKey": NSNumber(bool)  # True if muted
}
```

---

### Module 2: `audio_recorder.py`

**Purpose:** Capture audio from microphone and store in memory buffer.

**Dependencies:**
- `sounddevice`
- `numpy`
- `scipy.io.wavfile` (for WAV export)

**Audio Specifications:**
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Sample Rate | 16000 Hz | Optimal for Whisper, reduces file size |
| Channels | 1 (mono) | Whisper expects mono |
| Bit Depth | 16-bit int | Standard for speech |
| Format | WAV | Widely supported, no compression artifacts |
| Max Duration | 300 seconds (5 min) | Practical limit, Groq allows up to 25 min |

**Interface:**
```python
class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio recorder.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Whisper)
            channels: Number of audio channels (default 1 for mono)
        """

    def start_recording(self) -> None:
        """
        Begin capturing audio from default input device.
        Audio is accumulated in internal buffer.
        """

    def stop_recording(self) -> bytes:
        """
        Stop recording and return audio as WAV bytes.

        Returns:
            WAV file contents as bytes, ready for API upload.
        """

    def get_duration(self) -> float:
        """Return current recording duration in seconds."""

    def clear_buffer(self) -> None:
        """Discard any recorded audio."""
```

**Implementation Notes:**
- Uses `sounddevice.InputStream` with callback for non-blocking capture
- Audio chunks appended to `collections.deque` for efficient memory use
- WAV encoding done in-memory using `io.BytesIO`
- Handles device selection (prefers AirPods if connected)

---

### Module 3: `transcriber.py`

**Purpose:** Send audio to Groq Whisper API and return transcription.

**Dependencies:**
- `groq` (official Python SDK)
- `httpx` (async HTTP, used by groq SDK)

**API Specifications:**
| Parameter | Value |
|-----------|-------|
| Endpoint | `https://api.groq.com/openai/v1/audio/transcriptions` |
| Model | `whisper-large-v3-turbo` |
| Max File Size | 25 MB |
| Supported Formats | wav, mp3, m4a, webm, flac, ogg |
| Response Format | JSON with `text` field |

**Interface:**
```python
class Transcriber:
    def __init__(self, api_key: str = None):
        """
        Initialize transcriber with Groq API key.

        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
        """

    def transcribe(self, audio_bytes: bytes, language: str = None) -> str:
        """
        Transcribe audio to text.

        Args:
            audio_bytes: WAV audio file as bytes
            language: Optional language code (e.g., "en"). Auto-detected if None.

        Returns:
            Transcribed text string.

        Raises:
            TranscriptionError: If API call fails.
        """

    async def transcribe_async(self, audio_bytes: bytes) -> str:
        """Async version of transcribe()."""
```

**Error Handling:**
- Retry on 429 (rate limit) with exponential backoff
- Raise `TranscriptionError` on 4xx/5xx responses
- Timeout: 30 seconds

**Response Example:**
```json
{
  "text": "Hello world, this is a test of the transcription system.",
  "x_groq": {
    "id": "req_01abc123"
  }
}
```

---

### Module 4: `output_handler.py`

**Purpose:** Copy transcription to clipboard and type into active application.

**Dependencies:**
- `pyperclip` (clipboard)
- `pyautogui` (keystroke simulation)
- `AppKit` (macOS native, via pyobjc, alternative clipboard method)

**Interface:**
```python
class OutputHandler:
    def __init__(self, type_delay: float = 0.0):
        """
        Initialize output handler.

        Args:
            type_delay: Delay between keystrokes in seconds (0 = fastest)
        """

    def output(self, text: str) -> None:
        """
        Copy text to clipboard AND type into active app.

        Args:
            text: Transcribed text to output
        """

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard only."""

    def type_text(self, text: str) -> None:
        """Type text into active application."""
```

**Implementation Options for Typing:**

1. **pyautogui.write()** - Cross-platform but may miss some characters
2. **AppleScript via osascript** - More reliable for macOS
   ```python
   osascript -e 'tell application "System Events" to keystroke "text"'
   ```
3. **CGEventCreateKeyboardEvent** - Lowest level, most reliable

**Permissions Required:**
- Accessibility permissions for keystroke injection
- User must grant in: System Settings → Privacy & Security → Accessibility

---

### Module 5: `main.py`

**Purpose:** Application entry point, coordinates all modules.

**Interface:**
```python
def main():
    """
    Main entry point.

    1. Load configuration from environment
    2. Initialize all modules
    3. Set up signal handlers (Ctrl+C)
    4. Start mute detector
    5. Run event loop
    """
```

**Configuration (Environment Variables):**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Groq API key for transcription |
| `HANDFREE_LANGUAGE` | No | auto | Language code for transcription |
| `HANDFREE_TYPE_DELAY` | No | 0 | Delay between keystrokes (seconds) |

---

## File Structure

```
handfree/
├── main.py                 # Entry point, orchestration
├── mute_detector.py        # AirPods mute state detection
├── audio_recorder.py       # Microphone audio capture
├── transcriber.py          # Groq Whisper API client
├── output_handler.py       # Clipboard + auto-typing
├── config.py               # Configuration loading
├── exceptions.py           # Custom exceptions
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment file
├── spec/
│   └── spec.md             # This file
├── plan/
│   └── implementation_plan.md
└── README.md               # Setup & usage instructions
```

---

## Dependencies (requirements.txt)

```
# macOS framework bindings
pyobjc-framework-AVFAudio>=10.0
pyobjc-framework-Cocoa>=10.0

# Audio recording
sounddevice>=0.4.6
numpy>=1.24.0
scipy>=1.11.0

# Groq API
groq>=0.4.0

# Output handling
pyperclip>=1.8.2
pyautogui>=0.9.54

# Environment management
python-dotenv>=1.0.0
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Mute detection latency | < 50ms | Time from stem press to callback |
| Audio buffer overhead | < 10MB | For 5 minutes of audio |
| Transcription latency | < 500ms | Groq API round-trip for 30s audio |
| Total end-to-end latency | < 1 second | From mute press to text appearing |

---

## Security Considerations

1. **API Key Storage**: Use environment variable, never hardcode
2. **Audio Data**: Audio is sent to Groq cloud; not stored locally
3. **Permissions**: App requires microphone + accessibility access
4. **No Persistent Storage**: No audio files saved to disk by default

---

## Fallback Plan: Global Hotkey

If AirPods mute detection doesn't work reliably, implement a global hotkey trigger:

**Alternative Implementation:**
- Use `pynput` library to listen for global hotkeys
- Double-tap `fn` key (like Wispr Flow) or custom combo
- Same state machine, different trigger

```python
from pynput import keyboard

class HotkeyDetector:
    def __init__(self, on_toggle):
        self.on_toggle = on_toggle
        self.listener = keyboard.GlobalHotKeys({
            '<cmd>+<shift>+r': self.on_toggle  # Example hotkey
        })

    def start(self):
        self.listener.start()
```

This provides a reliable backup if the AirPods API proves unreliable.
