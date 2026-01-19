"""
Mute Detector Module
Detects input mute state changes using macOS AVFAudio framework.
Requires macOS 14 (Sonoma) or later.
Note: This module is deprecated - use hotkey_detector.py instead.
"""

from typing import Callable, Optional
from AVFAudio import AVAudioApplication, AVAudioSession
from Foundation import NSNotificationCenter


class MuteDetector:
    """Detects input mute state changes via AVAudioApplication API (deprecated)."""

    def __init__(self, on_mute: Callable[[], None], on_unmute: Callable[[], None]):
        """
        Initialize mute detector with callbacks.

        Args:
            on_mute: Called when input is muted
            on_unmute: Called when input is unmuted
        """
        self.on_mute = on_mute
        self.on_unmute = on_unmute
        self._observer: Optional[object] = None
        self._session: Optional[AVAudioSession] = None
        self._last_mute_state: Optional[bool] = None

    def _handle_notification(self, notification) -> None:
        """Handle mute state change notification."""
        # Get current mute state
        app = AVAudioApplication.sharedInstance()
        is_muted = app.isInputMuted()

        # Only trigger callback if state actually changed
        if is_muted != self._last_mute_state:
            self._last_mute_state = is_muted
            if is_muted:
                self.on_mute()
            else:
                self.on_unmute()

    def start(self) -> None:
        """
        Start listening for mute state changes.
        Must be called from main thread.
        """
        # Set up audio session
        self._session = AVAudioSession.sharedInstance()

        # Configure session for recording
        success = self._session.setCategory_mode_options_error_(
            "AVAudioSessionCategoryPlayAndRecord",
            "AVAudioSessionModeDefault",
            0,
            None
        )
        if not success:
            raise RuntimeError("Failed to set audio session category")

        # Activate session
        success = self._session.setActive_error_(True, None)
        if not success:
            raise RuntimeError("Failed to activate audio session")

        # Get initial mute state
        app = AVAudioApplication.sharedInstance()
        self._last_mute_state = app.isInputMuted()

        # Register for mute notifications
        center = NSNotificationCenter.defaultCenter()
        self._observer = center.addObserverForName_object_queue_usingBlock_(
            "AVAudioApplicationInputMuteStateChangeNotification",
            None,
            None,
            self._handle_notification
        )

        print(f"Mute detector started. Initial state: {'muted' if self._last_mute_state else 'unmuted'}")

    def stop(self) -> None:
        """Stop listening and clean up resources."""
        if self._observer:
            center = NSNotificationCenter.defaultCenter()
            center.removeObserver_(self._observer)
            self._observer = None

        if self._session:
            self._session.setActive_error_(False, None)
            self._session = None

    @property
    def is_muted(self) -> bool:
        """Current mute state."""
        app = AVAudioApplication.sharedInstance()
        return app.isInputMuted()
