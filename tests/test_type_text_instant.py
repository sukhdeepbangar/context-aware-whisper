"""
Test suite for type_text_instant() method across all platform handlers.

Tests the clipboard-restore behavior that:
1. Saves current clipboard content
2. Copies text to clipboard
3. Pastes using keyboard shortcut
4. Restores original clipboard content

This ensures the user's clipboard is not polluted with transcribed text.
"""

import subprocess
import unittest
from unittest.mock import MagicMock, patch, call


class TestMacOSTypeTextInstant(unittest.TestCase):
    """Tests for macOS type_text_instant() method."""

    def setUp(self):
        """Set up test fixtures."""
        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        self.handler = MacOSOutputHandler()

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_instant_paste_saves_and_restores_clipboard(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that clipboard is saved and restored after paste."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = "original content"

        self.handler.type_text_instant("new text")

        # Should save clipboard first
        mock_pyperclip.paste.assert_called_once()
        # Should copy new text
        mock_pyperclip.copy.assert_any_call("new text")
        # Should restore original clipboard
        mock_pyperclip.copy.assert_any_call("original content")
        # Verify order: paste (save), copy (new), copy (restore)
        self.assertEqual(mock_pyperclip.copy.call_count, 2)

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_instant_paste_sends_cmd_v(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that Cmd+V is sent to paste."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = ""

        self.handler.type_text_instant("test text")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        script = call_args[0][0][2]
        self.assertIn('keystroke "v"', script)
        self.assertIn('command down', script)

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    def test_instant_paste_empty_string_does_nothing(self, mock_run, mock_pyperclip):
        """Test that empty string doesn't trigger any actions."""
        self.handler.type_text_instant("")

        mock_run.assert_not_called()
        mock_pyperclip.copy.assert_not_called()

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_instant_paste_handles_empty_clipboard(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that empty clipboard is handled gracefully."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.side_effect = Exception("Clipboard empty")

        # Should not raise an error
        self.handler.type_text_instant("new text")

        # Should still copy the new text
        mock_pyperclip.copy.assert_called_with("new text")

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_instant_paste_restores_clipboard_even_on_error(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that clipboard is restored even if paste fails."""
        mock_pyperclip.paste.return_value = "original content"
        mock_run.side_effect = subprocess.CalledProcessError(1, 'osascript', stderr=b"error")

        from context_aware_whisper.exceptions import OutputError
        with self.assertRaises(OutputError):
            self.handler.type_text_instant("new text")

        # Original clipboard should still be restored
        mock_pyperclip.copy.assert_called_with("original content")

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_instant_paste_timeout_raises_error(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that timeout raises OutputError."""
        mock_pyperclip.paste.return_value = ""
        mock_run.side_effect = subprocess.TimeoutExpired('osascript', 10)

        from context_aware_whisper.exceptions import OutputError
        with self.assertRaises(OutputError) as context:
            self.handler.type_text_instant("test")

        self.assertIn("timed out", str(context.exception))

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_instant_paste_waits_for_completion(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that sleep is called to wait for paste completion."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = ""

        self.handler.type_text_instant("test")

        mock_sleep.assert_called_once_with(0.05)


class TestWindowsTypeTextInstant(unittest.TestCase):
    """Tests for Windows type_text_instant() method."""

    @patch('context_aware_whisper.platform.windows.output_handler.Controller')
    def setUp(self, mock_controller):
        """Set up test fixtures."""
        self.mock_keyboard = MagicMock()
        mock_controller.return_value = self.mock_keyboard

        from context_aware_whisper.platform.windows.output_handler import WindowsOutputHandler
        self.handler = WindowsOutputHandler()

    @patch('context_aware_whisper.platform.windows.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.windows.output_handler.time.sleep')
    @patch('context_aware_whisper.platform.windows.output_handler.Controller')
    def test_instant_paste_saves_and_restores_clipboard(self, mock_controller, mock_sleep, mock_pyperclip):
        """Test that clipboard is saved and restored after paste."""
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard
        mock_pyperclip.paste.return_value = "original content"

        from context_aware_whisper.platform.windows.output_handler import WindowsOutputHandler
        handler = WindowsOutputHandler()
        handler.type_text_instant("new text")

        # Should save clipboard first
        mock_pyperclip.paste.assert_called()
        # Should copy new text and restore original
        copy_calls = mock_pyperclip.copy.call_args_list
        self.assertEqual(len(copy_calls), 2)
        self.assertEqual(copy_calls[0][0][0], "new text")
        self.assertEqual(copy_calls[1][0][0], "original content")

    @patch('context_aware_whisper.platform.windows.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.windows.output_handler.time.sleep')
    @patch('context_aware_whisper.platform.windows.output_handler.Controller')
    def test_instant_paste_sends_ctrl_v(self, mock_controller, mock_sleep, mock_pyperclip):
        """Test that Ctrl+V is sent to paste."""
        from pynput.keyboard import Key

        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard
        mock_pyperclip.paste.return_value = ""

        from context_aware_whisper.platform.windows.output_handler import WindowsOutputHandler
        handler = WindowsOutputHandler()
        handler.type_text_instant("test text")

        # Should press Ctrl+V
        mock_keyboard.press.assert_any_call(Key.ctrl)
        mock_keyboard.press.assert_any_call('v')
        mock_keyboard.release.assert_any_call('v')
        mock_keyboard.release.assert_any_call(Key.ctrl)

    @patch('context_aware_whisper.platform.windows.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.windows.output_handler.Controller')
    def test_instant_paste_empty_string_does_nothing(self, mock_controller, mock_pyperclip):
        """Test that empty string doesn't trigger any actions."""
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard

        from context_aware_whisper.platform.windows.output_handler import WindowsOutputHandler
        handler = WindowsOutputHandler()
        handler.type_text_instant("")

        mock_keyboard.press.assert_not_called()
        mock_pyperclip.copy.assert_not_called()


class TestLinuxTypeTextInstant(unittest.TestCase):
    """Tests for Linux type_text_instant() method."""

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_instant_paste_x11_saves_and_restores_clipboard(
        self, mock_sleep, mock_pyperclip, mock_controller, mock_display, mock_tool
    ):
        """Test that clipboard is saved and restored after paste on X11."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard
        mock_pyperclip.paste.return_value = "original content"

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_instant("new text")

        # Should copy new text and restore original
        copy_calls = mock_pyperclip.copy.call_args_list
        self.assertEqual(len(copy_calls), 2)
        self.assertEqual(copy_calls[0][0][0], "new text")
        self.assertEqual(copy_calls[1][0][0], "original content")

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_instant_paste_x11_sends_ctrl_v(
        self, mock_sleep, mock_pyperclip, mock_controller, mock_display, mock_tool
    ):
        """Test that Ctrl+V is sent to paste on X11."""
        from pynput.keyboard import Key

        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard
        mock_pyperclip.paste.return_value = ""

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_instant("test text")

        # Should press Ctrl+V
        mock_keyboard.press.assert_any_call(Key.ctrl)
        mock_keyboard.press.assert_any_call('v')

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_instant_paste_wayland_uses_wtype(
        self, mock_sleep, mock_run, mock_controller, mock_display, mock_tool
    ):
        """Test that wtype is used for paste on Wayland."""
        mock_display.return_value = "wayland"
        mock_tool.side_effect = lambda t: t in ["wtype", "wl-copy", "wl-paste"]
        mock_controller.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0, stdout=b"original")

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_instant("test text")

        # Should have called wl-copy and wtype
        calls = mock_run.call_args_list
        # wl-paste for getting original, wl-copy for new text, wtype for paste, wl-copy for restore
        self.assertTrue(any("wtype" in str(c) for c in calls))

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    def test_instant_paste_empty_string_does_nothing(
        self, mock_pyperclip, mock_controller, mock_display, mock_tool
    ):
        """Test that empty string doesn't trigger any actions."""
        mock_display.return_value = "x11"
        mock_tool.return_value = False
        mock_keyboard = MagicMock()
        mock_controller.return_value = mock_keyboard

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_instant("")

        mock_keyboard.press.assert_not_called()

    @patch("context_aware_whisper.platform.linux.output_handler.is_tool_available")
    @patch("context_aware_whisper.platform.linux.output_handler.get_display_server")
    @patch("context_aware_whisper.platform.linux.output_handler.Controller")
    @patch("context_aware_whisper.platform.linux.output_handler.subprocess.run")
    @patch("context_aware_whisper.platform.linux.output_handler.pyperclip")
    @patch("context_aware_whisper.platform.linux.output_handler.time.sleep")
    def test_instant_paste_x11_xdotool_fallback(
        self, mock_sleep, mock_pyperclip, mock_run, mock_controller, mock_display, mock_tool
    ):
        """Test that xdotool fallback works on X11."""
        mock_display.return_value = "x11"
        mock_tool.side_effect = lambda t: t == "xdotool"
        mock_keyboard = MagicMock()
        mock_keyboard.press.side_effect = Exception("pynput error")
        mock_controller.return_value = mock_keyboard
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = "original"

        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        handler = LinuxOutputHandler()
        handler.type_text_instant("test text")

        # Should have called xdotool for paste
        xdotool_calls = [c for c in mock_run.call_args_list if "xdotool" in str(c)]
        self.assertTrue(len(xdotool_calls) > 0)


class TestBaseOutputMethodUsesInstant(unittest.TestCase):
    """Test that the base output() method now uses type_text_instant()."""

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_output_method_uses_instant_paste(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that output() uses type_text_instant() internally."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = "original"

        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        handler = MacOSOutputHandler()
        handler.output("test text")

        # Should have saved and restored clipboard (instant paste behavior)
        copy_calls = mock_pyperclip.copy.call_args_list
        self.assertEqual(len(copy_calls), 2)
        self.assertEqual(copy_calls[0][0][0], "test text")
        self.assertEqual(copy_calls[1][0][0], "original")

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_output_method_empty_string_does_nothing(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that output() with empty string doesn't trigger actions."""
        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        handler = MacOSOutputHandler()
        handler.output("")

        mock_run.assert_not_called()
        mock_pyperclip.copy.assert_not_called()

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_output_method_use_paste_param_ignored(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that use_paste parameter is now ignored (always uses instant paste)."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = ""

        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        handler = MacOSOutputHandler()

        # Both with and without use_paste should behave the same
        handler.output("test1", use_paste=False)
        handler.output("test2", use_paste=True)

        # Both calls should use instant paste (2 paste attempts + 4 copy calls total)
        self.assertEqual(mock_run.call_count, 2)


class TestClipboardRestoreEdgeCases(unittest.TestCase):
    """Test edge cases for clipboard restoration."""

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_none_clipboard_not_restored(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that None clipboard content doesn't attempt restore."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.side_effect = Exception("Clipboard empty")

        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        handler = MacOSOutputHandler()
        handler.type_text_instant("new text")

        # Should only copy the new text, not try to restore
        self.assertEqual(mock_pyperclip.copy.call_count, 1)
        mock_pyperclip.copy.assert_called_with("new text")

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_restore_failure_silently_ignored(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that clipboard restore failure doesn't raise exception."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = "original"

        # Make the second copy (restore) fail
        mock_pyperclip.copy.side_effect = [None, Exception("Restore failed")]

        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        handler = MacOSOutputHandler()

        # Should not raise, even though restore failed
        handler.type_text_instant("new text")

    @patch('context_aware_whisper.platform.macos.output_handler.pyperclip')
    @patch('context_aware_whisper.platform.macos.output_handler.subprocess.run')
    @patch('context_aware_whisper.platform.macos.output_handler.time.sleep')
    def test_special_characters_in_text(self, mock_sleep, mock_run, mock_pyperclip):
        """Test that special characters are handled correctly."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_pyperclip.paste.return_value = "original"

        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        handler = MacOSOutputHandler()

        # Text with special characters
        special_text = 'Hello "World" with \'quotes\' and\nnewlines'
        handler.type_text_instant(special_text)

        # Check that the special text was copied to clipboard
        mock_pyperclip.copy.assert_any_call(special_text)


if __name__ == '__main__':
    unittest.main()
