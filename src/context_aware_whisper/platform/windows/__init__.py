"""
Windows Platform Implementation

This module provides Windows-specific implementations for:
- Hotkey detection via pynput (Ctrl+Shift+Space)
- Text output via pynput keyboard controller
"""

from context_aware_whisper.platform.windows.hotkey_detector import WindowsHotkeyDetector
from context_aware_whisper.platform.windows.output_handler import WindowsOutputHandler

__all__ = [
    "WindowsHotkeyDetector",
    "WindowsOutputHandler",
]
