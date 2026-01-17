"""
Linux Output Handler

Handles text output via clipboard and pynput keyboard typing.

Note: On Wayland, pynput may have limited functionality.
For Wayland support, consider using wtype or wl-clipboard.
"""

import time

import pyperclip
from pynput.keyboard import Controller, Key

from handfree.platform.base import OutputHandlerBase
from handfree.exceptions import OutputError


class LinuxOutputHandler(OutputHandlerBase):
    """Handles output of transcribed text to clipboard and active app on Linux."""

    def __init__(self, type_delay: float = 0.0):
        """
        Initialize output handler.

        Args:
            type_delay: Delay between keystrokes in seconds (0 = fastest)
        """
        super().__init__(type_delay)
        self._keyboard = Controller()

    def copy_to_clipboard(self, text: str) -> None:
        """
        Copy text to system clipboard.

        Args:
            text: Text to copy to clipboard

        Raises:
            OutputError: If clipboard operation fails
        """
        if not text:
            return

        try:
            pyperclip.copy(text)
        except Exception as e:
            raise OutputError(f"Failed to copy to clipboard: {e}")

    def type_text(self, text: str) -> None:
        """
        Type text into active application using pynput.

        Args:
            text: Text to type into the active application

        Raises:
            OutputError: If typing operation fails
        """
        if not text:
            return

        try:
            for char in text:
                self._keyboard.type(char)
                if self.type_delay > 0:
                    time.sleep(self.type_delay)
        except Exception as e:
            raise OutputError(f"Failed to type text: {e}")

    def type_text_via_paste(self, text: str) -> None:
        """
        Copy text to clipboard and paste using Ctrl+V.

        This can be more reliable for special characters.

        Args:
            text: Text to paste into the active application

        Raises:
            OutputError: If operation fails
        """
        if not text:
            return

        # Copy to clipboard
        self.copy_to_clipboard(text)

        # Small delay to ensure clipboard is updated
        time.sleep(0.05)

        try:
            # Simulate Ctrl+V to paste
            self._keyboard.press(Key.ctrl)
            self._keyboard.press('v')
            self._keyboard.release('v')
            self._keyboard.release(Key.ctrl)
        except Exception as e:
            raise OutputError(f"Failed to paste text: {e}")
