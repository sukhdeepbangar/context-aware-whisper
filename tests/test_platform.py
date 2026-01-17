"""
Test suite for Platform Abstraction Layer.

Includes unit tests for platform detection, factory functions,
and platform-specific implementations.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

import pytest

from handfree.platform import (
    get_platform,
    create_hotkey_detector,
    create_output_handler,
    is_mute_detector_available,
    get_default_hotkey_description,
    HotkeyDetectorBase,
    OutputHandlerBase,
)
from handfree.exceptions import PlatformNotSupportedError


class TestGetPlatform(unittest.TestCase):
    """Tests for platform detection."""

    def test_get_platform_returns_string(self):
        """Test that get_platform returns a string."""
        result = get_platform()
        self.assertIsInstance(result, str)

    def test_get_platform_valid_value(self):
        """Test that get_platform returns a valid platform identifier."""
        result = get_platform()
        self.assertIn(result, ["macos", "windows", "linux", "unknown"])

    @patch.object(sys, 'platform', 'darwin')
    def test_get_platform_macos(self):
        """Test platform detection on macOS."""
        result = get_platform()
        self.assertEqual(result, "macos")

    @patch.object(sys, 'platform', 'win32')
    def test_get_platform_windows(self):
        """Test platform detection on Windows."""
        result = get_platform()
        self.assertEqual(result, "windows")

    @patch.object(sys, 'platform', 'linux')
    def test_get_platform_linux(self):
        """Test platform detection on Linux."""
        result = get_platform()
        self.assertEqual(result, "linux")

    @patch.object(sys, 'platform', 'linux2')
    def test_get_platform_linux_variant(self):
        """Test platform detection on older Linux identifier."""
        result = get_platform()
        self.assertEqual(result, "linux")

    @patch.object(sys, 'platform', 'freebsd')
    def test_get_platform_unknown(self):
        """Test platform detection returns unknown for unsupported platforms."""
        result = get_platform()
        self.assertEqual(result, "unknown")


class TestIsMuteDetectorAvailable(unittest.TestCase):
    """Tests for mute detector availability check."""

    @patch.object(sys, 'platform', 'darwin')
    def test_mute_detector_available_on_macos(self):
        """Test mute detector is available on macOS."""
        result = is_mute_detector_available()
        self.assertTrue(result)

    @patch.object(sys, 'platform', 'win32')
    def test_mute_detector_not_available_on_windows(self):
        """Test mute detector is not available on Windows."""
        result = is_mute_detector_available()
        self.assertFalse(result)

    @patch.object(sys, 'platform', 'linux')
    def test_mute_detector_not_available_on_linux(self):
        """Test mute detector is not available on Linux."""
        result = is_mute_detector_available()
        self.assertFalse(result)


class TestGetDefaultHotkeyDescription(unittest.TestCase):
    """Tests for hotkey description retrieval."""

    @patch.object(sys, 'platform', 'darwin')
    def test_hotkey_description_macos(self):
        """Test hotkey description on macOS."""
        result = get_default_hotkey_description()
        self.assertEqual(result, "Fn/Globe key")

    @patch.object(sys, 'platform', 'win32')
    def test_hotkey_description_windows(self):
        """Test hotkey description on Windows."""
        result = get_default_hotkey_description()
        self.assertEqual(result, "Ctrl+Shift+Space")

    @patch.object(sys, 'platform', 'linux')
    def test_hotkey_description_linux(self):
        """Test hotkey description on Linux."""
        result = get_default_hotkey_description()
        self.assertEqual(result, "Ctrl+Shift+Space")

    @patch.object(sys, 'platform', 'freebsd')
    def test_hotkey_description_unknown(self):
        """Test hotkey description on unknown platform."""
        result = get_default_hotkey_description()
        self.assertEqual(result, "Unknown")


class TestHotkeyDetectorBase(unittest.TestCase):
    """Tests for HotkeyDetectorBase abstract class."""

    def test_is_abstract(self):
        """Test that HotkeyDetectorBase cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            HotkeyDetectorBase(lambda: None, lambda: None)

    def test_concrete_implementation(self):
        """Test that a concrete implementation can be instantiated."""
        class ConcreteDetector(HotkeyDetectorBase):
            def start(self):
                pass
            def stop(self):
                pass
            def get_hotkey_description(self):
                return "Test"

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = ConcreteDetector(on_start, on_stop)

        self.assertEqual(detector.on_start, on_start)
        self.assertEqual(detector.on_stop, on_stop)
        self.assertFalse(detector.is_recording)

    def test_is_recording_property(self):
        """Test is_recording property tracks internal state."""
        class ConcreteDetector(HotkeyDetectorBase):
            def start(self):
                pass
            def stop(self):
                pass
            def get_hotkey_description(self):
                return "Test"

        detector = ConcreteDetector(lambda: None, lambda: None)
        self.assertFalse(detector.is_recording)

        detector._is_recording = True
        self.assertTrue(detector.is_recording)


