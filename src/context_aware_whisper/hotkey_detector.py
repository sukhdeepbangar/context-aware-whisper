"""
Hotkey Detector Module
Detects Fn/Globe key press using macOS CGEvent tap.
Hold Fn to record, release to transcribe.
"""

import threading
from typing import Callable, Optional

import Quartz
from Quartz import (
    CGEventTapCreate, kCGSessionEventTap, kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly, CGEventMaskBit, kCGEventFlagsChanged,
    CFMachPortCreateRunLoopSource, CFRunLoopGetCurrent, CFRunLoopAddSource,
    kCFRunLoopCommonModes, CFRunLoopRunInMode, kCFRunLoopDefaultMode,
    CGEventGetFlags
)

# Fn key constants
FN_KEYCODE = 63
FN_FLAG = 0x800000


class HotkeyDetector:
    """Detects Fn/Globe key for recording toggle using CGEvent tap."""

    def __init__(self, on_start: Callable[[], None], on_stop: Callable[[], None]):
        """
        Initialize hotkey detector with start/stop callbacks.

        Args:
            on_start: Called when Fn key is pressed (start recording)
            on_stop: Called when Fn key is released (stop recording)
        """
        self.on_start = on_start
        self.on_stop = on_stop
        self._is_recording = False
        self._tap = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _event_callback(self, proxy, event_type, event, refcon):
        """Handle CGEvent callback for Fn key detection."""
        keycode = Quartz.CGEventGetIntegerValueField(
            event, Quartz.kCGKeyboardEventKeycode
        )

        # Only handle Fn key (keycode 63)
        if keycode == FN_KEYCODE:
            flags = CGEventGetFlags(event)
            fn_pressed = (flags & FN_FLAG) != 0

            if fn_pressed and not self._is_recording:
                # Fn pressed - start recording
                self._is_recording = True
                self.on_start()
            elif not fn_pressed and self._is_recording:
                # Fn released - stop recording
                self._is_recording = False
                self.on_stop()

        return event

    def _run_loop(self) -> None:
        """Run the CGEvent tap loop in a thread."""
        mask = CGEventMaskBit(kCGEventFlagsChanged)

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

    @property
    def is_recording(self) -> bool:
        """Whether recording is currently active."""
        return self._is_recording

    def start(self) -> None:
        """Start listening for Fn key."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("Hotkey detector started. Hold Fn/Globe key to record.")

    def stop(self) -> None:
        """Stop listening and clean up."""
        self._running = False
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
            self._tap = None
