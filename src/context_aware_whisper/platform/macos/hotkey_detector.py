"""
macOS Hotkey Detector

Detects Fn/Globe key press using macOS CGEvent tap.
Hold Fn to record, release to transcribe.
Also detects Cmd+Shift+H for history panel toggle.
"""

import queue
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

from context_aware_whisper.platform.base import HotkeyDetectorBase

# Fn key constants
FN_KEYCODE = 63
FN_FLAG = 0x800000

# History toggle hotkey constants
H_KEYCODE = 4  # 'h' key on macOS
CMD_FLAG = Quartz.kCGEventFlagMaskCommand  # Command key flag
SHIFT_FLAG = Quartz.kCGEventFlagMaskShift  # Shift key flag


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
            on_history_toggle: Called when Cmd+Shift+H is pressed (toggle history)
        """
        super().__init__(on_start, on_stop, on_history_toggle)
        self._tap = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback_queue: queue.Queue = queue.Queue()
        self._callback_thread: Optional[threading.Thread] = None

    def _callback_worker(self) -> None:
        """Process callbacks from queue in a separate thread.

        This prevents blocking the CFRunLoop callback, which can cause
        trace traps when doing heavy work (subprocess, SQLite, etc.).
        """
        while self._running:
            try:
                callback = self._callback_queue.get(timeout=0.1)
                if callback is not None:
                    callback()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Callback error: {e}")

    def _dispatch_callback(self, callback: Callable[[], None]) -> None:
        """Dispatch callback to worker thread or call directly.

        If the callback worker is running, queue the callback for async processing.
        Otherwise (e.g., in tests), call the callback directly.
        """
        if self._callback_thread and self._callback_thread.is_alive():
            self._callback_queue.put(callback)
        else:
            # Worker not running (e.g., in tests) - call directly
            callback()

    def _event_callback(self, proxy, event_type, event, refcon):
        """Handle CGEvent callback for Fn key and Cmd+H detection.

        Dispatches actual callbacks to a worker thread to avoid blocking
        the CFRunLoop, which can cause trace traps on macOS.
        """
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
                self._dispatch_callback(self.on_start)
            elif not fn_pressed and self._is_recording:
                # Fn released - stop recording
                self._is_recording = False
                self._dispatch_callback(self.on_stop)

        # Handle Cmd+Shift+H for history toggle
        elif event_type == kCGEventKeyDown and keycode == H_KEYCODE:
            cmd_pressed = (flags & CMD_FLAG) != 0
            shift_pressed = (flags & SHIFT_FLAG) != 0
            if cmd_pressed and shift_pressed and self.on_history_toggle:
                self._dispatch_callback(self.on_history_toggle)

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
        return "Cmd+Shift+H"

    def start(self) -> None:
        """Start listening for Fn key."""
        self._running = True
        # Start callback worker thread (processes callbacks outside CFRunLoop)
        self._callback_thread = threading.Thread(target=self._callback_worker, daemon=True)
        self._callback_thread.start()
        # Start event tap thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"Hotkey detector started. Hold {self.get_hotkey_description()} to record.")

    def stop(self) -> None:
        """Stop listening and clean up."""
        self._running = False
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
            self._tap = None
