"""
HandFree UI Module

Provides visual feedback components including recording indicator and history panel.
"""

from handfree.ui.indicator import RecordingIndicator
from handfree.ui.history import HistoryPanel
from handfree.ui.app import HandFreeUI
from handfree.ui.menubar import (
    MenuBarApp,
    create_menubar_app,
    is_menubar_available,
    MENUBAR_AVAILABLE,
)

__all__ = [
    "RecordingIndicator",
    "HistoryPanel",
    "HandFreeUI",
    "MenuBarApp",
    "create_menubar_app",
    "is_menubar_available",
    "MENUBAR_AVAILABLE",
]
