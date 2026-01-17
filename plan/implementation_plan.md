# HandFree - Step-by-Step Implementation Plan

This document provides a detailed step-by-step guide to implement the HandFree application. For architecture and specifications, see `../spec/spec.md`.

---

## Master Todo Checklist

Use this checklist to track progress and resume from any point.

### Step 1: Project Initialization
- [x] 1.1 Create directory structure (`spec/`, `plan/`, root files)
- [x] 1.2 Create virtual environment (`python3 -m venv venv`)
- [x] 1.3 Create `requirements.txt`
- [x] 1.4 Install dependencies (`pip install -r requirements.txt`)
- [x] 1.5 Create `.env` file with `GROQ_API_KEY`
- [x] 1.6 Create `.env.example` template
- [x] 1.7 Verify: `python -c "import sounddevice; print('OK')"`
- [x] 1.8 Verify: `python -c "from AVFAudio import AVAudioApplication; print('OK')"`

### Step 2: Mute Detector
- [x] 2.1 Create `mute_detector.py` with `MuteDetector` class
- [x] 2.2 Implement `__init__` with callbacks
- [x] 2.3 Implement `start()` - audio session setup
- [x] 2.4 Implement `_handle_notification()` - mute state handler
- [x] 2.5 Implement `stop()` - cleanup
- [x] 2.6 Create `test_mute_detector.py`
- [x] 2.7 Verify: Connect AirPods, press stem, see MUTED/UNMUTED output

### Step 3: Audio Recorder
- [x] 3.1 Create `audio_recorder.py` with `AudioRecorder` class
- [x] 3.2 Implement `__init__` with sample rate config
- [x] 3.3 Implement `_audio_callback()` - buffer chunks
- [x] 3.4 Implement `start_recording()` - start stream
- [x] 3.5 Implement `stop_recording()` - return WAV bytes
- [x] 3.6 Implement `get_duration()` and `clear_buffer()`
- [x] 3.7 Create `test_audio_recorder.py`
- [x] 3.8 Verify: Record 3s audio, save to file, playback sounds clear

### Step 4: Transcriber
- [x] 4.1 Create `transcriber.py` with `Transcriber` class
- [x] 4.2 Implement `__init__` - Groq client setup
- [x] 4.3 Implement `transcribe()` with retry logic
- [x] 4.4 Create `TranscriptionError` exception
- [x] 4.5 Create `test_transcriber.py`
- [x] 4.6 Verify: Transcribe test audio, text matches spoken content
- [x] 4.7 Verify: Latency < 500ms

### Step 5: Output Handler
- [x] 5.1 Create `output_handler.py` with `OutputHandler` class
- [x] 5.2 Implement `copy_to_clipboard()` using pyperclip
- [x] 5.3 Implement `type_text()` using AppleScript
- [x] 5.4 Implement `output()` - does both clipboard + type
- [x] 5.5 Create `test_output_handler.py`
- [x] 5.6 Verify: Text appears in TextEdit AND clipboard

### Step 6: Main Loop
- [x] 6.1 Create `main.py` with `HandFreeApp` class
- [x] 6.2 Implement `__init__` - initialize all modules
- [x] 6.3 Implement `handle_unmute()` - start recording
- [x] 6.4 Implement `handle_mute()` - stop, transcribe, output
- [x] 6.5 Implement `run()` - macOS event loop
- [x] 6.6 Implement `stop()` - graceful shutdown
- [x] 6.7 Add signal handlers (Ctrl+C)
- [x] 6.8 Verify: Full flow works end-to-end (178 unit tests pass)

### Step 7: Configuration & Polish
- [x] 7.1 Create `config.py` with `Config` class
- [x] 7.2 Create `exceptions.py` with custom exceptions
- [x] 7.3 Add error handling to all modules
- [x] 7.4 Add user-friendly console output
- [x] 7.5 Verify: Missing API key shows helpful error

### Step 8: End-to-End Testing
- [x] 8.1 Test basic flow: unmute → speak → mute → text appears
- [x] 8.2 Test empty recording: unmute → immediately mute
- [x] 8.3 Test long recording: 60 seconds of speech
- [x] 8.4 Test special characters: punctuation preserved
- [x] 8.5 Test quick succession: multiple cycles
- [x] 8.6 Test no AirPods: graceful error message
- [x] 8.7 Verify: 265 tests total (261 passed, 4 skipped for hardware)

