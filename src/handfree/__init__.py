"""
HandFree - Speech-to-Text

A cross-platform Python application that uses hotkeys
to trigger fast speech-to-text transcription via Groq Whisper API.

Supported platforms:
- macOS: Fn/Globe key
- Windows: Ctrl+Shift+Space
- Linux: Ctrl+Shift+Space
"""

from handfree.audio_recorder import AudioRecorder
from handfree.config import Config
from handfree.exceptions import (
    HandFreeError,
    ConfigurationError,
    MuteDetectionError,
    AudioRecordingError,
    TranscriptionError,
    OutputError,
    PlatformNotSupportedError,
)
from handfree.transcriber import Transcriber

# Platform abstraction layer
from handfree.platform import (
    get_platform,
    create_hotkey_detector,
    create_output_handler,
    is_mute_detector_available,
    get_default_hotkey_description,
    HotkeyDetectorBase,
    OutputHandlerBase,
)

# Legacy imports for backward compatibility
from handfree.output_handler import OutputHandler, get_clipboard_content
from handfree.hotkey_detector import HotkeyDetector

# UI modules (optional - may not be available if tkinter not installed)
try:
    from handfree.ui import HandFreeUI, RecordingIndicator
    _UI_AVAILABLE = True
except ImportError:
    _UI_AVAILABLE = False
    HandFreeUI = None
    RecordingIndicator = None

# Mute detector (macOS only, deprecated)
try:
    from handfree.mute_detector import MuteDetector
except ImportError:
    MuteDetector = None

__version__ = "0.2.0"

__all__ = [
    # Core modules
    "AudioRecorder",
    "Config",
    "Transcriber",
    # Exceptions
    "HandFreeError",
    "ConfigurationError",
    "MuteDetectionError",
    "AudioRecordingError",
    "TranscriptionError",
    "OutputError",
    "PlatformNotSupportedError",
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
    "HandFreeUI",
    "RecordingIndicator",
]