class TestOutputHandlerBase(unittest.TestCase):
    """Tests for OutputHandlerBase abstract class."""

    def test_is_abstract(self):
        """Test that OutputHandlerBase cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            OutputHandlerBase(type_delay=0.0)

    def test_concrete_implementation(self):
        """Test that a concrete implementation can be instantiated."""
        class ConcreteHandler(OutputHandlerBase):
            def copy_to_clipboard(self, text):
                pass
            def type_text(self, text):
                pass
            def type_text_via_paste(self, text):
                pass

        handler = ConcreteHandler(type_delay=0.05)
        self.assertEqual(handler.type_delay, 0.05)

    def test_output_method_uses_type_text(self):
        """Test output method calls type_text when use_paste=False."""
        class ConcreteHandler(OutputHandlerBase):
            def __init__(self, type_delay):
                super().__init__(type_delay)
                self.clipboard_called = False
                self.type_text_called = False
                self.paste_called = False

            def copy_to_clipboard(self, text):
                self.clipboard_called = True

            def type_text(self, text):
                self.type_text_called = True

            def type_text_via_paste(self, text):
                self.paste_called = True

        handler = ConcreteHandler(0.0)
        handler.output("Test", use_paste=False)

        self.assertTrue(handler.clipboard_called)
        self.assertTrue(handler.type_text_called)
        self.assertFalse(handler.paste_called)

    def test_output_method_uses_paste(self):
        """Test output method calls type_text_via_paste when use_paste=True."""
        class ConcreteHandler(OutputHandlerBase):
            def __init__(self, type_delay):
                super().__init__(type_delay)
                self.clipboard_called = False
                self.type_text_called = False
                self.paste_called = False

            def copy_to_clipboard(self, text):
                self.clipboard_called = True

            def type_text(self, text):
                self.type_text_called = True

            def type_text_via_paste(self, text):
                self.paste_called = True

        handler = ConcreteHandler(0.0)
        handler.output("Test", use_paste=True)

        self.assertTrue(handler.clipboard_called)
        self.assertFalse(handler.type_text_called)
        self.assertTrue(handler.paste_called)

    def test_output_empty_string(self):
        """Test output method does nothing for empty string."""
        class ConcreteHandler(OutputHandlerBase):
            def __init__(self, type_delay):
                super().__init__(type_delay)
                self.clipboard_called = False

            def copy_to_clipboard(self, text):
                self.clipboard_called = True

            def type_text(self, text):
                pass

            def type_text_via_paste(self, text):
                pass

        handler = ConcreteHandler(0.0)
        handler.output("")

        self.assertFalse(handler.clipboard_called)


class TestCreateHotkeyDetectorFactory(unittest.TestCase):
    """Tests for create_hotkey_detector factory function."""

    @patch.object(sys, 'platform', 'darwin')
    def test_creates_macos_detector(self):
        """Test factory creates macOS detector on darwin."""
        on_start = MagicMock()
        on_stop = MagicMock()

        # Patch the macOS-specific import
        with patch('handfree.platform.macos.hotkey_detector.Quartz') as mock_quartz:
            from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector
            detector = create_hotkey_detector(on_start, on_stop)
            self.assertIsInstance(detector, MacOSHotkeyDetector)
            self.assertEqual(detector.get_hotkey_description(), "Fn/Globe key")

    @patch.object(sys, 'platform', 'freebsd')
    def test_raises_on_unsupported_platform(self):
        """Test factory raises PlatformNotSupportedError on unsupported platform."""
        with self.assertRaises(PlatformNotSupportedError) as context:
            create_hotkey_detector(lambda: None, lambda: None)

        self.assertIn("not supported", str(context.exception))


class TestCreateOutputHandlerFactory(unittest.TestCase):
    """Tests for create_output_handler factory function."""

    @patch.object(sys, 'platform', 'darwin')
    def test_creates_macos_handler(self):
        """Test factory creates macOS output handler on darwin."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler
        handler = create_output_handler(type_delay=0.05)
        self.assertIsInstance(handler, MacOSOutputHandler)
        self.assertEqual(handler.type_delay, 0.05)

    @patch.object(sys, 'platform', 'freebsd')
    def test_raises_on_unsupported_platform(self):
        """Test factory raises PlatformNotSupportedError on unsupported platform."""
        with self.assertRaises(PlatformNotSupportedError) as context:
            create_output_handler()

        self.assertIn("not supported", str(context.exception))


