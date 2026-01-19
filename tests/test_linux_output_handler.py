"""
Test suite for Linux Output Handler with xdotool/wtype fallback.

Tests cover:
- Display server detection (X11 vs Wayland)
- Tool availability detection
- Fallback logic for typing and clipboard operations
- Error handling when tools are unavailable
"""

import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch, call

import pytest

from context_aware_whisper.exceptions import OutputError


class TestDisplayServerDetection(unittest.TestCase):
    """Tests for display server detection functions."""

    def test_is_wayland_session_true(self):
        """Test is_wayland_session returns True when XDG_SESSION_TYPE is wayland."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            from context_aware_whisper.platform.linux.output_handler import is_wayland_session
            self.assertTrue(is_wayland_session())

    def test_is_wayland_session_false_x11(self):
        """Test is_wayland_session returns False when XDG_SESSION_TYPE is x11."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=True):
            from context_aware_whisper.platform.linux.output_handler import is_wayland_session
            self.assertFalse(is_wayland_session())

    def test_is_wayland_session_false_unset(self):
        """Test is_wayland_session returns False when XDG_SESSION_TYPE is unset."""
        env = os.environ.copy()
        env.pop("XDG_SESSION_TYPE", None)
        with patch.dict(os.environ, env, clear=True):
            from context_aware_whisper.platform.linux.output_handler import is_wayland_session
            self.assertFalse(is_wayland_session())

    def test_is_wayland_session_case_insensitive(self):
        """Test is_wayland_session handles case insensitively."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "WAYLAND"}):
            from context_aware_whisper.platform.linux.output_handler import is_wayland_session
            self.assertTrue(is_wayland_session())

    def test_get_display_server_wayland_from_session_type(self):
        """Test get_display_server returns wayland from XDG_SESSION_TYPE."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=True):
            from context_aware_whisper.platform.linux.output_handler import get_display_server
            self.assertEqual(get_display_server(), "wayland")

    def test_get_display_server_x11_from_session_type(self):
        """Test get_display_server returns x11 from XDG_SESSION_TYPE."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=True):
            from context_aware_whisper.platform.linux.output_handler import get_display_server
            self.assertEqual(get_display_server(), "x11")

    def test_get_display_server_wayland_from_wayland_display(self):
        """Test get_display_server detects Wayland from WAYLAND_DISPLAY."""
        env = {"WAYLAND_DISPLAY": "wayland-0"}
        with patch.dict(os.environ, env, clear=True):
            from context_aware_whisper.platform.linux.output_handler import get_display_server
            self.assertEqual(get_display_server(), "wayland")

    def test_get_display_server_x11_from_display(self):
        """Test get_display_server detects X11 from DISPLAY."""
        env = {"DISPLAY": ":0"}
        with patch.dict(os.environ, env, clear=True):
            from context_aware_whisper.platform.linux.output_handler import get_display_server
            self.assertEqual(get_display_server(), "x11")

    def test_get_display_server_unknown(self):
        """Test get_display_server returns unknown when no display vars set."""
        with patch.dict(os.environ, {}, clear=True):
            from context_aware_whisper.platform.linux.output_handler import get_display_server
            self.assertEqual(get_display_server(), "unknown")

    def test_get_display_server_session_type_precedence(self):
        """Test XDG_SESSION_TYPE takes precedence over WAYLAND_DISPLAY."""
        env = {"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": "wayland-0"}
        with patch.dict(os.environ, env, clear=True):
            from context_aware_whisper.platform.linux.output_handler import get_display_server
            self.assertEqual(get_display_server(), "x11")


class TestToolAvailability(unittest.TestCase):
    """Tests for tool availability detection."""

    @patch("shutil.which")
    def test_is_tool_available_found(self, mock_which):
        """Test is_tool_available returns True when tool exists."""
        mock_which.return_value = "/usr/bin/xdotool"
        from context_aware_whisper.platform.linux.output_handler import is_tool_available
        self.assertTrue(is_tool_available("xdotool"))
        mock_which.assert_called_once_with("xdotool")

    @patch("shutil.which")
    def test_is_tool_available_not_found(self, mock_which):
        """Test is_tool_available returns False when tool doesn't exist."""
        mock_which.return_value = None
        from context_aware_whisper.platform.linux.output_handler import is_tool_available
        self.assertFalse(is_tool_available("nonexistent"))
        mock_which.assert_called_once_with("nonexistent")


