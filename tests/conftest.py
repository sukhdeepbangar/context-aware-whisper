"""
Pytest configuration and fixtures for context-aware-whisper tests.

IMPORTANT: This file sets up mocks for macOS-specific and tkinter modules
BEFORE any test imports happen. This prevents hangs when running full test suite.

PERFORMANCE: Common fixtures are cached at session/module level to avoid
repeated setup overhead in tests.
"""

import io
import sys
from functools import lru_cache
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from scipy.io import wavfile


def _setup_global_mocks():
    """
    Set up mocks for modules that may not be available or cause issues during testing.

    This must run before any test modules are imported to prevent:
    - tkinter import failures/hangs on headless systems
    - macOS-specific module import failures on non-macOS systems
    - NSStatusBar SIGABRT crashes in pytest (menu bar disabled)
    """
    import os

    # Disable menu bar to prevent SIGABRT crashes from NSStatusBar in pytest
    os.environ["CAW_DISABLE_MENUBAR"] = "1"
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
        # Version attributes must be real numbers for comparison operations
        mock_tk.TkVersion = 8.6
        mock_tk.TclVersion = 8.6
        # String constants
        mock_tk.X = 'x'
        mock_tk.Y = 'y'
        mock_tk.BOTH = 'both'
        mock_tk.LEFT = 'left'
        mock_tk.RIGHT = 'right'
        mock_tk.TOP = 'top'
        mock_tk.BOTTOM = 'bottom'
        mock_tk.VERTICAL = 'vertical'
        mock_tk.FLAT = 'flat'
        mock_tk.END = 'end'
        mock_tk.NORMAL = 'normal'
        mock_tk.DISABLED = 'disabled'
        mock_tk.WORD = 'word'
        mock_tk.NONE = 'none'
        sys.modules['_tkinter'] = MagicMock()
        sys.modules['tkinter'] = mock_tk
        sys.modules['tkinter.ttk'] = MagicMock()

    # Mock macOS-specific modules if not on macOS
    if sys.platform != 'darwin':
        # Create a mock NSObject class that can be subclassed
        class MockNSObject:
            pass

        # Mock objc module (from pyobjc-core)
        if 'objc' not in sys.modules:
            mock_objc = MagicMock()
            mock_objc.NSObject = MockNSObject
            sys.modules['objc'] = mock_objc

        # Mock Foundation with NSObject
        if 'Foundation' not in sys.modules:
            mock_foundation = MagicMock()
            mock_foundation.NSObject = MockNSObject
            mock_foundation.NSNotificationCenter = MagicMock()
            sys.modules['Foundation'] = mock_foundation

        if 'AVFAudio' not in sys.modules:
            sys.modules['AVFAudio'] = MagicMock()
        if 'Quartz' not in sys.modules:
            mock_quartz = MagicMock()
            mock_quartz.CGEventTapCreate = MagicMock()
            mock_quartz.CGEventMaskBit = MagicMock()
            sys.modules['Quartz'] = mock_quartz
        if 'AppKit' not in sys.modules:
            mock_appkit = MagicMock()
            mock_appkit.NSObject = MockNSObject
            mock_appkit.NSApplication = MagicMock()
            sys.modules['AppKit'] = mock_appkit

        # Mock Cocoa (used by rumps and pyobjc)
        if 'Cocoa' not in sys.modules:
            mock_cocoa = MagicMock()
            mock_cocoa.NSObject = MockNSObject
            sys.modules['Cocoa'] = mock_cocoa

        # Mock rumps (macOS menu bar library)
        if 'rumps' not in sys.modules:
            mock_rumps = MagicMock()
            mock_rumps.App = MagicMock()
            mock_rumps.MenuItem = MagicMock()
            mock_rumps.clicked = MagicMock()
            sys.modules['rumps'] = mock_rumps

    # Mock pynput if DISPLAY not available (headless CI on Linux)
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'):
        if 'pynput' not in sys.modules:
            mock_keyboard = MagicMock()
            mock_keyboard.Listener = MagicMock()
            mock_keyboard.Key = MagicMock()
            mock_keyboard.Key.ctrl_l = MagicMock(name='ctrl_l')
            mock_keyboard.Key.ctrl_r = MagicMock(name='ctrl_r')
            mock_keyboard.Key.shift = MagicMock(name='shift')
            mock_keyboard.Key.space = MagicMock(name='space')
            sys.modules['pynput'] = MagicMock()
            sys.modules['pynput.keyboard'] = mock_keyboard


