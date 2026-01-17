"""
HandFree - Speech-to-Text

Main application entry point.
Orchestrates hotkey detection, audio recording, transcription, and text output.
"""

import logging
import os
import signal
import sys
from enum import Enum, auto
from typing import Optional

from dotenv import load_dotenv

from handfree.audio_recorder import AudioRecorder
from handfree.config import Config
from handfree.transcriber import Transcriber
from handfree.exceptions import (
    TranscriptionError,
    OutputError,
    UIInitializationError,
    HotkeyDetectorError,
    OutputHandlerError,
    PlatformNotSupportedError,
)
from handfree.ui import HandFreeUI
from handfree.platform import (
    create_hotkey_detector,
    create_output_handler,
    get_platform,
    get_default_hotkey_description,
)


# Configure logging
logger = logging.getLogger(__name__)


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
        ui_position: str = "top-center",
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
            ui_position: Position for UI indicator (top-center, top-right, etc.).
            history_enabled: If True, save transcriptions to history database.
        """
        # Load environment variables
        load_dotenv()

        # Log platform detection
        platform = get_platform()
        logger.info(f"Platform detected: {platform}")

        # Store configuration
        self.language = language or os.environ.get("HANDFREE_LANGUAGE")
        self.use_paste = use_paste
        self.ui_enabled = ui_enabled
        self.history_enabled = history_enabled

        # Initialize audio recorder
        self.recorder = AudioRecorder(sample_rate=sample_rate)
        logger.debug(f"Audio recorder initialized (sample_rate={sample_rate})")

        # Initialize transcriber
        self.transcriber = Transcriber(api_key=api_key)
        logger.debug("Transcriber initialized")

        # Initialize output handler with error handling
        try:
            self.output = create_output_handler(type_delay=type_delay)
            logger.info(f"Output handler initialized: {type(self.output).__name__}")
        except PlatformNotSupportedError as e:
            logger.error(f"Output handler initialization failed: {e}")
            raise OutputHandlerError(
                f"Cannot initialize output handler on {platform}: {e}\n"
                "Ensure you have the required dependencies installed for your platform."
            ) from e

        # Initialize UI with graceful degradation
        self.ui = None
        if ui_enabled:
            try:
                self.ui = HandFreeUI(
                    history_enabled=history_enabled,
                    indicator_position=ui_position
                )
                logger.info(f"UI initialized (position={ui_position}, history={history_enabled})")
            except Exception as e:
                # UI failure is non-fatal - continue without UI
                logger.warning(f"UI initialization failed, continuing without visual indicator: {e}")
                print(f"[Warning] UI disabled: {e}")
                self.ui = None

        # Initialize hotkey detector with clear error messages
        try:
            self.detector = create_hotkey_detector(
                on_start=self.handle_start,
                on_stop=self.handle_stop
            )
            logger.info(f"Hotkey detector initialized: {type(self.detector).__name__}")
        except PlatformNotSupportedError as e:
            logger.error(f"Hotkey detector initialization failed: {e}")
            raise HotkeyDetectorError(
                f"Cannot initialize hotkey detector on {platform}: {e}\n"
                "Supported platforms: macOS, Windows, Linux"
            ) from e
        except Exception as e:
            logger.error(f"Hotkey detector initialization failed: {e}")
            raise HotkeyDetectorError(
                f"Failed to initialize hotkey detector: {e}\n"
                "This may be due to missing system permissions or dependencies.\n"
                "On macOS: Grant Accessibility permission in System Settings.\n"
                "On Linux: Ensure you have X11 or proper Wayland permissions."
            ) from e

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
        hotkey = self.detector.get_hotkey_description()
        platform = get_platform()

        print("=" * 55)
        print("  HandFree - Speech-to-Text")
        print("=" * 55)
        print()
        print(f"  Platform: {platform}")
        print(f"  Mode: {hotkey} (hold to record)")
        print()
        print("  Usage:")
        print(f"    1. HOLD {hotkey:<20} -> Recording starts")
        print("    2. Speak while holding")
        print(f"    3. RELEASE {hotkey:<17} -> Transcribes & types")
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


def setup_logging(debug: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        debug: If True, enable debug-level logging
    """
    level = logging.DEBUG if debug else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt=date_format
    )

    # Also log to file if in debug mode
    if debug:
        file_handler = logging.FileHandler("handfree.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(format_str, datefmt=date_format))
        logging.getLogger().addHandler(file_handler)


def main():
    """Main entry point."""
    # Check for debug mode from environment
    debug_mode = os.environ.get("HANDFREE_DEBUG", "").lower() in ("true", "1", "yes")
    setup_logging(debug=debug_mode)

    logger.info("HandFree starting...")

    # Load and validate configuration
    try:
        config = Config.from_env()
        warnings = config.validate()
        for warning in warnings:
            print(f"Warning: {warning}")
            logger.warning(warning)
    except ValueError as e:
        print(f"Error: {e}")
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create application with validated config
    try:
        app = HandFreeApp(
            api_key=config.groq_api_key,
            language=config.language,
            type_delay=config.type_delay,
            sample_rate=config.sample_rate,
            use_paste=config.use_paste,
            ui_enabled=config.ui_enabled,
            ui_position=config.ui_position,
            history_enabled=config.history_enabled
        )
    except HotkeyDetectorError as e:
        print(f"Error: {e}")
        logger.error(f"Hotkey detector error: {e}")
        sys.exit(1)
    except OutputHandlerError as e:
        print(f"Error: {e}")
        logger.error(f"Output handler error: {e}")
        sys.exit(1)
    except PlatformNotSupportedError as e:
        print(f"Error: {e}")
        logger.error(f"Platform not supported: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to initialize application: {e}")
        logger.exception(f"Unexpected initialization error: {e}")
        sys.exit(1)

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the application
    try:
        logger.info("HandFree running")
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.exception(f"Fatal error during execution: {e}")
        app.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