class TestLinuxOutputHandlerInitialization(unittest.TestCase):
    """Tests for LinuxOutputHandler initialization."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_initialization_x11(self, mock_controller, mock_display, mock_tool):
        """Test initialization on X11."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t in ["xdotool"]
        mock_controller.return_value = MagicMock()

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler(type_delay=0.05)

        self.assertEqual(handler.type_delay, 0.05)
        self.assertEqual(handler._display_server, "x11")
        self.assertTrue(handler._has_xdotool)
        self.assertFalse(handler._has_wtype)
        self.assertFalse(handler._has_wl_copy)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_initialization_wayland(self, mock_controller, mock_display, mock_tool):
        """Test initialization on Wayland."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t in ["wtype", "wl-copy"]
        mock_controller.return_value = MagicMock()

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        self.assertEqual(handler._display_server, "wayland")
        self.assertFalse(handler._has_xdotool)
        self.assertTrue(handler._has_wtype)
        self.assertTrue(handler._has_wl_copy)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_initialization_pynput_failure(self, mock_controller, mock_display, mock_tool):
        """Test initialization handles pynput failure gracefully."""
        mock_display.return_value = "x11"
        mock_tool.return_value = True
        mock_controller.side_effect = Exception("pynput error")

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        self.assertIsNone(handler._keyboard)


class TestLinuxOutputHandlerClipboard(unittest.TestCase):
    """Tests for clipboard operations."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    def test_copy_to_clipboard_x11(self, mock_pyperclip, mock_controller, mock_display, mock_tool):
        """Test clipboard copy on X11 uses pyperclip."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_controller.return_value = MagicMock()

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.copy_to_clipboard("test text")

        mock_pyperclip.copy.assert_called_once_with("test text")

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_copy_to_clipboard_wayland_wl_copy(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test clipboard copy on Wayland uses wl-copy."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t == "wl-copy"
        mock_controller.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.copy_to_clipboard("test text")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0], ["wl-copy", "--"])
        self.assertEqual(call_args[1]["input"], b"test text")

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    def test_copy_to_clipboard_wayland_fallback(self, mock_pyperclip, mock_run, mock_controller, mock_display, mock_tool):
        """Test clipboard copy on Wayland falls back to pyperclip if wl-copy fails."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t == "wl-copy"
        mock_controller.return_value = MagicMock()
        mock_run.side_effect = Exception("wl-copy error")

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.copy_to_clipboard("test text")

        mock_pyperclip.copy.assert_called_once_with("test text")

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_copy_to_clipboard_empty_string(self, mock_controller, mock_display, mock_tool):
        """Test clipboard copy with empty string does nothing."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_controller.return_value = MagicMock()

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        with patch("context_aware_whisper.platform.linux.output_handler.pyperclip") as mock_pyperclip:
            handler = LinuxOutputHandler()
            handler.copy_to_clipboard("")
            mock_pyperclip.copy.assert_not_called()


class TestLinuxOutputHandlerTypeText(unittest.TestCase):
    """Tests for type_text operations."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_type_text_x11_pynput(self, mock_controller, mock_display, mock_tool):
        """Test type_text on X11 uses pynput."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text("Hi")

        # Should call type for each character
        self.assertEqual(mock_keyboard.type.call_count, 2)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_type_text_x11_xdotool_fallback(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test type_text on X11 falls back to xdotool when pynput fails."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t == "xdotool"
        mock_keyboard = MagicMock()
        mock_keyboard.type.side_effect = Exception("pynput error")
        mock_controller.return_value = mock_keyboard
        mock_run.return_value = MagicMock(returncode=0)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text("Hello")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "xdotool")
        self.assertIn("Hello", call_args)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_type_text_x11_xdotool_with_delay(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test type_text on X11 xdotool includes delay parameter."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t == "xdotool"
        mock_controller.side_effect = Exception("pynput unavailable")
        mock_run.return_value = MagicMock(returncode=0)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler(type_delay=0.1)  # 100ms delay
        handler.type_text("Hello")

        call_args = mock_run.call_args[0][0]
        self.assertIn("--delay", call_args)
        self.assertIn("100", call_args)  # 0.1 seconds = 100 ms

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_type_text_wayland_wtype(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test type_text on Wayland uses wtype."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t == "wtype"
        mock_controller.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text("Hello")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "wtype")
        self.assertIn("Hello", call_args)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_type_text_wayland_no_wtype_error(self, mock_controller, mock_display, mock_tool):
        """Test type_text on Wayland raises error when wtype not available."""
        mock_display.return_value = "wayland"
        mock_tool.return_value = False
        mock_controller.return_value = MagicMock()

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler.type_text("Hello")

        self.assertIn("wtype", str(context.exception))
        self.assertIn("not installed", str(context.exception))

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_type_text_x11_no_tools_error(self, mock_controller, mock_display, mock_tool):
        """Test type_text on X11 raises error when no tools available."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_controller.side_effect = Exception("pynput unavailable")

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler.type_text("Hello")

        self.assertIn("xdotool", str(context.exception))
        self.assertIn("not found", str(context.exception))

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_type_text_empty_string(self, mock_controller, mock_display, mock_tool):
        """Test type_text with empty string does nothing."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text("")

        mock_keyboard.type.assert_not_called()


class TestLinuxOutputHandlerTypeTextViaPaste(unittest.TestCase):
    """Tests for type_text_via_paste operations."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_paste_x11_pynput(self, mock_sleep, mock_pyperclip, mock_controller, mock_display, mock_tool):
        """Test paste on X11 uses pynput."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_via_paste("test")

        mock_pyperclip.copy.assert_called_once_with("test")
        # Should simulate Ctrl+V
        mock_keyboard.press.assert_called()
        mock_keyboard.release.assert_called()

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_paste_x11_xdotool_fallback(self, mock_sleep, mock_run, mock_pyperclip, mock_controller, mock_display, mock_tool):
        """Test paste on X11 falls back to xdotool."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t == "xdotool"
        mock_keyboard = MagicMock()
        mock_keyboard.press.side_effect = Exception("pynput error")
        mock_controller.return_value = mock_keyboard
        mock_run.return_value = MagicMock(returncode=0)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_via_paste("test")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "xdotool")
        self.assertIn("ctrl+v", call_args)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_paste_wayland_wtype(self, mock_sleep, mock_run, mock_controller, mock_display, mock_tool):
        """Test paste on Wayland uses wtype."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t in ["wtype", "wl-copy"]
        mock_controller.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_via_paste("test")

        # Should have called wl-copy for clipboard and wtype for paste
        self.assertEqual(mock_run.call_count, 2)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    def test_paste_empty_string(self, mock_controller, mock_display, mock_tool):
        """Test paste with empty string does nothing."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_via_paste("")

        mock_keyboard.press.assert_not_called()


