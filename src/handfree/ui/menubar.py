"""
Menu Bar Component for macOS

Provides a persistent menu bar icon with status and controls.
Uses PyObjC directly for better integration with the existing tkinter event loop.
"""

import os
import sys
import threading
from typing import Callable, Optional

# Only import PyObjC on macOS
MENUBAR_AVAILABLE = False
if sys.platform == "darwin":
    try:
        import objc
        from AppKit import (
            NSStatusBar,
            NSMenu,
            NSMenuItem,
            NSVariableStatusItemLength,
            NSApplication,
            NSObject,
        )
        from Foundation import NSRunLoop, NSDefaultRunLoopMode
        from PyObjCTools import AppHelper
        MENUBAR_AVAILABLE = True
    except ImportError:
        MENUBAR_AVAILABLE = False


class MenuBarDelegate(NSObject):
    """Objective-C delegate for handling menu actions."""

    _history_callback = None
    _quit_callback = None

    def init(self):
        self = objc.super(MenuBarDelegate, self).init()
        return self

    def setHistoryCallback_(self, callback):
        """Set the history toggle callback."""
        self._history_callback = callback

    def setQuitCallback_(self, callback):
        """Set the quit callback."""
        self._quit_callback = callback

    def showHistory_(self, sender):
        """Handle Show History menu click."""
        if self._history_callback:
            self._history_callback()

    def quitApp_(self, sender):
        """Handle Quit menu click."""
        if self._quit_callback:
            self._quit_callback()


class MenuBarApp:
    """
    macOS menu bar application for HandFree.

    Shows a microphone icon that changes based on recording state.
    Provides menu items for history toggle and quit.

    Uses PyObjC directly (not rumps) for better integration with tkinter.
    """

    # Icon characters (using emoji/text for simplicity)
    ICON_IDLE = "🎙️"
    ICON_RECORDING = "🔴"

    def __init__(
        self,
        on_quit: Callable[[], None],
        on_history_toggle: Optional[Callable[[], None]] = None
    ):
        """
        Initialize menu bar app.

        Args:
            on_quit: Callback when Quit is selected
            on_history_toggle: Callback when Show History is selected
        """
        if not MENUBAR_AVAILABLE:
            raise RuntimeError("Menu bar not available (macOS only with PyObjC)")

        self._on_quit = on_quit
        self._on_history_toggle = on_history_toggle
        self._is_recording = False
        self._status_item = None
        self._menu = None
        self._delegate = None
        self._status_menu_item = None
        self._lock = threading.Lock()
        self._initialized = False

    def start(self) -> None:
        """
        Initialize the menu bar item.

        Must be called from the main thread (or a thread with a run loop).
        Fails gracefully if not running in a proper macOS application context.

        Set HANDFREE_DISABLE_MENUBAR=1 to skip menu bar creation (useful for tests).
        """
        if self._initialized:
            return

        # Check if menu bar is disabled via environment variable
        # This is useful for running in pytest where NSStatusBar crashes
        if os.environ.get("HANDFREE_DISABLE_MENUBAR", "").lower() in ("1", "true", "yes"):
            raise RuntimeError("Menu bar disabled via HANDFREE_DISABLE_MENUBAR environment variable")

        try:
            # Create delegate for handling callbacks
            self._delegate = MenuBarDelegate.alloc().init()
            self._delegate.setHistoryCallback_(self._on_history_toggle)
            self._delegate.setQuitCallback_(self._on_quit)

            # Create status bar item
            # Note: This may crash with SIGABRT if not in a proper GUI context
            # (e.g., running in pytest without a display). Use HANDFREE_DISABLE_MENUBAR=1
            # to disable in such environments.
            status_bar = NSStatusBar.systemStatusBar()
            self._status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
            self._status_item.setTitle_(self.ICON_IDLE)
        except Exception as e:
            # Clean up and mark as failed to initialize
            self._delegate = None
            self._status_item = None
            raise RuntimeError(f"Failed to create status bar item: {e}") from e

        # Create menu
        self._menu = NSMenu.alloc().init()

        # Status item (non-clickable)
        self._status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Status: Idle", None, ""
        )
        self._status_menu_item.setEnabled_(False)
        self._menu.addItem_(self._status_menu_item)

        # Separator
        self._menu.addItem_(NSMenuItem.separatorItem())

        # Show History item
        history_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show History", "showHistory:", ""
        )
        history_item.setTarget_(self._delegate)
        self._menu.addItem_(history_item)

        # Separator
        self._menu.addItem_(NSMenuItem.separatorItem())

        # Quit item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit HandFree", "quitApp:", ""
        )
        quit_item.setTarget_(self._delegate)
        self._menu.addItem_(quit_item)

        # Attach menu to status item
        self._status_item.setMenu_(self._menu)

        self._initialized = True

    def set_recording(self, is_recording: bool) -> None:
        """
        Update menu bar to reflect recording state.

        Thread-safe - can be called from any thread.

        Args:
            is_recording: True if recording is active
        """
        with self._lock:
            self._is_recording = is_recording

        if not self._initialized or not self._status_item:
            return

        # Update UI (should be called from main thread, but setTitle_ is generally safe)
        try:
            if is_recording:
                self._status_item.setTitle_(self.ICON_RECORDING)
                if self._status_menu_item:
                    self._status_menu_item.setTitle_("Status: Recording...")
            else:
                self._status_item.setTitle_(self.ICON_IDLE)
                if self._status_menu_item:
                    self._status_menu_item.setTitle_("Status: Idle")
        except Exception:
            # Silently handle any threading issues
            pass

    @property
    def is_recording(self) -> bool:
        """Current recording state."""
        with self._lock:
            return self._is_recording

    def stop(self) -> None:
        """Remove the status bar item."""
        if self._status_item:
            try:
                status_bar = NSStatusBar.systemStatusBar()
                status_bar.removeStatusItem_(self._status_item)
            except Exception:
                pass
            self._status_item = None
        self._initialized = False


def create_menubar_app(
    on_quit: Callable[[], None],
    on_history_toggle: Optional[Callable[[], None]] = None
) -> Optional[MenuBarApp]:
    """
    Create menu bar app if available.

    Returns None if not on macOS or PyObjC not installed.

    Args:
        on_quit: Callback when Quit is selected
        on_history_toggle: Callback when Show History is selected

    Returns:
        MenuBarApp instance or None if not available
    """
    if not MENUBAR_AVAILABLE:
        return None

    try:
        return MenuBarApp(on_quit, on_history_toggle)
    except Exception:
        return None


def is_menubar_available() -> bool:
    """Check if menu bar functionality is available."""
    return MENUBAR_AVAILABLE