### Step 9: Documentation
- [x] 9.1 Create `README.md` with installation instructions
- [x] 9.2 Document usage instructions
- [x] 9.3 Document permissions setup
- [x] 9.4 Document troubleshooting
- [x] 9.5 Verify: 44 documentation tests pass

---

## Detailed Implementation

---

## Step 1: Project Initialization

**Goal:** Set up project structure, virtual environment, and dependencies.

**Tasks:**
1. Create directory structure
2. Create virtual environment
3. Create requirements.txt
4. Install dependencies
5. Create .env file with GROQ_API_KEY
6. Create empty module files

**Commands:**
```bash
cd /Users/sukhdeepsingh/projects/ClaudeProjects/handfree
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Files to Create:**

`requirements.txt`:
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

`.env`:
```
GROQ_API_KEY=your_api_key_here
```

**Verification:**
- `python -c "import sounddevice; print(sounddevice.query_devices())"` shows audio devices
- `python -c "from AVFAudio import AVAudioApplication; print('OK')"` imports successfully

---

## Step 2: Implement Mute Detector

**Goal:** Detect AirPods mute/unmute gestures.

**File:** `mute_detector.py`

**Implementation Details:**

1. Create `MuteDetector` class with callbacks
2. Set up AVAudioSession with `.playAndRecord` category
3. Activate the audio session
4. Register observer for `inputMuteStateChangeNotification`
5. Implement notification handler to extract mute state
6. Call appropriate callback (on_mute or on_unmute)

**Complete Implementation:**
```python
"""
Mute Detector Module
Detects AirPods mute/unmute gestures using macOS AVFAudio framework.
Requires macOS 14 (Sonoma) or later.
"""

from typing import Callable, Optional
from AVFAudio import AVAudioApplication, AVAudioSession
from Foundation import NSNotificationCenter, NSObject


class MuteDetector:
    """Detects AirPods mute/unmute gestures via AVAudioApplication API."""

    def __init__(self, on_mute: Callable[[], None], on_unmute: Callable[[], None]):
        """
        Initialize mute detector with callbacks.

        Args:
            on_mute: Called when user mutes (press AirPods stem)
            on_unmute: Called when user unmutes
        """
        self.on_mute = on_mute
        self.on_unmute = on_unmute
        self._observer: Optional[object] = None
        self._session: Optional[AVAudioSession] = None
        self._last_mute_state: Optional[bool] = None

    def _handle_notification(self, notification) -> None:
        """Handle mute state change notification."""
        # Get current mute state
        app = AVAudioApplication.sharedInstance()
        is_muted = app.isInputMuted()

        # Only trigger callback if state actually changed
        if is_muted != self._last_mute_state:
            self._last_mute_state = is_muted
            if is_muted:
                self.on_mute()
            else:
                self.on_unmute()

    def start(self) -> None:
        """
        Start listening for mute state changes.
        Must be called from main thread.
        """
        # Set up audio session
        self._session = AVAudioSession.sharedInstance()

        # Configure session for recording
        success, error = self._session.setCategory_mode_options_error_(
            "AVAudioSessionCategoryPlayAndRecord",
            "AVAudioSessionModeDefault",
            0,
            None
        )
        if not success:
            raise RuntimeError(f"Failed to set audio session category: {error}")

        # Activate session
        success, error = self._session.setActive_error_(True, None)
        if not success:
            raise RuntimeError(f"Failed to activate audio session: {error}")

        # Get initial mute state
        app = AVAudioApplication.sharedInstance()
        self._last_mute_state = app.isInputMuted()

        # Register for mute notifications
        center = NSNotificationCenter.defaultCenter()
        self._observer = center.addObserverForName_object_queue_usingBlock_(
            "AVAudioApplicationInputMuteStateChangeNotification",
            None,
            None,
            self._handle_notification
        )

        print(f"Mute detector started. Initial state: {'muted' if self._last_mute_state else 'unmuted'}")

    def stop(self) -> None:
        """Stop listening and clean up resources."""
        if self._observer:
            center = NSNotificationCenter.defaultCenter()
            center.removeObserver_(self._observer)
            self._observer = None

        if self._session:
            self._session.setActive_error_(False, None)
            self._session = None

    @property
    def is_muted(self) -> bool:
        """Current mute state."""
        app = AVAudioApplication.sharedInstance()
        return app.isInputMuted()
