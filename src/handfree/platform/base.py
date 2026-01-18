"""
Platform Abstraction - Base Classes

This module defines abstract base classes for platform-specific components.
Each platform (macOS, Windows, Linux) implements these interfaces with
platform-appropriate code.
"""

from abc import ABC, abstractmethod
from typing import Callable


class HotkeyDetectorBase(ABC):
    """
    Abstract base class for hotkey detection.

    Each platform implements this to detect the hold-to-record hotkey:
    - macOS: Fn/Globe key (keycode 63) via CGEvent tap
    - Windows/Linux: Ctrl+Shift+Space via pynput

    Additionally supports a secondary hotkey for toggling history panel:
    - macOS: Cmd+H
    - Windows/Linux: Ctrl+H
    """

    def __init__(
        self,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_history_toggle: Callable[[], None] | None = None
    ):
        """
        Initialize hotkey detector with start/stop callbacks.

        Args:
            on_start: Called when hotkey is pressed (start recording)
            on_stop: Called when hotkey is released (stop recording)
            on_history_toggle: Called when history toggle hotkey is pressed (optional)
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_history_toggle = on_history_toggle
        self._is_recording = False

    @abstractmethod
    def start(self) -> None:
        """Start listening for the hotkey."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and clean up resources."""
        pass

    @abstractmethod
    def get_hotkey_description(self) -> str:
        """
        Get human-readable description of the hotkey.

        Returns:
            Description like "Fn/Globe key" or "Ctrl+Shift+Space"
        """
        pass

    @property
    def is_recording(self) -> bool:
        """Whether recording is currently active."""
        return self._is_recording

    @abstractmethod
    def get_history_toggle_description(self) -> str:
        """
        Get human-readable description of the history toggle hotkey.

        Returns:
            Description like "Cmd+H" or "Ctrl+H"
        """
        pass


class OutputHandlerBase(ABC):
    """
    Abstract base class for text output handling.

    Each platform implements this to copy text to clipboard and type
    into the active application:
    - macOS: AppleScript via osascript
    - Windows/Linux: pynput keyboard controller
    """

    def __init__(self, type_delay: float = 0.0):
        """
        Initialize output handler.

        Args:
            type_delay: Delay between keystrokes in seconds (0 = fastest)
        """
        self.type_delay = type_delay

    @abstractmethod
    def copy_to_clipboard(self, text: str) -> None:
        """
        Copy text to system clipboard.

        Args:
            text: Text to copy to clipboard

        Raises:
            OutputError: If clipboard operation fails
        """
        pass

    @abstractmethod
    def type_text(self, text: str) -> None:
        """
        Type text into active application.

        Args:
            text: Text to type into the active application

        Raises:
            OutputError: If typing operation fails
        """
        pass

    @abstractmethod
    def type_text_via_paste(self, text: str) -> None:
        """
        Copy text to clipboard and paste using keyboard shortcut.

        This can be more reliable for special characters.

        Args:
            text: Text to paste into the active application

        Raises:
            OutputError: If operation fails
        """
        pass

    def output(self, text: str, use_paste: bool = False) -> None:
        """
        Copy text to clipboard AND type/paste into active app.

        Args:
            text: Transcribed text to output
            use_paste: If True, use clipboard paste instead of keystroke typing

        Raises:
            OutputError: If output operation fails
        """
        if not text:
            return

        # Always copy to clipboard first (as backup)
        self.copy_to_clipboard(text)

        # Then type or paste into active app
        if use_paste:
            self.type_text_via_paste(text)
        else:
            self.type_text(text)
