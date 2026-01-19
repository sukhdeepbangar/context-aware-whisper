"""
macOS Platform Implementation

This module provides macOS-specific implementations for:
- Hotkey detection via CGEvent tap (Fn/Globe key)
- Text output via AppleScript
- Mute detection via AVFAudio (deprecated)
"""

from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector
from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler

__all__ = [
    "MacOSHotkeyDetector",
    "MacOSOutputHandler",
]