```

**Verification:**
- Create test script that prints "MUTED" / "UNMUTED" on state changes
- Connect AirPods, press stem, verify output

**Test Script:**
```python
# test_mute_detector.py
from mute_detector import MuteDetector
from Foundation import NSRunLoop, NSDate, NSDefaultRunLoopMode

def on_mute():
    print("MUTED")

def on_unmute():
    print("UNMUTED")

detector = MuteDetector(on_mute=on_mute, on_unmute=on_unmute)
detector.start()

print("Listening for mute events. Press Ctrl+C to exit.")
try:
    while True:
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode,
            NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )
except KeyboardInterrupt:
    detector.stop()
    print("Stopped.")
```

---

## Step 3: Implement Audio Recorder

**Goal:** Capture microphone audio to memory buffer.

**File:** `audio_recorder.py`

**Implementation Details:**

1. Create `AudioRecorder` class
2. Initialize `sounddevice.InputStream` with callback
3. Callback appends audio chunks to deque
4. `start_recording()` starts the stream
5. `stop_recording()` stops stream and encodes to WAV bytes
6. Use `scipy.io.wavfile.write()` with `io.BytesIO` for in-memory WAV

**Complete Implementation:**
```python
"""
Audio Recorder Module
Captures audio from microphone and stores in memory buffer.
"""

import io
from collections import deque
from typing import Optional

import numpy as np
import sounddevice as sd
from scipy.io import wavfile


class AudioRecorder:
    """Records audio from microphone to memory buffer."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio recorder.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Whisper)
            channels: Number of audio channels (default 1 for mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer: deque = deque()
        self.stream: Optional[sd.InputStream] = None
        self._is_recording = False

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info, status) -> None:
        """Callback for audio stream - appends chunks to buffer."""
        if status:
            print(f"Audio callback status: {status}")
        self.buffer.append(indata.copy())

    def start_recording(self) -> None:
        """Begin capturing audio from default input device."""
        if self._is_recording:
            return

        self.buffer.clear()
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            callback=self._audio_callback
        )
        self.stream.start()
        self._is_recording = True

    def stop_recording(self) -> bytes:
        """
        Stop recording and return audio as WAV bytes.

        Returns:
            WAV file contents as bytes, ready for API upload.
        """
        if not self._is_recording:
            return b''

        self.stream.stop()
        self.stream.close()
        self.stream = None
        self._is_recording = False

        if not self.buffer:
            return b''

        # Combine all chunks
        audio_data = np.concatenate(list(self.buffer))

        # Encode as WAV in memory
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, self.sample_rate, audio_data)
        wav_buffer.seek(0)

        return wav_buffer.getvalue()

    def get_duration(self) -> float:
        """Return current recording duration in seconds."""
        if not self.buffer:
            return 0.0
        total_samples = sum(chunk.shape[0] for chunk in self.buffer)
        return total_samples / self.sample_rate

    def clear_buffer(self) -> None:
        """Discard any recorded audio."""
        self.buffer.clear()

    @property
    def is_recording(self) -> bool:
        """Whether recording is currently active."""
        return self._is_recording
```

**Verification:**
- Record 3 seconds of audio
- Save to file, play back to confirm quality
- Check file size is reasonable (~96KB for 3 seconds at 16kHz)

**Test Script:**
```python
# test_audio_recorder.py
import time
from audio_recorder import AudioRecorder

recorder = AudioRecorder()

print("Recording for 3 seconds...")
recorder.start_recording()
time.sleep(3)
audio_bytes = recorder.stop_recording()

print(f"Recorded {len(audio_bytes)} bytes ({recorder.get_duration():.1f}s)")

# Save for playback verification
with open("test_recording.wav", "wb") as f:
    f.write(audio_bytes)
print("Saved to test_recording.wav - play to verify quality")
```

---

## Step 4: Implement Transcriber

**Goal:** Send audio to Groq API and get transcription.

**File:** `transcriber.py`

**Implementation Details:**

1. Create `Transcriber` class
2. Initialize Groq client with API key
3. Implement `transcribe()` method
4. Handle errors and implement retry logic
5. Return transcribed text

**Complete Implementation:**
```python
"""
Transcriber Module
Sends audio to Groq Whisper API and returns transcription.
"""

import os
import time
from typing import Optional

from groq import Groq


class TranscriptionError(Exception):
    """Raised when transcription fails."""
    pass


class Transcriber:
    """Transcribes audio using Groq Whisper API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize transcriber with Groq API key.

        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        self.client = Groq(api_key=self.api_key)
        self.model = "whisper-large-v3-turbo"

    def transcribe(self, audio_bytes: bytes, language: Optional[str] = None,
                   max_retries: int = 3) -> str:
        """
        Transcribe audio to text.

        Args:
            audio_bytes: WAV audio file as bytes
            language: Optional language code (e.g., "en"). Auto-detected if None.
            max_retries: Maximum number of retry attempts on failure.

        Returns:
            Transcribed text string.

        Raises:
            TranscriptionError: If API call fails after retries.
        """
        if not audio_bytes:
            return ""

        last_error = None
        for attempt in range(max_retries):
            try:
                transcription = self.client.audio.transcriptions.create(
                    file=("audio.wav", audio_bytes),
                    model=self.model,
                    language=language,
                    response_format="text"
                )
                # The response is the text directly when response_format="text"
                return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()

            except Exception as e:
                last_error = e
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    # Other error - retry immediately
                    print(f"Transcription error (attempt {attempt + 1}): {e}")

        raise TranscriptionError(f"Transcription failed after {max_retries} attempts: {last_error}")
