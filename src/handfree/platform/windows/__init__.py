"""
Windows Platform Implementation

This module provides Windows-specific implementations for:
- Hotkey detection via pynput (Ctrl+Shift+Space)
- Text output via pynput keyboard controller
"""

from handfree.platform.windows.hotkey_detector import WindowsHotkeyDetector
from handfree.platform.windows.output_handler import WindowsOutputHandler

__all__ = [
    "WindowsHotkeyDetector",
    "WindowsOutputHandler",
]
