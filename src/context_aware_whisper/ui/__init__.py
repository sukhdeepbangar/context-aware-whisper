"""
Context-Aware Whisper UI Module

Provides visual feedback components including recording indicator and history panel.
"""

from context_aware_whisper.ui.indicator import RecordingIndicator
from context_aware_whisper.ui.history import HistoryPanel
from context_aware_whisper.ui.app import CAWUI
from context_aware_whisper.ui.menubar import (
    MenuBarApp,
    create_menubar_app,
    is_menubar_available,
    MENUBAR_AVAILABLE,
)

__all__ = [
    "RecordingIndicator",
    "HistoryPanel",
    "CAWUI",
    "MenuBarApp",
    "create_menubar_app",
    "is_menubar_available",
    "MENUBAR_AVAILABLE",
]
