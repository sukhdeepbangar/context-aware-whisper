"""
Context-Aware Whisper - Speech-to-Text

A cross-platform Python application that uses hotkeys
to trigger fast speech-to-text transcription via Groq Whisper API.

Supported platforms:
- macOS: Fn/Globe key
- Windows: Ctrl+Shift+Space
- Linux: Ctrl+Shift+Space
"""

from context_aware_whisper.audio_recorder import AudioRecorder
from context_aware_whisper.config import Config
from context_aware_whisper.exceptions import (
    CAWError,
    ConfigurationError,
    MuteDetectionError,
    AudioRecordingError,
    TranscriptionError,
    OutputError,
    PlatformNotSupportedError,
    TextCleanupError,
)
from context_aware_whisper.text_cleanup import TextCleaner, CleanupMode
from context_aware_whisper.transcriber import Transcriber

# Platform abstraction layer
from context_aware_whisper.platform import (
    get_platform,
    create_hotkey_detector,
    create_output_handler,
    is_mute_detector_available,
    get_default_hotkey_description,
    HotkeyDetectorBase,
    OutputHandlerBase,
)

# Legacy imports for backward compatibility
from context_aware_whisper.output_handler import OutputHandler, get_clipboard_content
from context_aware_whisper.hotkey_detector import HotkeyDetector

# UI modules (optional - may not be available if tkinter not installed)
try:
    from context_aware_whisper.ui import CAWUI, RecordingIndicator
    _UI_AVAILABLE = True
except ImportError:
    _UI_AVAILABLE = False
    CAWUI = None
    RecordingIndicator = None

# Mute detector (macOS only, deprecated)
try:
    from context_aware_whisper.mute_detector import MuteDetector
except ImportError:
    MuteDetector = None

__version__ = "0.2.0"

__all__ = [
    # Core modules
    "AudioRecorder",
    "Config",
    "Transcriber",
    # Exceptions
    "CAWError",
    "ConfigurationError",
    "MuteDetectionError",
    "AudioRecordingError",
    "TranscriptionError",
    "OutputError",
    "PlatformNotSupportedError",
    "TextCleanupError",
    # Text cleanup
    "TextCleaner",
    "CleanupMode",
    # Platform abstraction
    "get_platform",
    "create_hotkey_detector",
    "create_output_handler",
    "is_mute_detector_available",
    "get_default_hotkey_description",
    "HotkeyDetectorBase",
    "OutputHandlerBase",
    # Legacy (backward compatibility)
    "MuteDetector",
    "HotkeyDetector",
    "OutputHandler",
    "get_clipboard_content",
    # UI
    "CAWUI",
    "RecordingIndicator",
]
