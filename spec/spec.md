# Context-Aware Whisper - Architecture & Specifications

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
│  │  Mute Detector  │  │  Audio Recorder │  │  Text Cleaner   │            │
│  │  (PyObjC/       │  │  (sounddevice)  │  │  (disfluency    │            │
│  │   AVFAudio)     │  │                 │  │   removal)      │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                    │                    │                       │
│           │                    │                    ▼                       │
│           │                    │           ┌─────────────────┐             │
│           │                    │           │  Output Handler │             │
│           │                    │           │  (pyautogui/    │             │
│           │                    │           │   clipboard)    │             │
│           │                    │           └────────┬────────┘             │
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
                                    OR
                         ┌─────────────────────┐
                         │   whisper.cpp       │
                         │   (local)           │
                         │                     │
                         │   Models: tiny,     │
                         │   base, small,      │
                         │   medium, large     │
                         └─────────────────────┘

Data Flow:
  Audio → Transcriber → TextCleaner → OutputHandler → Active App
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

### Module 3b: `local_transcriber.py` (Future: whisper.cpp)

**Purpose:** Local speech-to-text transcription using whisper.cpp for offline, private transcription.

**Dependencies:**
- `pywhispercpp` (recommended) or `whispercpp`

**Benefits Over Cloud (Groq API):**
| Aspect | Groq API | whisper.cpp |
|--------|----------|-------------|
| Privacy | Audio sent to cloud | Audio stays local |
| Offline | Requires internet | Works offline |
| Latency | Network dependent (~200ms) | Local processing (~100-500ms depending on model) |
| Cost | Free tier limits | Completely free |
| Rate Limits | 2K req/day | Unlimited |

**Model Options:**
| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| tiny.en | 75 MB | ~1 GB | Fastest | Basic | Quick drafts, low-resource |
| base.en | 142 MB | ~2 GB | Fast | Good | General use (recommended) |
| small.en | 466 MB | ~3 GB | Medium | Better | Balanced accuracy/speed |
| medium.en | 1.5 GB | ~5 GB | Slow | Great | High accuracy needed |
| large | 3 GB | ~10 GB | Slowest | Best | Maximum accuracy, multilingual |

**Interface:**
```python
class LocalTranscriber:
    def __init__(self, model_name: str = "base.en", models_dir: Optional[str] = None):
        """
        Initialize local transcriber with whisper.cpp.

        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
            models_dir: Directory for model files. Defaults to ~/.cache/whisper/
        """

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe audio to text locally.

        Args:
            audio_bytes: WAV audio file as bytes
            language: Language code (default "en")

        Returns:
            Transcribed text string.
        """

    def is_model_downloaded(self) -> bool:
        """Check if the configured model is available locally."""

    def download_model(self) -> None:
        """Download the configured model if not present."""
```

**Implementation Notes:**
- Apple Silicon Macs get Metal GPU acceleration (significantly faster)
- Models are downloaded on first use to `~/.cache/whisper/`
- Can run alongside Groq as fallback (use local when offline, cloud when available)
- Consider model warm-up on app start for faster first transcription

**Configuration:**
```python
# Environment variables
CAW_TRANSCRIBER = "local"  # or "groq" (default)
CAW_WHISPER_MODEL = "base.en"  # model to use
CAW_MODELS_DIR = "~/.cache/whisper"  # model storage location
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
| `GROQ_API_KEY` | Yes* | - | Groq API key (*required if using cloud) |
| `CAW_LANGUAGE` | No | auto | Language code for transcription |
| `CAW_TYPE_DELAY` | No | 0 | Delay between keystrokes (seconds) |
| `CAW_TRANSCRIBER` | No | groq | Transcription backend: "groq" or "local" |
| `CAW_WHISPER_MODEL` | No | base.en | Local whisper model to use |
| `CAW_MODELS_DIR` | No | ~/.cache/whisper | Directory for local models |

---

### Module 6: `text_cleanup.py`

**Purpose:** Remove speech disfluencies from transcriptions before output.

**Problem:**
Natural speech contains disfluencies that degrade written output quality:
- "Hey, um, can you... sorry, can you send this?" → "Can you send this?"
- "I I think we should" → "I think we should"
- "So like basically, you know, the thing is" → "The thing is"

**Dependencies:**
- `re` (standard library, regex patterns)
- `groq` (optional, for aggressive LLM-based cleanup)

**Cleanup Modes:**

| Mode | Description | Latency | Use Case |
|------|-------------|---------|----------|
| `off` | No cleanup, raw transcription | 0ms | Verbatim transcription needed |
| `light` | Remove obvious fillers (um, uh, ah) | <2ms | Minimal cleanup |
| `standard` | Fillers + repetitions + false starts | <5ms | **Recommended default** |
| `aggressive` | LLM-powered intelligent cleanup | 200-500ms | Professional quality |

**Disfluencies Handled:**

| Type | Examples | Handling |
|------|----------|----------|
| Filler words | um, uh, ah, er, hmm | Remove |
| Discourse markers | like, you know, I mean, basically, actually | Remove (context-aware) |
| Word repetitions | "I I think", "the the" | Deduplicate |
| False starts | "Can you... sorry, can you" | Keep correction only |
| Self-corrections | "Go left, I mean right" | Keep correction only |

**Interface:**
```python
from enum import Enum, auto
from typing import Optional