```

**Verification:**
- Use audio from Step 3
- Send to API, print response
- Confirm text matches spoken content
- Measure latency (should be < 500ms)

**Test Script:**
```python
# test_transcriber.py
import time
from transcriber import Transcriber

# Load test audio (from Step 3)
with open("test_recording.wav", "rb") as f:
    audio_bytes = f.read()

transcriber = Transcriber()

print("Transcribing...")
start = time.time()
text = transcriber.transcribe(audio_bytes)
elapsed = time.time() - start

print(f"Transcription: {text}")
print(f"Latency: {elapsed*1000:.0f}ms")
```

---

## Step 5: Implement Output Handler

**Goal:** Copy text to clipboard and type into active app.

**File:** `output_handler.py`

**Implementation Details:**

1. Create `OutputHandler` class
2. Implement `copy_to_clipboard()` using pyperclip
3. Implement `type_text()` using AppleScript (most reliable for macOS)
4. Implement `output()` that does both
5. Handle special characters properly

**Complete Implementation:**
```python
"""
Output Handler Module
Copies transcription to clipboard and types into active application.
"""

import subprocess
from typing import Optional

import pyperclip


class OutputHandler:
    """Handles output of transcribed text to clipboard and active app."""

    def __init__(self, type_delay: float = 0.0):
        """
        Initialize output handler.

        Args:
            type_delay: Delay between keystrokes in seconds (0 = fastest)
        """
        self.type_delay = type_delay

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        pyperclip.copy(text)

    def type_text(self, text: str) -> None:
        """
        Type text into active application using AppleScript.

        This method is more reliable than pyautogui on macOS.
        """
        if not text:
            return

        # Escape special characters for AppleScript
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')

        # Use AppleScript to type the text
        script = f'tell application "System Events" to keystroke "{escaped}"'

        try:
            subprocess.run(
                ['osascript', '-e', script],
                check=True,
                capture_output=True,
                timeout=10
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to type text: {e.stderr.decode()}")
        except subprocess.TimeoutExpired:
            print("Typing timed out")

    def output(self, text: str) -> None:
        """
        Copy text to clipboard AND type into active app.

        Args:
            text: Transcribed text to output
        """
        if not text:
            return

        # Copy to clipboard first (always works)
        self.copy_to_clipboard(text)

        # Then type into active app
        self.type_text(text)
```

**Verification:**
- Open TextEdit
- Run `output("Hello world")`
- Verify text appears in TextEdit AND is in clipboard

**Test Script:**
```python
# test_output_handler.py
import time
from output_handler import OutputHandler

handler = OutputHandler()

print("Open TextEdit and click in the document.")
print("You have 3 seconds...")
time.sleep(3)

handler.output("Hello, this is a test of the HandFree output handler!")

import pyperclip
clipboard = pyperclip.paste()
print(f"Clipboard contains: {clipboard}")
```

---

## Step 6: Implement Main Loop

**Goal:** Orchestrate all modules and handle state transitions.

**File:** `main.py`

**Implementation Details:**

1. Load environment variables
2. Initialize all modules
3. Define state machine callbacks
4. Start mute detector
5. Run macOS event loop
6. Handle Ctrl+C gracefully

**Complete Implementation:**
```python
"""
HandFree - AirPods-Triggered Speech-to-Text

Main application entry point.
"""

import signal
import sys
from dotenv import load_dotenv
from Foundation import NSRunLoop, NSDate, NSDefaultRunLoopMode

from mute_detector import MuteDetector
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from output_handler import OutputHandler


class HandFreeApp:
    """Main application class coordinating all modules."""

    def __init__(self):
        """Initialize all components."""
        # Load environment variables
        load_dotenv()

        # Initialize modules
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.output = OutputHandler()
        self.detector = MuteDetector(
            on_mute=self.handle_mute,
            on_unmute=self.handle_unmute
        )

        self.is_recording = False
        self._running = True

    def handle_unmute(self) -> None:
        """Called when user unmutes AirPods - start recording."""
        print("🎤 Recording started...")
        self.is_recording = True
        self.recorder.start_recording()

    def handle_mute(self) -> None:
        """Called when user mutes AirPods - stop, transcribe, output."""
        if not self.is_recording:
            return

        print("⏹️  Recording stopped, transcribing...")
        self.is_recording = False

        # Get recorded audio
        audio_bytes = self.recorder.stop_recording()

        if not audio_bytes:
            print("⚠️  No audio recorded")
            return

        # Transcribe
        try:
            text = self.transcriber.transcribe(audio_bytes)
            if text:
                print(f"📝 Transcription: {text}")
                self.output.output(text)
            else:
                print("⚠️  No transcription returned")
        except Exception as e:
            print(f"❌ Transcription error: {e}")

    def run(self) -> None:
        """Start the application and run the event loop."""
        self.detector.start()

        print("=" * 50)
        print("HandFree is running!")
        print("=" * 50)
        print("")
        print("• Unmute AirPods (press stem) to START recording")
        print("• Mute AirPods (press stem again) to STOP and transcribe")
        print("• Text will be typed at cursor and copied to clipboard")
        print("")
        print("Press Ctrl+C to exit.")
        print("=" * 50)

        # Run macOS event loop
        while self._running:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )

    def stop(self) -> None:
        """Stop the application gracefully."""
        self._running = False
        self.detector.stop()
        print("\nHandFree stopped. Goodbye!")


