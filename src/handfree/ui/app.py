"""
HandFree UI Controller

Manages the UI components in a separate thread with thread-safe state updates.
"""

import threading
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

from handfree.ui.indicator import RecordingIndicator
from handfree.ui.history import HistoryPanel
from handfree.ui.menubar import create_menubar_app, MenuBarApp
from handfree.storage.history_store import HistoryStore, TranscriptionRecord


class HandFreeUI:
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

        # Create root window (hidden) - MUST be on main thread for macOS
        self._root = tk.Tk()
        self._root.withdraw()  # Hide root window

        # Create indicator with configured position
        self._indicator = RecordingIndicator(root=self._root, position=self._indicator_position)

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
        if not self._running or not self._root or not self._indicator:
            return

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
