"""
Linux Output Handler

Handles text output via clipboard and pynput keyboard typing.

On X11: Uses pynput with xdotool as fallback.
On Wayland: Uses wtype for typing and wl-clipboard for clipboard operations.
"""

import logging
import os
import shutil
import subprocess
import time
from typing import Optional

import pyperclip
from pynput.keyboard import Controller, Key

from context_aware_whisper.platform.base import OutputHandlerBase
from context_aware_whisper.exceptions import OutputError

logger = logging.getLogger(__name__)


def is_wayland_session() -> bool:
    """
    Check if the current session is running on Wayland.

    Returns:
        True if running on Wayland, False otherwise (X11 or unknown).
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    return session_type == "wayland"


def get_display_server() -> str:
    """
    Get the current display server type.

    Returns:
        "wayland", "x11", or "unknown"
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        return "wayland"
    elif session_type == "x11":
        return "x11"
    elif os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    elif os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def is_tool_available(tool_name: str) -> bool:
    """
    Check if a command-line tool is available in PATH.

    Args:
        tool_name: Name of the tool to check (e.g., "xdotool", "wtype")

    Returns:
        True if the tool is available, False otherwise.
    """
    return shutil.which(tool_name) is not None


class LinuxOutputHandler(OutputHandlerBase):
    """
    Handles output of transcribed text to clipboard and active app on Linux.

    Supports both X11 and Wayland display servers with appropriate fallbacks:
    - X11: pynput (primary), xdotool (fallback)
    - Wayland: wtype (primary), wl-copy for clipboard
    """

    def __init__(self, type_delay: float = 0.0):
        """
        Initialize output handler.

        Args:
            type_delay: Delay between keystrokes in seconds (0 = fastest)
        """
        super().__init__(type_delay)
        self._keyboard: Optional[Controller] = None
        self._display_server = get_display_server()

        # Check available tools
        self._has_xdotool = is_tool_available("xdotool")
        self._has_wtype = is_tool_available("wtype")
        self._has_wl_copy = is_tool_available("wl-copy")

        # Initialize pynput keyboard controller (may not work on Wayland)
        try:
            self._keyboard = Controller()
        except Exception as e:
            logger.warning(f"Could not initialize pynput keyboard controller: {e}")
            self._keyboard = None

        # Log detected configuration
        logger.debug(
            f"LinuxOutputHandler initialized: display_server={self._display_server}, "
            f"xdotool={self._has_xdotool}, wtype={self._has_wtype}, "
            f"wl-copy={self._has_wl_copy}, pynput={'available' if self._keyboard else 'unavailable'}"
        )

    def copy_to_clipboard(self, text: str) -> None:
        """
        Copy text to system clipboard.

        Uses wl-copy on Wayland if available, otherwise falls back to pyperclip.

        Args:
            text: Text to copy to clipboard

        Raises:
            OutputError: If clipboard operation fails
        """
        if not text:
            return

        # On Wayland, prefer wl-copy if available
        if self._display_server == "wayland" and self._has_wl_copy:
            try:
                self._copy_with_wl_copy(text)
                return
            except Exception as e:
                logger.warning(f"wl-copy failed, falling back to pyperclip: {e}")

        # Fallback to pyperclip (works on X11 and sometimes on XWayland)
        try:
            pyperclip.copy(text)
        except Exception as e:
            raise OutputError(f"Failed to copy to clipboard: {e}")

    def _copy_with_wl_copy(self, text: str) -> None:
        """
        Copy text to clipboard using wl-copy (Wayland).

        Args:
            text: Text to copy

        Raises:
            OutputError: If wl-copy fails
        """
        try:
            result = subprocess.run(
                ["wl-copy", "--"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise OutputError(f"wl-copy failed: {result.stderr.decode('utf-8')}")
        except subprocess.TimeoutExpired:
            raise OutputError("wl-copy timed out")
        except FileNotFoundError:
            raise OutputError("wl-copy not found")

    def type_text(self, text: str) -> None:
        """
        Type text into active application.

        Strategy:
        - On Wayland: Uses wtype (xdotool doesn't work on Wayland)
        - On X11: Tries pynput first, falls back to xdotool if pynput fails

        Args:
            text: Text to type into the active application

        Raises:
            OutputError: If typing operation fails with all available methods
        """
        if not text:
            return

        # On Wayland, only wtype works for simulating keyboard input
        if self._display_server == "wayland":
            if self._has_wtype:
                self._type_with_wtype(text)
                return
            else:
                raise OutputError(
                    "Cannot type text on Wayland: wtype is not installed. "
                    "Please install wtype: https://github.com/atx/wtype"
                )

        # On X11, try pynput first, then xdotool as fallback
        if self._keyboard is not None:
            try:
                self._type_with_pynput(text)
                return
            except Exception as e:
                logger.warning(f"pynput typing failed, trying xdotool fallback: {e}")

        # Fallback to xdotool on X11
        if self._has_xdotool:
            self._type_with_xdotool(text)
            return

        raise OutputError(
            "Failed to type text: pynput unavailable and xdotool not found. "
            "Please install xdotool: sudo apt install xdotool"
        )

    def _type_with_pynput(self, text: str) -> None:
        """
        Type text using pynput keyboard controller.

        Args:
            text: Text to type

        Raises:
            Exception: If pynput typing fails
        """
        for char in text:
            self._keyboard.type(char)
            if self.type_delay > 0:
                time.sleep(self.type_delay)

    def _type_with_xdotool(self, text: str) -> None:
        """
        Type text using xdotool (X11 only).

        Args:
            text: Text to type

        Raises:
            OutputError: If xdotool fails
        """
        try:
            # Use --clearmodifiers to prevent modifier key interference
            # Apply delay in milliseconds (xdotool uses ms)
            delay_ms = int(self.type_delay * 1000) if self.type_delay > 0 else 0
            cmd = ["xdotool", "type", "--clearmodifiers"]
            if delay_ms > 0:
                cmd.extend(["--delay", str(delay_ms)])
            cmd.append(text)

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,  # Allow more time for long text
            )
            if result.returncode != 0:
                raise OutputError(f"xdotool failed: {result.stderr.decode('utf-8')}")
        except subprocess.TimeoutExpired:
            raise OutputError("xdotool timed out")
        except FileNotFoundError:
            raise OutputError("xdotool not found")

    def _type_with_wtype(self, text: str) -> None:
        """
        Type text using wtype (Wayland only).

        Args:
            text: Text to type

        Raises:
            OutputError: If wtype fails
        """
        try:
            # wtype uses -d for delay in milliseconds
            delay_ms = int(self.type_delay * 1000) if self.type_delay > 0 else 0
            cmd = ["wtype"]
            if delay_ms > 0:
                cmd.extend(["-d", str(delay_ms)])
            cmd.append(text)

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,  # Allow more time for long text
            )
            if result.returncode != 0:
                raise OutputError(f"wtype failed: {result.stderr.decode('utf-8')}")
        except subprocess.TimeoutExpired:
            raise OutputError("wtype timed out")
        except FileNotFoundError:
            raise OutputError("wtype not found")

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

        # On Wayland, use wtype to send Ctrl+V
        if self._display_server == "wayland":
            if self._has_wtype:
                self._paste_with_wtype()
                return
            else:
                raise OutputError(
                    "Cannot paste on Wayland: wtype is not installed. "
                    "Please install wtype: https://github.com/atx/wtype"
                )

        # On X11, try pynput first, then xdotool
        if self._keyboard is not None:
            try:
                self._paste_with_pynput()
                return
            except Exception as e:
                logger.warning(f"pynput paste failed, trying xdotool fallback: {e}")

        # Fallback to xdotool on X11
        if self._has_xdotool:
            self._paste_with_xdotool()
            return

        raise OutputError(
            "Failed to paste text: pynput unavailable and xdotool not found. "
            "Please install xdotool: sudo apt install xdotool"
        )

    def _paste_with_pynput(self) -> None:
        """
        Simulate Ctrl+V paste using pynput.

        Raises:
            Exception: If pynput fails
        """
        self._keyboard.press(Key.ctrl)
        self._keyboard.press('v')
        self._keyboard.release('v')
        self._keyboard.release(Key.ctrl)

    def _paste_with_xdotool(self) -> None:
        """
        Simulate Ctrl+V paste using xdotool (X11 only).

        Raises:
            OutputError: If xdotool fails
        """
        try:
            result = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise OutputError(f"xdotool paste failed: {result.stderr.decode('utf-8')}")
        except subprocess.TimeoutExpired:
            raise OutputError("xdotool timed out")
        except FileNotFoundError:
            raise OutputError("xdotool not found")

    def _paste_with_wtype(self) -> None:
        """
        Simulate Ctrl+V paste using wtype (Wayland only).

        Raises:
            OutputError: If wtype fails
        """
        try:
            # wtype uses -M for modifier and -m to release
            result = subprocess.run(
                ["wtype", "-M", "ctrl", "-P", "v", "-p", "v", "-m", "ctrl"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise OutputError(f"wtype paste failed: {result.stderr.decode('utf-8')}")
        except subprocess.TimeoutExpired:
            raise OutputError("wtype timed out")
        except FileNotFoundError:
            raise OutputError("wtype not found")

    def _get_clipboard_content(self) -> Optional[str]:
        """
        Get current clipboard content.

        Returns:
            Current clipboard text, or None if unavailable
        """
        # On Wayland, try wl-paste first
        if self._display_server == "wayland" and is_tool_available("wl-paste"):
            try:
                result = subprocess.run(
                    ["wl-paste", "--no-newline"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout.decode("utf-8")
            except Exception:
                pass

        # Fallback to pyperclip
        try:
            return pyperclip.paste()
        except Exception:
            return None

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
        original_clipboard = self._get_clipboard_content()

        try:
            # Copy text to clipboard
            self.copy_to_clipboard(text)

            # Small delay to ensure clipboard is updated
            time.sleep(0.05)

            # Paste using Ctrl+V via the appropriate method
            if self._display_server == "wayland":
                if self._has_wtype:
                    self._paste_with_wtype()
                else:
                    raise OutputError(
                        "Cannot paste on Wayland: wtype is not installed. "
                        "Please install wtype: https://github.com/atx/wtype"
                    )
            else:
                # X11: try pynput first, then xdotool
                if self._keyboard is not None:
                    try:
                        self._paste_with_pynput()
                    except Exception as e:
                        logger.warning(f"pynput paste failed, trying xdotool fallback: {e}")
                        if self._has_xdotool:
                            self._paste_with_xdotool()
                        else:
                            raise OutputError(f"Failed to paste text: {e}")
                elif self._has_xdotool:
                    self._paste_with_xdotool()
                else:
                    raise OutputError(
                        "Failed to paste text: pynput unavailable and xdotool not found. "
                        "Please install xdotool: sudo apt install xdotool"
                    )

            # Wait for paste to complete
            time.sleep(0.05)

        finally:
            # Restore original clipboard
            if original_clipboard is not None:
                try:
                    self.copy_to_clipboard(original_clipboard)
                except Exception:
                    pass  # Best effort restoration