class TestMacOSHotkeyDetector(unittest.TestCase):
    """Tests for MacOSHotkeyDetector implementation."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz')
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_initialization(self, mock_tap_create, mock_quartz):
        """Test MacOSHotkeyDetector initialization."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        self.assertEqual(detector.on_start, on_start)
        self.assertEqual(detector.on_stop, on_stop)
        self.assertFalse(detector.is_recording)

    @patch('handfree.platform.macos.hotkey_detector.Quartz')
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_hotkey_description(self, mock_tap_create, mock_quartz):
        """Test MacOSHotkeyDetector returns correct hotkey description."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)
        self.assertEqual(detector.get_hotkey_description(), "Fn/Globe key")


class TestMacOSOutputHandler(unittest.TestCase):
    """Tests for MacOSOutputHandler implementation."""

    def test_initialization(self):
        """Test MacOSOutputHandler initialization."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        handler = MacOSOutputHandler(type_delay=0.1)
        self.assertEqual(handler.type_delay, 0.1)

    def test_default_type_delay(self):
        """Test MacOSOutputHandler default type delay."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        handler = MacOSOutputHandler()
        self.assertEqual(handler.type_delay, 0.0)

    @patch('handfree.platform.macos.output_handler.pyperclip')
    def test_copy_to_clipboard(self, mock_pyperclip):
        """Test clipboard copy functionality."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        handler = MacOSOutputHandler()
        handler.copy_to_clipboard("Test text")

        mock_pyperclip.copy.assert_called_once_with("Test text")

    @patch('handfree.platform.macos.output_handler.pyperclip')
    def test_copy_to_clipboard_empty(self, mock_pyperclip):
        """Test clipboard copy with empty string."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        handler = MacOSOutputHandler()
        handler.copy_to_clipboard("")

        mock_pyperclip.copy.assert_not_called()

    @patch('handfree.platform.macos.output_handler.subprocess.run')
    def test_type_text_basic(self, mock_run):
        """Test basic keystroke typing."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        mock_run.return_value = MagicMock(returncode=0)
        handler = MacOSOutputHandler()
        handler.type_text("Hello")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0][0], 'osascript')
        self.assertIn('Hello', call_args[0][0][2])

    @patch('handfree.platform.macos.output_handler.subprocess.run')
    def test_type_text_escapes_quotes(self, mock_run):
        """Test that quotes are properly escaped."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        mock_run.return_value = MagicMock(returncode=0)
        handler = MacOSOutputHandler()
        handler.type_text('Say "hello"')

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        self.assertIn('\\"hello\\"', script)

    @patch('handfree.platform.macos.output_handler.subprocess.run')
    def test_type_text_escapes_backslashes(self, mock_run):
        """Test that backslashes are properly escaped."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        mock_run.return_value = MagicMock(returncode=0)
        handler = MacOSOutputHandler()
        handler.type_text('path\\to\\file')

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        self.assertIn('\\\\', script)

    @patch('handfree.platform.macos.output_handler.subprocess.run')
    @patch('handfree.platform.macos.output_handler.pyperclip')
    def test_type_text_via_paste(self, mock_pyperclip, mock_run):
        """Test paste-based typing."""
        from handfree.platform.macos.output_handler import MacOSOutputHandler

        mock_run.return_value = MagicMock(returncode=0)
        handler = MacOSOutputHandler()
        handler.type_text_via_paste("Test text")

        # Should copy to clipboard
        mock_pyperclip.copy.assert_called_once_with("Test text")
        # Should trigger Cmd+V
        call_args = mock_run.call_args
        script = call_args[0][0][2]
        self.assertIn('keystroke "v"', script)
        self.assertIn('command down', script)


