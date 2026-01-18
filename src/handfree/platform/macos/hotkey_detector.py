"""
macOS Hotkey Detector

Detects Fn/Globe key press using macOS CGEvent tap.
Hold Fn to record, release to transcribe.
Also detects Cmd+H for history panel toggle.
"""

import threading
from typing import Callable, Optional

import Quartz
from Quartz import (
    CGEventTapCreate, kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly, CGEventMaskBit, kCGEventFlagsChanged,
    kCGEventKeyDown,
    CFMachPortCreateRunLoopSource, CFRunLoopGetCurrent, CFRunLoopAddSource,
    kCFRunLoopCommonModes, CFRunLoopRunInMode, kCFRunLoopDefaultMode,
    CGEventGetFlags
)

from handfree.platform.base import HotkeyDetectorBase

# Fn key constants
FN_KEYCODE = 63
FN_FLAG = 0x800000

# History toggle hotkey constants
H_KEYCODE = 4  # 'h' key on macOS
CMD_FLAG = Quartz.kCGEventFlagMaskCommand  # Command key flag


class MacOSHotkeyDetector(HotkeyDetectorBase):
    """Detects Fn/Globe key for recording toggle using CGEvent tap."""

    def __init__(
        self,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_history_toggle: Callable[[], None] | None = None
    ):
        """
        Initialize hotkey detector with start/stop callbacks.

        Args:
            on_start: Called when Fn key is pressed (start recording)
            on_stop: Called when Fn key is released (stop recording)
            on_history_toggle: Called when Cmd+H is pressed (toggle history)
        """
        super().__init__(on_start, on_stop, on_history_toggle)
        self._tap = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _event_callback(self, proxy, event_type, event, refcon):
        """Handle CGEvent callback for Fn key and Cmd+H detection."""
        keycode = Quartz.CGEventGetIntegerValueField(
            event, Quartz.kCGKeyboardEventKeycode
        )
        flags = CGEventGetFlags(event)

        # Handle Fn key (keycode 63) for recording toggle
        if keycode == FN_KEYCODE and event_type == kCGEventFlagsChanged:
            fn_pressed = (flags & FN_FLAG) != 0

            if fn_pressed and not self._is_recording:
                # Fn pressed - start recording
                self._is_recording = True
                self.on_start()
            elif not fn_pressed and self._is_recording:
                # Fn released - stop recording
                self._is_recording = False
                self.on_stop()

        # Handle Cmd+H for history toggle
        elif event_type == kCGEventKeyDown and keycode == H_KEYCODE:
            cmd_pressed = (flags & CMD_FLAG) != 0
            if cmd_pressed and self.on_history_toggle:
                self.on_history_toggle()

        return event

    def _run_loop(self) -> None:
        """Run the CGEvent tap loop in a thread."""
        # Listen for both flag changes (Fn key) and key down events (Cmd+H)
        mask = CGEventMaskBit(kCGEventFlagsChanged) | CGEventMaskBit(kCGEventKeyDown)

        self._tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            mask,
            self._event_callback,
            None
        )

        if self._tap is None:
            print("Error: Failed to create event tap.")
            print("Please grant Accessibility permission in System Settings.")
            return

        source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)

        while self._running:
            CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, False)

    def get_hotkey_description(self) -> str:
        """Get human-readable description of the hotkey."""
        return "Fn/Globe key"

    def get_history_toggle_description(self) -> str:
        """Get human-readable description of the history toggle hotkey."""
        return "Cmd+H"

    def start(self) -> None:
        """Start listening for Fn key."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"Hotkey detector started. Hold {self.get_hotkey_description()} to record.")

    def stop(self) -> None:
        """Stop listening and clean up."""
        self._running = False
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
            self._tap = None
