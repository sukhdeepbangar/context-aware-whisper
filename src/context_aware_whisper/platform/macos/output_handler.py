"""
macOS Output Handler

Handles text output via clipboard and AppleScript typing.
"""

import subprocess
import time

import pyperclip

from context_aware_whisper.platform.base import OutputHandlerBase
from context_aware_whisper.exceptions import OutputError


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

    def type_text_instant(self, text: str) -> None:
        """
        Insert text instantly using clipboard paste, then restore clipboard.

        This method:
        1. Saves current clipboard content
        2. Copies text to clipboard
        3. Pastes using Cmd+V
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

            # Paste using Cmd+V
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

            # Wait for paste to complete
            time.sleep(0.05)

        finally:
            # Restore original clipboard
            if original_clipboard is not None:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass  # Best effort restoration