def main():
    """Main entry point."""
    app = HandFreeApp()

    def signal_handler(sig, frame):
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        app.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Verification:**
- Run `python main.py`
- Unmute AirPods, speak "Hello world"
- Mute AirPods
- Verify "Hello world" is typed into active app and in clipboard

---

## Step 7: Add Configuration & Polish

**Goal:** Add configuration file, error handling, and user feedback.

**File:** `config.py`

**Complete Implementation:**
```python
"""
Configuration Module
Loads settings from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables."""

    # Required
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    # Optional
    LANGUAGE = os.environ.get("HANDFREE_LANGUAGE", None)  # Auto-detect if not set
    TYPE_DELAY = float(os.environ.get("HANDFREE_TYPE_DELAY", 0))
    SAMPLE_RATE = int(os.environ.get("HANDFREE_SAMPLE_RATE", 16000))

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY environment variable is required.\n"
                "Set it in your .env file or export it:\n"
                "  export GROQ_API_KEY=your_key_here"
            )
```

**File:** `exceptions.py`

```python
"""
Custom Exceptions
"""


class HandFreeError(Exception):
    """Base exception for HandFree errors."""
    pass


class MuteDetectionError(HandFreeError):
    """Error detecting mute state."""
    pass


class AudioRecordingError(HandFreeError):
    """Error recording audio."""
    pass


class TranscriptionError(HandFreeError):
    """Error transcribing audio."""
    pass


class OutputError(HandFreeError):
    """Error outputting text."""
    pass
```

**File:** `.env.example`

```
# Required: Your Groq API key
GROQ_API_KEY=your_api_key_here

# Optional: Language code for transcription (auto-detected if not set)
# HANDFREE_LANGUAGE=en

# Optional: Delay between keystrokes in seconds (0 = fastest)
# HANDFREE_TYPE_DELAY=0

# Optional: Audio sample rate in Hz (default 16000)
# HANDFREE_SAMPLE_RATE=16000
```

**Verification:**
- Remove GROQ_API_KEY, run app, verify helpful error message
- Test with invalid API key, verify error handling

---

