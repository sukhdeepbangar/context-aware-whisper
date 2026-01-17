"""
macOS Output Handler

Handles text output via clipboard and AppleScript typing.
"""

import subprocess

import pyperclip

from handfree.platform.base import OutputHandlerBase
from handfree.exceptions import OutputError


class MacOSOutputHandler(OutputHandlerBase):
    """Handles output of transcribed text to clipboard and active app on macOS."""

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
        Type text into active application using AppleScript.

        This method is more reliable than pyautogui on macOS.

        Args:
            text: Text to type into the active application

        Raises:
            OutputError: If typing operation fails
        """
        if not text:
            return

        # Escape special characters for AppleScript
        # Handle backslash first, then quotes
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')

        # Use AppleScript to type the text
        script = f'tell application "System Events" to keystroke "{escaped}"'

        try:
            subprocess.run(
                ['osascript', '-e', script],
                check=True,
                capture_output=True,
                timeout=10
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            raise OutputError(f"Failed to type text: {stderr}")
        except subprocess.TimeoutExpired:
            raise OutputError("Typing operation timed out")
        except FileNotFoundError:
            raise OutputError("osascript not found - this module requires macOS")

    def type_text_via_paste(self, text: str) -> None:
        """
        Copy text to clipboard and paste using Cmd+V.

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

        # Simulate Cmd+V to paste
        script = 'tell application "System Events" to keystroke "v" using command down'

        try:
            subprocess.run(
                ['osascript', '-e', script],
                check=True,
                capture_output=True,
                timeout=10
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            raise OutputError(f"Failed to paste text: {stderr}")
        except subprocess.TimeoutExpired:
            raise OutputError("Paste operation timed out")
