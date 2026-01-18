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
from handfree.local_transcriber import LocalTranscriber
from handfree.text_cleanup import TextCleaner, CleanupMode
from handfree.exceptions import (
    TranscriptionError,
    LocalTranscriptionError,
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


def get_transcriber(config: Config) -> tuple:
    """
    Create transcriber based on configuration.

    Implements factory pattern with fallback logic:
    - If config.transcriber == "local": try local first, fallback to cloud if model missing
    - If config.transcriber == "groq": use cloud transcription

    Args:
        config: Application configuration

    Returns:
        Tuple of (transcriber_instance, transcriber_mode_string)
    """
    if config.transcriber == "local":
        local_transcriber = LocalTranscriber(
            model_name=config.whisper_model,
            models_dir=config.models_dir
        )

        if not local_transcriber.is_model_downloaded():
            logger.warning(
                f"Local model '{config.whisper_model}' not downloaded at {config.models_dir}"
            )
            if config.groq_api_key:
                # Fallback to cloud transcription
                logger.info("Falling back to Groq cloud transcription")
                print(f"[Warning] Local model '{config.whisper_model}' not found.")
                print("          Falling back to Groq cloud transcription.")
                print(f"          To download: python -m handfree.model_manager download {config.whisper_model}")
                return Transcriber(api_key=config.groq_api_key), "groq (fallback)"
            else:
                # No fallback available - download model
                logger.info("No Groq API key for fallback, downloading model...")
                print(f"[Info] Downloading model '{config.whisper_model}' (this may take a few minutes)...")
                local_transcriber.download_model()

        mode = f"local (whisper.cpp, model: {config.whisper_model})"
        logger.info(f"Using local transcription: {mode}")
        return local_transcriber, mode
    else:
        # Cloud (Groq) transcription
        mode = "groq (cloud)"
        logger.info(f"Using cloud transcription: {mode}")
        return Transcriber(api_key=config.groq_api_key), mode


def get_text_cleaner(config: Config) -> TextCleaner:
    """Create text cleaner based on configuration."""
    mode_map = {
        "off": CleanupMode.OFF,
        "light": CleanupMode.LIGHT,
        "standard": CleanupMode.STANDARD,
        "aggressive": CleanupMode.AGGRESSIVE,
    }
    mode = mode_map.get(config.text_cleanup, CleanupMode.STANDARD)

    return TextCleaner(
        mode=mode,
        api_key=config.groq_api_key if mode == CleanupMode.AGGRESSIVE else None,
        preserve_intentional=config.preserve_intentional,
    )


class AppState(Enum):
    """Application state machine states."""
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


class HandFreeApp:
    """Main application class coordinating all modules."""

    def __init__(
        self,
        config: Config,
    ):
        """
        Initialize all components.

        Args:
            config: Application configuration loaded from environment.
        """
        # Load environment variables
        load_dotenv()

        # Log platform detection
        platform = get_platform()
        logger.info(f"Platform detected: {platform}")

        # Store configuration
        self.config = config
        self.language = config.language
        self.use_paste = config.use_paste
        self.skip_clipboard = config.skip_clipboard
        self.ui_enabled = config.ui_enabled
        self.history_enabled = config.history_enabled

        # Initialize audio recorder
        self.recorder = AudioRecorder(sample_rate=config.sample_rate)
        logger.debug(f"Audio recorder initialized (sample_rate={config.sample_rate})")

        # Initialize transcriber using factory function
        self.transcriber, self.transcriber_mode = get_transcriber(config)
        logger.debug(f"Transcriber initialized: {self.transcriber_mode}")

        # Initialize text cleaner
        self.text_cleaner = get_text_cleaner(config)
        logger.debug(f"Text cleaner initialized: mode={config.text_cleanup}")

        # Initialize output handler with error handling
        try:
            self.output = create_output_handler(type_delay=config.type_delay)
            logger.info(f"Output handler initialized: {type(self.output).__name__}")
        except PlatformNotSupportedError as e:
            logger.error(f"Output handler initialization failed: {e}")
            raise OutputHandlerError(
                f"Cannot initialize output handler on {platform}: {e}\n"
                "Ensure you have the required dependencies installed for your platform."
            ) from e

        # Initialize UI with graceful degradation
        self.ui = None
        if config.ui_enabled:
            try:
                self.ui = HandFreeUI(
                    history_enabled=config.history_enabled,
                    indicator_position=config.ui_position,
                    menubar_enabled=True,
                    on_quit=self._handle_quit_from_menu
                )
                logger.info(f"UI initialized (position={config.ui_position}, history={config.history_enabled}, menubar=True)")
            except Exception as e:
                # UI failure is non-fatal - continue without UI
                logger.warning(f"UI initialization failed, continuing without visual indicator: {e}")
                print(f"[Warning] UI disabled: {e}")
                self.ui = None

        # Initialize hotkey detector with clear error messages
        try:
            self.detector = create_hotkey_detector(
                on_start=self.handle_start,
                on_stop=self.handle_stop,
                on_history_toggle=self.handle_history_toggle if self.ui else None
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

        # Transcribe - show appropriate message based on transcriber mode
        if self.config.transcriber == "local" and isinstance(self.transcriber, LocalTranscriber):
            print(f"[Transcribing] Processing locally ({self.config.whisper_model})...")
        else:
            print("[Transcribing] Sending to Groq API...")
        try:
            text = self.transcriber.transcribe(
                audio_bytes,
                language=self.language
            )
            if text:
                # Clean disfluencies
                if self.config.text_cleanup != "off":
                    original_text = text
                    text = self.text_cleaner.clean(text)
                    if text != original_text:
                        logger.debug(f"Text cleaned: '{original_text}' -> '{text}'")

                # Check if text is still non-empty after cleanup
                if not text:
                    print("[Warning] No transcription returned (empty after cleanup)")
                    if self.ui:
                        self.ui.set_state("error")
                    self._state = AppState.IDLE
                    return

                print(f"[Transcription] {text}")
                try:
                    self.output.output(text, use_paste=self.use_paste, skip_clipboard=self.skip_clipboard)
                    if self.skip_clipboard:
                        print("[Output] Text typed")
                    else:
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
        except (TranscriptionError, LocalTranscriptionError) as e:
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

    def handle_history_toggle(self) -> None:
        """Called when user presses history toggle hotkey (Cmd+Shift+H / Ctrl+Shift+H)."""
        if self.ui:
            self.ui.toggle_history()
            logger.debug("History panel toggled")

    def _handle_quit_from_menu(self) -> None:
        """Called when user clicks Quit from menu bar."""
        logger.info("Quit requested from menu bar")
        self.stop()

    def run(self) -> None:
        """Start the application and run the event loop."""
        import time

        self._running = True

        # Start UI (creates windows on main thread - required for macOS)
        if self.ui:
            self.ui.start()

        self.detector.start()

        self._print_banner()

        # Run event loop
        if self.ui:
            # Run tkinter mainloop on main thread (required for macOS)
            self.ui.run_mainloop()
        else:
            # No UI - just sleep loop
            while self._running:
                time.sleep(0.1)

    def _print_banner(self) -> None:
        """Print welcome message and instructions."""
        hotkey = self.detector.get_hotkey_description()
        history_hotkey = self.detector.get_history_toggle_description()
        platform = get_platform()

        print("=" * 55)
        print("  HandFree - Speech-to-Text")
        print("=" * 55)
        print()
        print(f"  Platform: {platform}")
        print(f"  Transcription: {self.transcriber_mode}")
        print(f"  Text cleanup: {self.config.text_cleanup}")
        print(f"  Hotkey: {hotkey} (hold to record)")
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
        if self.ui and self.history_enabled:
            print(f"  Press {history_hotkey} to toggle history panel")
        if self.ui and self.ui.menubar_enabled:
            print("  Menu bar: Click microphone icon for controls")
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
        app = HandFreeApp(config=config)
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
