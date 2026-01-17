"""
HandFree - Speech-to-Text

Main application entry point.
Orchestrates hotkey detection, audio recording, transcription, and text output.
"""

import os
import signal
import sys
from enum import Enum, auto
from typing import Optional

from dotenv import load_dotenv

from handfree.hotkey_detector import HotkeyDetector
from handfree.audio_recorder import AudioRecorder
from handfree.transcriber import Transcriber
from handfree.output_handler import OutputHandler
from handfree.exceptions import TranscriptionError, OutputError
from handfree.ui import HandFreeUI


class AppState(Enum):
    """Application state machine states."""
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


class HandFreeApp:
    """Main application class coordinating all modules."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        language: Optional[str] = None,
        type_delay: float = 0.0,
        sample_rate: int = 16000,
        use_paste: bool = False,
        ui_enabled: bool = True,
        history_enabled: bool = True
    ):
        """
        Initialize all components.

        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
            language: Language code for transcription. Auto-detected if None.
            type_delay: Delay between keystrokes in seconds.
            sample_rate: Audio sample rate in Hz.
            use_paste: If True, use clipboard paste instead of keystroke typing.
            ui_enabled: If True, show visual UI indicator.
            history_enabled: If True, save transcriptions to history database.
        """
        # Load environment variables
        load_dotenv()

        # Store configuration
        self.language = language or os.environ.get("HANDFREE_LANGUAGE")
        self.use_paste = use_paste
        self.ui_enabled = ui_enabled
        self.history_enabled = history_enabled

        # Initialize modules
        self.recorder = AudioRecorder(sample_rate=sample_rate)
        self.transcriber = Transcriber(api_key=api_key)
        self.output = OutputHandler(type_delay=type_delay)

        # Initialize UI (with history support)
        self.ui = HandFreeUI(history_enabled=history_enabled) if ui_enabled else None

        # Initialize hotkey detector (Fn/Globe key)
        self.detector = HotkeyDetector(
            on_start=self.handle_start,
            on_stop=self.handle_stop
        )

        # Application state
        self._state = AppState.IDLE
        self._running = False

    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Whether the application is running."""
        return self._running

    def handle_start(self) -> None:
        """Called when user presses Fn key - start recording."""
        if self._state == AppState.TRANSCRIBING:
            # Still processing previous transcription, ignore
            return

        print("\n[Recording] Started... Speak now.")
        self._state = AppState.RECORDING

        # Update UI
        if self.ui:
            self.ui.set_state("recording")

        self.recorder.start_recording()

    def handle_stop(self) -> None:
        """Called when user releases Fn key - stop, transcribe, output."""
        if self._state != AppState.RECORDING:
            return

        duration = self.recorder.get_duration()
        print(f"[Recording] Stopped. Duration: {duration:.1f}s")

        self._state = AppState.TRANSCRIBING

        # Update UI
        if self.ui:
            self.ui.set_state("transcribing")

        # Get recorded audio
        audio_bytes = self.recorder.stop_recording()

        if not audio_bytes or duration < 0.1:
            print("[Warning] No audio recorded or too short")
            self._state = AppState.IDLE
            if self.ui:
                self.ui.set_state("error")
            return

        # Transcribe
        print("[Transcribing] Sending to Groq API...")
        try:
            text = self.transcriber.transcribe(
                audio_bytes,
                language=self.language
            )
            if text:
                print(f"[Transcription] {text}")
                try:
                    self.output.output(text, use_paste=self.use_paste)
                    print("[Output] Text copied to clipboard and typed")
                    # Update UI - success
                    if self.ui:
                        self.ui.set_state("success")
                        # Save to history
                        self.ui.add_transcription(
                            text=text,
                            duration=duration,
                            language=self.language
                        )
                except OutputError as e:
                    print(f"[Error] Output failed: {e}")
                    print("[Info] Text is still in clipboard - use Cmd+V to paste")
                    # Update UI - error
                    if self.ui:
                        self.ui.set_state("error")
            else:
                print("[Warning] No transcription returned (empty response)")
                # Update UI - error
                if self.ui:
                    self.ui.set_state("error")
        except TranscriptionError as e:
            print(f"[Error] Transcription failed: {e}")
            # Update UI - error
            if self.ui:
                self.ui.set_state("error")
        except Exception as e:
            print(f"[Error] Unexpected error during transcription: {e}")
            # Update UI - error
            if self.ui:
                self.ui.set_state("error")
        finally:
            self._state = AppState.IDLE

    def run(self) -> None:
        """Start the application and run the event loop."""
        import time

        self._running = True

        # Start UI
        if self.ui:
            self.ui.start()

        self.detector.start()

        self._print_banner()

        # Run event loop
        while self._running:
            time.sleep(0.1)

    def _print_banner(self) -> None:
        """Print welcome message and instructions."""
        print("=" * 55)
        print("  HandFree - Speech-to-Text")
        print("=" * 55)
        print()
        print("  Mode: Fn/Globe key (hold to record)")
        print()
        print("  Usage:")
        print("    1. HOLD Fn key            -> Recording starts")
        print("    2. Speak while holding")
        print("    3. RELEASE Fn key         -> Transcribes & types")
        print()
        print("  The transcribed text will be:")
        print("    - Typed at the current cursor position")
        print("    - Copied to clipboard (as backup)")
        print()
        print("  Press Ctrl+C to exit")
        print("=" * 55)
        print()

    def stop(self) -> None:
        """Stop the application gracefully."""
        if not self._running:
            return

        self._running = False

        # Stop recording if in progress
        if self._state == AppState.RECORDING:
            self.recorder.stop_recording()

        # Stop detector
        self.detector.stop()

        # Stop UI
        if self.ui:
            self.ui.stop()

        print("\nHandFree stopped. Goodbye!")


def main():
    """Main entry point."""
    # Load environment variables early to validate
    load_dotenv()

    # Check for API key
    if not os.environ.get("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY environment variable is not set.")
        print()
        print("To fix this:")
        print("  1. Get your API key from https://console.groq.com/keys")
        print("  2. Set it in your .env file: GROQ_API_KEY=your_key_here")
        print("  3. Or export it: export GROQ_API_KEY=your_key_here")
        sys.exit(1)

    # Load optional configuration from environment
    language = os.environ.get("HANDFREE_LANGUAGE")
    type_delay = float(os.environ.get("HANDFREE_TYPE_DELAY", "0"))
    sample_rate = int(os.environ.get("HANDFREE_SAMPLE_RATE", "16000"))
    use_paste = os.environ.get("HANDFREE_USE_PASTE", "").lower() in ("true", "1", "yes")
    ui_enabled = os.environ.get("HANDFREE_UI_ENABLED", "true").lower() in ("true", "1", "yes")
    history_enabled = os.environ.get("HANDFREE_HISTORY_ENABLED", "true").lower() in ("true", "1", "yes")

    # Create application
    try:
        app = HandFreeApp(
            language=language,
            type_delay=type_delay,
            sample_rate=sample_rate,
            use_paste=use_paste,
            ui_enabled=ui_enabled,
            history_enabled=history_enabled
        )
    except Exception as e:
        print(f"Error: Failed to initialize application: {e}")
        sys.exit(1)

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the application
    try:
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        app.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