# Run mocks setup immediately when conftest is loaded
_setup_global_mocks()


import pytest


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require hardware)"
    )


# =============================================================================
# LOGGING PROTECTION
# =============================================================================

import logging

@pytest.fixture(autouse=True)
def _protect_logging_handlers():
    """
    Protect logging handlers from being corrupted by mocks.

    Some tests use MagicMock which can inadvertently replace logging handler
    attributes (like 'level') with MagicMock objects, causing TypeError when
    Python's logging module tries to compare log levels.

    This fixture ensures all handlers have proper integer levels before and
    after each test.
    """
    def _fix_handler_levels():
        """Ensure all logging handlers have integer levels."""
        for handler in logging.root.handlers[:]:
            if not isinstance(handler.level, int):
                handler.level = logging.NOTSET
        # Also fix levels on named loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                if not isinstance(handler.level, int):
                    handler.level = logging.NOTSET

    _fix_handler_levels()
    yield
    _fix_handler_levels()


# =============================================================================
# CACHED TEST DATA GENERATION
# =============================================================================

@lru_cache(maxsize=16)
def create_test_audio(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """
    Create valid WAV audio bytes (cached for performance).

    This function is cached because test audio generation involves expensive
    numpy operations and WAV encoding. Most tests use the same audio parameters.

    Args:
        duration_sec: Duration of audio in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        WAV file as bytes.
    """
    # Generate simple sine wave (440 Hz tone)
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
    audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    # Encode as WAV
    wav_buffer = io.BytesIO()
    wavfile.write(wav_buffer, sample_rate, audio_data)
    wav_buffer.seek(0)
    return wav_buffer.getvalue()


# =============================================================================
# SESSION-SCOPED FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def groq_api_key_env(session_mocker):
    """
    Session-scoped fixture to set GROQ_API_KEY environment variable.

    Using session scope avoids repeated monkeypatch setup/teardown for each test.
    """
    import os
    original = os.environ.get("GROQ_API_KEY")
    os.environ["GROQ_API_KEY"] = "test-api-key"
    yield "test-api-key"
    if original is None:
        os.environ.pop("GROQ_API_KEY", None)
    else:
        os.environ["GROQ_API_KEY"] = original


@pytest.fixture(scope="session")
def session_mocker():
    """Session-scoped mocker placeholder for compatibility."""
    yield


# =============================================================================
# FUNCTION-SCOPED FIXTURES (for tests that need fresh state)
# =============================================================================

@pytest.fixture
def test_audio():
    """Provide cached test audio bytes (1 second duration)."""
    return create_test_audio(1.0, 16000)


@pytest.fixture
def test_audio_short():
    """Provide cached short test audio bytes (0.1 second)."""
    return create_test_audio(0.1, 16000)


@pytest.fixture
def mock_groq_env(monkeypatch):
    """Set up GROQ_API_KEY environment variable for a single test."""
    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")


# =============================================================================
# HARDWARE DETECTION FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def has_microphone() -> bool:
    """Check if a microphone is available."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        return len(input_devices) > 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def has_whisper_model() -> bool:
    """Check if whisper.cpp model is available."""
    from pathlib import Path
    model_path = Path.home() / ".cache" / "whisper" / "ggml-base.en.bin"
    return model_path.exists()


@pytest.fixture(scope="session")
def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    import os
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"]
    return any(os.environ.get(var) for var in ci_vars)


@pytest.fixture(scope="session")
def has_accessibility_permission() -> bool:
    """Check if accessibility permission is granted (macOS)."""
    if sys.platform != "darwin":
        return True
    try:
        import subprocess
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to return name of first process'],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# =============================================================================
# AUTO-SKIP FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def _auto_skip_by_marker(request, has_microphone, has_whisper_model, has_accessibility_permission):
    """Automatically skip tests based on markers."""
    if request.node.get_closest_marker("requires_microphone") and not has_microphone:
        pytest.skip("No microphone available")

    if request.node.get_closest_marker("requires_whisper") and not has_whisper_model:
        pytest.skip("Whisper model not downloaded")

    if request.node.get_closest_marker("requires_macos") and sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    if request.node.get_closest_marker("requires_accessibility") and not has_accessibility_permission:
        pytest.skip("Accessibility permission not granted")