class TestLinuxOutputHandlerTimeoutErrors(unittest.TestCase):
    """Tests for timeout error handling."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_xdotool_timeout(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test xdotool timeout raises OutputError."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t == "xdotool"
        mock_controller.side_effect = Exception("pynput unavailable")
        mock_run.side_effect = subprocess.TimeoutExpired("xdotool", 30)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler.type_text("Hello")

        self.assertIn("timed out", str(context.exception))

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_wtype_timeout(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test wtype timeout raises OutputError."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t == "wtype"
        mock_controller.return_value = MagicMock()
        mock_run.side_effect = subprocess.TimeoutExpired("wtype", 30)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler.type_text("Hello")

        self.assertIn("timed out", str(context.exception))

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_wl_copy_timeout(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test wl-copy timeout raises OutputError."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t == "wl-copy"
        mock_controller.return_value = MagicMock()
        mock_run.side_effect = subprocess.TimeoutExpired("wl-copy", 5)

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler._copy_with_wl_copy("test")

        self.assertIn("timed out", str(context.exception))


class TestLinuxOutputHandlerCommandFailures(unittest.TestCase):
    """Tests for command failure handling."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_xdotool_nonzero_exit(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test xdotool non-zero exit code raises OutputError."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t == "xdotool"
        mock_controller.side_effect = Exception("pynput unavailable")
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error message")

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler.type_text("Hello")

        self.assertIn("xdotool failed", str(context.exception))

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    def test_wtype_nonzero_exit(self, mock_run, mock_controller, mock_display, mock_tool):
        """Test wtype non-zero exit code raises OutputError."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t == "wtype"
        mock_controller.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error message")

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        with self.assertRaises(OutputError) as context:
            handler.type_text("Hello")

        self.assertIn("wtype failed", str(context.exception))


class TestLinuxOutputHandlerIntegration(unittest.TestCase):
    """Integration tests for LinuxOutputHandler."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_output_method_uses_instant_paste(self, mock_sleep, mock_pyperclip, mock_controller, mock_display, mock_tool):
        """Test output() method uses type_text_instant (new behavior)."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard
        mock_pyperclip.paste.return_value = "original"

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.output("Hello", use_paste=False)

        # New behavior: type_text_instant copies text, pastes, then restores clipboard
        # So copy is called twice: once for "Hello", once for "original" (restore)
        self.assertEqual(mock_pyperclip.copy.call_count, 2)
        copy_calls = mock_pyperclip.copy.call_args_list
        self.assertEqual(copy_calls[0][0][0], "Hello")
        self.assertEqual(copy_calls[1][0][0], "original")
        # Should use Ctrl+V for pasting
        self.assertTrue(mock_keyboard.press.called)

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_output_method_ignores_use_paste_flag(self, mock_sleep, mock_pyperclip, mock_controller, mock_display, mock_tool):
        """Test output() method ignores use_paste flag (always uses instant)."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard
        mock_pyperclip.paste.return_value = "original"

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()

        # Both calls should behave the same (use instant paste)
        handler.output("Test1", use_paste=False)
        call_count_1 = mock_pyperclip.copy.call_count
        mock_pyperclip.reset_mock()

        handler.output("Test2", use_paste=True)
        call_count_2 = mock_pyperclip.copy.call_count

        # Both should call copy twice (text + restore)
        self.assertEqual(call_count_1, 2)
        self.assertEqual(call_count_2, 2)


if __name__ == "__main__":
    unittest.main()
