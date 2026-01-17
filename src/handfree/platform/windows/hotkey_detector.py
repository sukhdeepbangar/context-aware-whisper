"""
Windows Hotkey Detector

Detects Ctrl+Shift+Space key combination using pynput.
Hold the keys to record, release to transcribe.
"""

import threading
from typing import Callable, Optional

from pynput import keyboard

from handfree.platform.base import HotkeyDetectorBase


class WindowsHotkeyDetector(HotkeyDetectorBase):
    """Detects Ctrl+Shift+Space for recording toggle using pynput."""

    # Keys that must all be pressed to trigger recording
    TRIGGER_KEYS = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.Key.space}
    ALT_TRIGGER_KEYS = {keyboard.Key.ctrl_r, keyboard.Key.shift, keyboard.Key.space}

    def __init__(self, on_start: Callable[[], None], on_stop: Callable[[], None]):
        """
        Initialize hotkey detector with start/stop callbacks.

        Args:
            on_start: Called when hotkey is pressed (start recording)
            on_stop: Called when hotkey is released (stop recording)
        """
        super().__init__(on_start, on_stop)
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: set = set()
        self._thread: Optional[threading.Thread] = None

    def _normalize_key(self, key) -> keyboard.Key:
        """Normalize key to handle left/right variants."""
        # Map right ctrl to left ctrl for comparison
        if key == keyboard.Key.ctrl_r:
            return keyboard.Key.ctrl_l
        if key == keyboard.Key.shift_r:
            return keyboard.Key.shift
        return key

    def _check_trigger(self) -> bool:
        """Check if trigger key combination is pressed."""
        normalized = {self._normalize_key(k) for k in self._pressed_keys}
        return self.TRIGGER_KEYS.issubset(normalized)

    def _on_press(self, key) -> None:
        """Handle key press event."""
        self._pressed_keys.add(key)

        if self._check_trigger() and not self._is_recording:
            self._is_recording = True
            self.on_start()

    def _on_release(self, key) -> None:
        """Handle key release event."""
        self._pressed_keys.discard(key)

        # If we were recording and trigger is no longer fully pressed
        if self._is_recording and not self._check_trigger():
            self._is_recording = False
            self.on_stop()

    def get_hotkey_description(self) -> str:
        """Get human-readable description of the hotkey."""
        return "Ctrl+Shift+Space"

    def start(self) -> None:
        """Start listening for the hotkey."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
        print(f"Hotkey detector started. Hold {self.get_hotkey_description()} to record.")

    def stop(self) -> None:
        """Stop listening and clean up."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()
