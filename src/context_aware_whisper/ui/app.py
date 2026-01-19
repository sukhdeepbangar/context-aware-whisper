"""
Context-Aware Whisper UI Controller

Manages the UI components in a separate thread with thread-safe state updates.
"""

import sys
import threading
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional


def _set_macos_background_app() -> None:
    """Set the app as a background app that CANNOT receive focus.

    This MUST be called before creating any tkinter windows.
    A background (prohibited) app:
    - Never appears in the Dock
    - Windows appear but CANNOT be activated/focused
    - Does not appear in Cmd+Tab app switcher

    Reference: https://developer.apple.com/documentation/appkit/nsapplication/activationpolicy/prohibited
    """
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyProhibited
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    except Exception:
        pass


from context_aware_whisper.ui.indicator import RecordingIndicator

# Native indicator disabled - causes trace trap crash
# TODO: Investigate PyObjC NSPanel crash
NATIVE_INDICATOR_AVAILABLE = False

# Subprocess indicator for focus-preserving overlay (macOS only)
SUBPROCESS_INDICATOR_AVAILABLE = sys.platform == "darwin"

from context_aware_whisper.ui.history import HistoryPanel
from context_aware_whisper.ui.menubar import create_menubar_app, MenuBarApp
from context_aware_whisper.storage.history_store import HistoryStore, TranscriptionRecord


