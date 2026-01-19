"""
Windows Output Handler

Handles text output via clipboard and pynput keyboard typing.
"""

import time

import pyperclip
from pynput.keyboard import Controller, Key

from context_aware_whisper.platform.base import OutputHandlerBase
from context_aware_whisper.exceptions import OutputError


class WindowsOutputHandler(OutputHandlerBase):
    """Handles output of transcribed text to clipboard and active app on Windows."""

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

    def type_text_instant(self, text: str) -> None:
        """
        Insert text instantly using clipboard paste, then restore clipboard.

        This method:
        1. Saves current clipboard content
        2. Copies text to clipboard
        3. Pastes using Ctrl+V
        4. Restores original clipboard content

        Args:
            text: Text to insert at cursor position

        Raises:
            OutputError: If paste operation fails
        """
        if not text:
            return

        # Save current clipboard content
        original_clipboard = None
        try:
            original_clipboard = pyperclip.paste()
        except Exception:
            pass  # Clipboard might be empty or contain non-text

        try:
            # Copy text to clipboard
            pyperclip.copy(text)

            # Small delay to ensure clipboard is updated
            time.sleep(0.05)

            # Paste using Ctrl+V
            try:
                self._keyboard.press(Key.ctrl)
                self._keyboard.press('v')
                self._keyboard.release('v')
                self._keyboard.release(Key.ctrl)
            except Exception as e:
                raise OutputError(f"Failed to paste text: {e}")

            # Wait for paste to complete
            time.sleep(0.05)

        finally:
            # Restore original clipboard
            if original_clipboard is not None:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass  # Best effort restoration
