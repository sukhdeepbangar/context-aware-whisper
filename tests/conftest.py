"""
Pytest configuration and fixtures for handfree tests.

IMPORTANT: This file sets up mocks for macOS-specific and tkinter modules
BEFORE any test imports happen. This prevents hangs when running full test suite.
"""

import sys
from unittest.mock import MagicMock


def _setup_global_mocks():
    """
    Set up mocks for modules that may not be available or cause issues during testing.

    This must run before any test modules are imported to prevent:
    - tkinter import failures/hangs on headless systems
    - macOS-specific module import failures on non-macOS systems
    """
    # Mock tkinter if not available (headless environments)
    if '_tkinter' not in sys.modules:
        mock_tk = MagicMock()
        mock_tk.Tk = MagicMock(return_value=MagicMock())
        mock_tk.Toplevel = MagicMock(return_value=MagicMock())
        mock_tk.Canvas = MagicMock(return_value=MagicMock())
        mock_tk.Frame = MagicMock(return_value=MagicMock())
        mock_tk.Label = MagicMock(return_value=MagicMock())
        mock_tk.Button = MagicMock(return_value=MagicMock())
        mock_tk.TclError = Exception
        mock_tk.X = 'x'
        mock_tk.Y = 'y'
        mock_tk.BOTH = 'both'
        mock_tk.LEFT = 'left'
        mock_tk.RIGHT = 'right'
        mock_tk.TOP = 'top'
        mock_tk.BOTTOM = 'bottom'
        mock_tk.VERTICAL = 'vertical'
        mock_tk.FLAT = 'flat'
        sys.modules['_tkinter'] = MagicMock()
        sys.modules['tkinter'] = mock_tk
        sys.modules['tkinter.ttk'] = MagicMock()

    # Mock macOS-specific modules if not on macOS
    if sys.platform != 'darwin':
        if 'Foundation' not in sys.modules:
            sys.modules['Foundation'] = MagicMock()
        if 'AVFAudio' not in sys.modules:
            sys.modules['AVFAudio'] = MagicMock()
        if 'Quartz' not in sys.modules:
            sys.modules['Quartz'] = MagicMock()
        if 'AppKit' not in sys.modules:
            sys.modules['AppKit'] = MagicMock()


# Run mocks setup immediately when conftest is loaded
_setup_global_mocks()


import pytest


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require hardware)"
    )