## Step 8: End-to-End Testing

**Goal:** Verify complete workflow works reliably.

**Test Cases:**

| # | Test Case | Steps | Expected Result |
|---|-----------|-------|-----------------|
| 1 | Basic flow | Unmute → speak → mute | Text appears at cursor and in clipboard |
| 2 | Empty recording | Unmute → immediately mute | No crash, warning message |
| 3 | Long recording | Speak for 60 seconds | Full transcription works |
| 4 | Special characters | Say "Hello, world!" | Punctuation preserved |
| 5 | Quick succession | Multiple unmute/mute cycles | All transcriptions work |
| 6 | No AirPods | Test with AirPods disconnected | Graceful error message |

**Test Script:**
```python
# test_e2e.py
import time
import pyperclip
from main import HandFreeApp

def test_manual():
    """Manual end-to-end test - requires human interaction."""
    print("=" * 50)
    print("HandFree End-to-End Test")
    print("=" * 50)
    print("")
    print("Instructions:")
    print("1. Make sure AirPods are connected")
    print("2. Open TextEdit or another text editor")
    print("3. Click in the document so it has focus")
    print("4. Unmute AirPods and say 'Hello world'")
    print("5. Mute AirPods")
    print("6. Verify 'Hello world' appears in the document")
    print("")
    input("Press Enter when ready to start...")

    app = HandFreeApp()

    import signal
    def handler(sig, frame):
        app.stop()

        # Check clipboard
        clipboard = pyperclip.paste()
        print(f"\nClipboard contents: {clipboard}")
        if "hello" in clipboard.lower():
            print("✅ Test PASSED - transcription found in clipboard")
        else:
            print("❌ Test FAILED - transcription not found")
        exit(0)

    signal.signal(signal.SIGINT, handler)
    app.run()

if __name__ == "__main__":
    test_manual()
```

---

## Step 9: Create README

**Goal:** Document setup and usage instructions.

**File:** `README.md`

```markdown
# HandFree

AirPods-triggered speech-to-text for macOS. Press your AirPods stem to start recording, press again to transcribe and type.

## Requirements

- macOS 14 (Sonoma) or later
- Python 3.10+
- AirPods Pro (or AirPods with mute gesture support)
- Groq API key (free tier available)

## Installation

1. Clone or download this repository:
   ```bash
   cd /path/to/handfree
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file with your Groq API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

## Usage

1. Connect your AirPods
2. Run the app:
   ```bash
   python main.py
   ```
3. Click where you want text to appear
4. **Unmute AirPods** (press stem) → Recording starts
5. Speak your text
6. **Mute AirPods** (press stem) → Text is transcribed and typed

## Permissions

On first run, macOS will ask for:

1. **Microphone access**: Required for recording audio
2. **Accessibility access**: Required for typing text

To grant accessibility:
1. Open System Settings → Privacy & Security → Accessibility
2. Enable access for Terminal (or your Python executable)

## Troubleshooting

### "Mute detection not working"
- Ensure AirPods are connected and selected as input device
- Try pressing and holding the stem (different AirPods models behave differently)

### "Text not typing"
- Check accessibility permissions
- Try copying from clipboard (Cmd+V) as fallback

### "Transcription empty or wrong"
- Check your Groq API key is valid
- Speak clearly and closer to the microphone

## License

MIT
```

---

## Implementation Order Summary

| Step | Module | Key Files | Dependency |
|------|--------|-----------|------------|
| 1 | Project Setup | requirements.txt, .env | None |
| 2 | Mute Detector | mute_detector.py | Step 1 |
| 3 | Audio Recorder | audio_recorder.py | Step 1 |
| 4 | Transcriber | transcriber.py | Step 1 |
| 5 | Output Handler | output_handler.py | Step 1 |
| 6 | Main Loop | main.py | Steps 2-5 |
| 7 | Config & Polish | config.py, exceptions.py | Step 6 |
| 8 | E2E Testing | test_e2e.py | Step 6 |
| 9 | Documentation | README.md | Step 8 |

---

## Verification Checklist

- [ ] Dependencies install successfully
- [ ] Mute detector receives events from AirPods
- [ ] Audio recorder captures clear audio
- [ ] Transcriber returns accurate text
- [ ] Output handler types text correctly
- [ ] End-to-end flow works smoothly
- [ ] App handles errors gracefully
- [ ] Permissions are requested properly