class CAWUI:
    """
    Main UI controller that runs the tkinter event loop in a daemon thread.

    Provides thread-safe methods to update UI state from the main application thread.
    """

    def __init__(
        self,
        history_enabled: bool = True,
        history_path: Optional[Path] = None,
        indicator_position: str = "top-center",
        menubar_enabled: bool = True,
        on_quit: Optional[Callable[[], None]] = None
    ):
        """
        Initialize UI controller.

        Args:
            history_enabled: Whether to enable history storage and panel
            history_path: Optional path for history file (for testing)
            indicator_position: Position for the recording indicator. One of:
                               top-center, top-right, top-left, bottom-center,
                               bottom-right, bottom-left. Default: top-center.
            menubar_enabled: Whether to enable menu bar icon (macOS only)
            on_quit: Callback when quit is selected from menu bar
        """
        self._root: Optional[tk.Tk] = None
        self._indicator: Optional[RecordingIndicator] = None
        self._native_indicator = None  # NativeRecordingIndicator on macOS
        self._subprocess_indicator = None  # Subprocess indicator for macOS
        self._history_panel: Optional[HistoryPanel] = None
        self._history_store: Optional[HistoryStore] = None
        self._menubar: Optional[MenuBarApp] = None
        self._ui_thread: Optional[threading.Thread] = None
        self._running = False
        self._history_enabled = history_enabled
        self._history_path = history_path
        self._indicator_position = indicator_position
        self._menubar_enabled = menubar_enabled
        self._on_quit = on_quit

    def start(self) -> None:
        """
        Initialize the UI components on the main thread.

        On macOS, tkinter windows MUST be created on the main thread.
        This method creates the UI but does NOT start the mainloop.
        Call run_mainloop() to start the event loop.
        """
        if self._running:
            return

        self._running = True

        # On macOS, set app as background BEFORE creating any windows
        # This prevents the app from ever stealing focus
        _set_macos_background_app()

        # Create root window (hidden) - MUST be on main thread for macOS
        self._root = tk.Tk()
        self._root.withdraw()  # Hide root window

        # TEMPORARILY DISABLED: Tkinter/Native indicators steal focus on macOS
        # Instead, use subprocess indicator which runs in a separate process
        # with NSApplicationActivationPolicyProhibited set before window creation
        self._native_indicator = None
        self._indicator = None
        self._subprocess_indicator = None

        # Launch subprocess indicator on macOS (replaces disabled tkinter indicator)
        if SUBPROCESS_INDICATOR_AVAILABLE:
            try:
                from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator
                self._subprocess_indicator = SubprocessIndicator()
                if not self._subprocess_indicator.start():
                    print("[Warning] Subprocess indicator failed to start")
                    self._subprocess_indicator = None
            except Exception as e:
                print(f"[Warning] Subprocess indicator unavailable: {e}")
                self._subprocess_indicator = None

        # Create history components if enabled
        if self._history_enabled:
            try:
                self._history_store = HistoryStore(path=self._history_path)
                self._history_panel = HistoryPanel(
                    root=self._root,
                    on_copy=self._on_history_copy
                )
                # Load recent entries
                recent = self._history_store.get_recent(limit=50)
                self._history_panel.load_entries(recent)
            except Exception as e:
                # History failed to initialize, continue without it
                print(f"[Warning] History disabled: {e}")
                self._history_store = None
                self._history_panel = None

        # Create menu bar if enabled (macOS only)
        if self._menubar_enabled:
            try:
                self._menubar = create_menubar_app(
                    on_quit=self._on_quit,
                    on_history_toggle=self.toggle_history
                )
                if self._menubar:
                    self._menubar.start()
            except Exception as e:
                # Menu bar failed to initialize, continue without it
                print(f"[Warning] Menu bar disabled: {e}")
                self._menubar = None

    def run_mainloop(self) -> None:
        """
        Run the tkinter mainloop on the current (main) thread.

        This blocks until stop() is called.
        """
        if not self._root:
            return

        try:
            self._root.mainloop()
        except Exception:
            # Silently handle shutdown errors
            pass

    def set_state(self, state: str) -> None:
        """
        Set the indicator state (thread-safe).

        Args:
            state: One of "idle", "recording", "transcribing", "success", "error"
        """
        if not self._running:
            return

        # Forward state to subprocess indicator (focus-preserving)
        if self._subprocess_indicator:
            try:
                self._subprocess_indicator.set_state(state)
            except Exception:
                pass
        # Use native indicator if available (direct call, no thread scheduling needed)
        elif self._native_indicator:
            try:
                self._native_indicator.set_state(state)
            except Exception:
                pass
        elif self._root and self._indicator:
            # Schedule state update in UI thread using after()
            try:
                self._root.after(0, lambda: self._indicator.set_state(state))
            except Exception:
                # Ignore errors if UI is shutting down
                pass

        # Update menu bar recording state
        if self._menubar:
            try:
                is_recording = state == "recording"
                self._menubar.set_recording(is_recording)
            except Exception:
                # Ignore errors if menu bar is unavailable
                pass

    def add_transcription(
        self,
        text: str,
        duration: Optional[float] = None,
        language: Optional[str] = None
    ) -> None:
        """
        Add a transcription to history (thread-safe).

        Stores the transcription in the database and updates the history panel.

        Args:
            text: The transcribed text
            duration: Recording duration in seconds
            language: Language code
        """
        if not self._running or not self._history_store:
            return

        try:
            # Add to database (this happens in calling thread, which is OK for SQLite)
            record_id = self._history_store.add(text, duration, language)

            # Get the full record to display
            record = self._history_store.get_by_id(record_id)
            if record and self._history_panel and self._root:
                # Update panel in UI thread
                self._root.after(0, lambda: self._history_panel.add_entry(record))
        except Exception as e:
            # Log but don't fail
            print(f"[Warning] Failed to save transcription to history: {e}")

    def toggle_history(self) -> None:
        """Toggle the history panel visibility (thread-safe)."""
        if not self._running or not self._history_panel or not self._root:
            return

        try:
            self._root.after(0, self._history_panel.toggle)
        except Exception:
            pass

    def _on_history_copy(self, text: str) -> None:
        """Callback when text is copied from history panel."""
        # Could add notification or other feedback here
        pass

    @property
    def history_enabled(self) -> bool:
        """Whether history feature is enabled and available."""
        return self._history_store is not None

    @property
    def menubar_enabled(self) -> bool:
        """Whether menu bar is enabled and available."""
        return self._menubar is not None

    def stop(self) -> None:
        """
        Stop the UI gracefully.

        Destroys windows and stops the event loop.
        """
        if not self._running:
            return

        self._running = False

        # Stop subprocess indicator first (clean shutdown)
        if self._subprocess_indicator:
            try:
                self._subprocess_indicator.stop()
            except Exception:
                pass
            self._subprocess_indicator = None

        # Stop native indicator if using it
        if self._native_indicator:
            try:
                self._native_indicator.destroy()
            except Exception:
                pass
            self._native_indicator = None

        # Stop menu bar first
        if self._menubar:
            try:
                self._menubar.stop()
            except Exception:
                pass
            self._menubar = None

        if self._root:
            try:
                # Destroy history panel first
                if self._history_panel:
                    self._root.after(0, self._history_panel.destroy)

                # Schedule destruction in UI thread
                self._root.after(0, self._root.quit)
            except Exception:
                # Ignore errors during shutdown
                pass

        # Wait for thread to finish (with timeout)
        if self._ui_thread and self._ui_thread.is_alive():
            self._ui_thread.join(timeout=1.0)