class TestPlatformNotSupportedError(unittest.TestCase):
    """Tests for PlatformNotSupportedError exception."""

    def test_exception_inheritance(self):
        """Test PlatformNotSupportedError inherits from HandFreeError."""
        from handfree.exceptions import HandFreeError, PlatformNotSupportedError

        self.assertTrue(issubclass(PlatformNotSupportedError, HandFreeError))

    def test_exception_message(self):
        """Test exception can be raised with message."""
        from handfree.exceptions import PlatformNotSupportedError

        with self.assertRaises(PlatformNotSupportedError) as context:
            raise PlatformNotSupportedError("Test error message")

        self.assertEqual(str(context.exception), "Test error message")


class TestPlatformConsistency(unittest.TestCase):
    """Tests to ensure platform implementations are consistent."""

    def test_all_platforms_have_required_files(self):
        """Test that all platform modules have required files."""
        import importlib

        platforms = ['macos', 'windows', 'linux']
        required_modules = ['hotkey_detector', 'output_handler']

        for platform in platforms:
            for module in required_modules:
                module_path = f'handfree.platform.{platform}.{module}'
                try:
                    importlib.import_module(module_path)
                except ImportError as e:
                    # On non-matching platforms, some imports might fail
                    # due to platform-specific dependencies
                    if platform == 'macos' and sys.platform != 'darwin':
                        # macOS modules require Quartz which is not available on other platforms
                        pass
                    else:
                        # Windows/Linux modules use pynput which should be available
                        self.fail(f"Failed to import {module_path}: {e}")


class TestWindowsHotkeyDetector(unittest.TestCase):
    """Tests for WindowsHotkeyDetector implementation."""

    @patch('handfree.platform.windows.hotkey_detector.keyboard')
    def test_initialization(self, mock_keyboard):
        """Test WindowsHotkeyDetector initialization."""
        from handfree.platform.windows.hotkey_detector import WindowsHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = WindowsHotkeyDetector(on_start, on_stop)

        self.assertEqual(detector.on_start, on_start)
        self.assertEqual(detector.on_stop, on_stop)
        self.assertFalse(detector.is_recording)

    @patch('handfree.platform.windows.hotkey_detector.keyboard')
    def test_hotkey_description(self, mock_keyboard):
        """Test WindowsHotkeyDetector returns correct hotkey description."""
        from handfree.platform.windows.hotkey_detector import WindowsHotkeyDetector

        detector = WindowsHotkeyDetector(lambda: None, lambda: None)
        self.assertEqual(detector.get_hotkey_description(), "Ctrl+Shift+Space")


class TestLinuxHotkeyDetector(unittest.TestCase):
    """Tests for LinuxHotkeyDetector implementation."""

    @patch('handfree.platform.linux.hotkey_detector.keyboard')
    def test_initialization(self, mock_keyboard):
        """Test LinuxHotkeyDetector initialization."""
        from handfree.platform.linux.hotkey_detector import LinuxHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)

        self.assertEqual(detector.on_start, on_start)
        self.assertEqual(detector.on_stop, on_stop)
        self.assertFalse(detector.is_recording)

    @patch('handfree.platform.linux.hotkey_detector.keyboard')
    def test_hotkey_description(self, mock_keyboard):
        """Test LinuxHotkeyDetector returns correct hotkey description."""
        from handfree.platform.linux.hotkey_detector import LinuxHotkeyDetector

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)
        self.assertEqual(detector.get_hotkey_description(), "Ctrl+Shift+Space")


if __name__ == '__main__':
    unittest.main()