class CleanupMode(Enum):
    """Text cleanup aggressiveness levels."""
    OFF = auto()        # No cleanup
    LIGHT = auto()      # Only obvious fillers (um, uh, ah)
    STANDARD = auto()   # Fillers + repetitions + false starts
    AGGRESSIVE = auto() # LLM-powered cleanup (requires API)


class TextCleaner:
    """
    Cleans speech disfluencies from transcribed text.

    Pipeline position: Transcriber → TextCleaner → OutputHandler
    """

    def __init__(
        self,
        mode: CleanupMode = CleanupMode.STANDARD,
        api_key: Optional[str] = None,
        preserve_intentional: bool = True,
    ):
        """
        Initialize text cleaner.

        Args:
            mode: Cleanup aggressiveness level
            api_key: Groq API key (required for AGGRESSIVE mode)
            preserve_intentional: Preserve intentional patterns like "I like pizza"
        """

    def clean(self, text: str) -> str:
        """
        Clean speech disfluencies from text.

        Args:
            text: Raw transcription text

        Returns:
            Cleaned text with disfluencies removed

        Raises:
            TextCleanupError: If cleanup fails (AGGRESSIVE mode only)
        """
```

**Rule-Based Implementation (LIGHT/STANDARD):**

```python
# Filler words - removed as standalone words
FILLERS_LIGHT = {"um", "uh", "ah", "er", "hmm", "mm", "mhm"}

FILLERS_STANDARD = FILLERS_LIGHT | {
    "like", "you know", "i mean", "so", "basically",
    "actually", "literally", "right", "okay", "well",
    "anyway", "kind of", "sort of",
}

# Correction markers - text before these is likely a false start
CORRECTION_MARKERS = [
    "sorry", "i mean", "no wait", "actually",
    "let me rephrase", "correction", "rather",
]
```

**Context-Aware Rules:**
- "like" as verb preserved: "I like pizza" ✓
- "like" as filler removed: "It's like really good" → "It's really good"
- Emphasis repetition preserved: "very very important" ✓
- Stutter repetition removed: "I I think" → "I think"

**LLM-Based Implementation (AGGRESSIVE):**

```python
LLM_PROMPT = """Clean this speech transcription by removing disfluencies.

Remove: filler words, false starts, repetitions, incomplete sentences
Preserve: core meaning, natural tone, intentional emphasis

Input: {text}

Output only the cleaned text:"""

# Uses Groq's llama-3.1-8b-instant for fast, cheap cleanup
```

**Configuration (Environment Variables):**

| Variable | Default | Description |
|----------|---------|-------------|
| `CAW_TEXT_CLEANUP` | `standard` | Cleanup mode: off, light, standard, aggressive |
| `CAW_PRESERVE_INTENTIONAL` | `true` | Preserve intentional patterns |

**Integration Point:**

In `main.py` handle_stop(), between transcription and output:

```python
# After transcription
text = self.transcriber.transcribe(audio_bytes, language)

# NEW: Clean disfluencies
if self.config.text_cleanup != "off":
    text = self.text_cleaner.clean(text)

# Output cleaned text
self.output.output(text)
```

**Performance Targets:**

| Mode | Target | Max Acceptable |
|------|--------|----------------|
| OFF | 0ms | 0ms |
| LIGHT | <2ms | <5ms |
| STANDARD | <5ms | <20ms |
| AGGRESSIVE | <500ms | <1000ms |

**Edge Cases:**

| Case | Input | Expected Output |
|------|-------|-----------------|
| Empty input | "" | "" |
| All fillers | "Um uh like" | "" or original |
| Quoted speech | 'She said "um, hello"' | Preserve quoted content |
| Technical terms | "like literally equals" | Preserve technical usage |
| Non-English | Mixed language | Apply basic patterns |

---

## File Structure

```
context_aware_whisper/
├── main.py                 # Entry point, orchestration
├── mute_detector.py        # AirPods mute state detection
├── audio_recorder.py       # Microphone audio capture
├── transcriber.py          # Groq Whisper API client (cloud)
├── local_transcriber.py    # whisper.cpp client (local)
├── text_cleanup.py         # Speech disfluency removal
├── output_handler.py       # Clipboard + auto-typing
├── config.py               # Configuration loading
├── exceptions.py           # Custom exceptions
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment file
├── spec/
│   └── spec.md             # This file
├── plan/
│   ├── implementation_plan.md
│   ├── whisper_cpp_plan.md # whisper.cpp implementation plan
│   └── text_cleanup_plan.md # Text cleanup implementation plan
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

# Groq API (cloud transcription)
groq>=0.4.0

# Local transcription (optional - whisper.cpp)
# pywhispercpp>=1.0.0  # Uncomment to enable local transcription

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
2. **Audio Data**:
   - Cloud mode (Groq): Audio is sent to Groq servers
   - Local mode (whisper.cpp): Audio never leaves the machine - maximum privacy
3. **Permissions**: App requires microphone + accessibility access
4. **No Persistent Storage**: No audio files saved to disk by default
5. **Local Transcription Benefits**: For sensitive content, use `CAW_TRANSCRIBER=local`

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
