"""
Test suite for Output Handler Module.

Includes unit tests and property-based tests for the OutputHandler class.
"""

import subprocess
import unittest
from unittest.mock import patch, MagicMock

import pytest
import pyperclip

from context_aware_whisper.output_handler import OutputHandler, get_clipboard_content
from context_aware_whisper.exceptions import OutputError


class TestOutputHandlerClipboard(unittest.TestCase):
    """Tests for clipboard functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OutputHandler()
        # Save original clipboard content to restore after tests
        try:
            self.original_clipboard = pyperclip.paste()
        except Exception:
            self.original_clipboard = ""

    def tearDown(self):
        """Restore original clipboard content."""
        try:
            pyperclip.copy(self.original_clipboard)
        except Exception:
            pass

    def test_copy_to_clipboard_basic(self):
        """Test basic clipboard copy operation."""
        test_text = "Hello, World!"
        self.handler.copy_to_clipboard(test_text)
        result = pyperclip.paste()
        self.assertEqual(result, test_text)

    def test_copy_to_clipboard_empty_string(self):
        """Test that empty string is handled without error."""
        self.handler.copy_to_clipboard("")
        # Should not raise an error

    def test_copy_to_clipboard_unicode(self):
        """Test copying unicode characters."""
        test_text = "Hello"
        self.handler.copy_to_clipboard(test_text)
        result = pyperclip.paste()
        self.assertEqual(result, test_text)

    def test_copy_to_clipboard_special_chars(self):
        """Test copying special characters."""
        test_text = 'Hello, "World"! It\'s a test with $pecial chars.'
        self.handler.copy_to_clipboard(test_text)
        result = pyperclip.paste()
        self.assertEqual(result, test_text)

    def test_copy_to_clipboard_newlines(self):
        """Test copying text with newlines."""
        test_text = "Line 1\nLine 2\nLine 3"
        self.handler.copy_to_clipboard(test_text)
        result = pyperclip.paste()
        self.assertEqual(result, test_text)

    def test_copy_to_clipboard_long_text(self):
        """Test copying long text."""
        test_text = "A" * 10000
        self.handler.copy_to_clipboard(test_text)
        result = pyperclip.paste()
        self.assertEqual(result, test_text)


class TestOutputHandlerTypeText(unittest.TestCase):
    """Tests for type_text functionality using mocks."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OutputHandler()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_basic(self, mock_run):
        """Test basic keystroke typing."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text("Hello")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0][0], 'osascript')
        self.assertIn('Hello', call_args[0][0][2])

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_empty_string(self, mock_run):
        """Test that empty string doesn't call subprocess."""
        self.handler.type_text("")
        mock_run.assert_not_called()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_escapes_quotes(self, mock_run):
        """Test that quotes are properly escaped."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text('Say "hello"')

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        # Check that quotes are escaped with backslash
        self.assertIn('\\"hello\\"', script)

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_escapes_backslashes(self, mock_run):
        """Test that backslashes are properly escaped."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text('path\\to\\file')

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        # Check that backslashes are escaped
        self.assertIn('\\\\', script)

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_handles_subprocess_error(self, mock_run):
        """Test error handling when subprocess fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'osascript', stderr=b"Permission denied"
        )

        with self.assertRaises(OutputError) as context:
            self.handler.type_text("Hello")

        self.assertIn("Failed to type text", str(context.exception))

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_handles_timeout(self, mock_run):
        """Test error handling on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('osascript', 10)

        with self.assertRaises(OutputError) as context:
            self.handler.type_text("Hello")

        self.assertIn("timed out", str(context.exception))

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_handles_missing_osascript(self, mock_run):
        """Test error handling when osascript not found."""
        mock_run.side_effect = FileNotFoundError()

        with self.assertRaises(OutputError) as context:
            self.handler.type_text("Hello")

        self.assertIn("osascript not found", str(context.exception))


class TestOutputHandlerOutput(unittest.TestCase):
    """Tests for the combined output method."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OutputHandler()
        try:
            self.original_clipboard = pyperclip.paste()
        except Exception:
            self.original_clipboard = ""

    def tearDown(self):
        """Restore original clipboard content."""
        try:
            pyperclip.copy(self.original_clipboard)
        except Exception:
            pass

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_output_copies_to_clipboard_and_types(self, mock_run):
        """Test that output copies to clipboard and types."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.output("Hello, World!")

        # Check clipboard
        self.assertEqual(pyperclip.paste(), "Hello, World!")
        # Check subprocess was called for typing
        mock_run.assert_called_once()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_output_empty_string(self, mock_run):
        """Test that empty string doesn't trigger actions."""
        self.handler.output("")
        mock_run.assert_not_called()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_output_use_paste_mode(self, mock_run):
        """Test paste mode uses Cmd+V."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.output("Hello", use_paste=True)

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        self.assertIn('keystroke "v"', script)
        self.assertIn('command down', script)


class TestOutputHandlerViaPaste(unittest.TestCase):
    """Tests for the paste-based typing method."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OutputHandler()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_via_paste_empty(self, mock_run):
        """Test empty string doesn't trigger paste."""
        self.handler.type_text_via_paste("")
        mock_run.assert_not_called()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_type_text_via_paste_copies_and_pastes(self, mock_run):
        """Test that paste method copies to clipboard and pastes."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text_via_paste("Test text")

        # Check that Cmd+V was triggered
        call_args = mock_run.call_args
        script = call_args[0][0][2]
        self.assertIn('keystroke "v"', script)
        self.assertIn('command down', script)


class TestGetClipboardContent(unittest.TestCase):
    """Tests for the get_clipboard_content helper function."""

    def setUp(self):
        """Save original clipboard."""
        try:
            self.original_clipboard = pyperclip.paste()
        except Exception:
            self.original_clipboard = ""

    def tearDown(self):
        """Restore original clipboard."""
        try:
            pyperclip.copy(self.original_clipboard)
        except Exception:
            pass

    def test_get_clipboard_content_returns_text(self):
        """Test getting clipboard content."""
        test_text = "Test clipboard content"
        pyperclip.copy(test_text)
        result = get_clipboard_content()
        self.assertEqual(result, test_text)


class TestOutputHandlerInit(unittest.TestCase):
    """Tests for OutputHandler initialization."""

    def test_default_type_delay(self):
        """Test default type delay is 0."""
        handler = OutputHandler()
        self.assertEqual(handler.type_delay, 0.0)

    def test_custom_type_delay(self):
        """Test custom type delay."""
        handler = OutputHandler(type_delay=0.05)
        self.assertEqual(handler.type_delay, 0.05)


class TestOutputHandlerEscaping(unittest.TestCase):
    """Tests for proper escaping of special characters."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OutputHandler()

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_escape_single_quotes(self, mock_run):
        """Test single quotes in text."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text("It's working")

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        # Single quotes don't need escaping in double-quoted AppleScript strings
        self.assertIn("It's working", script)

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_escape_mixed_quotes(self, mock_run):
        """Test mixed quote types."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text('He said "it\'s fine"')

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        # Double quotes should be escaped
        self.assertIn('\\"it\'s fine\\"', script)

    @patch('context_aware_whisper.output_handler.subprocess.run')
    def test_escape_backslash_and_quote(self, mock_run):
        """Test backslash followed by quote."""
        mock_run.return_value = MagicMock(returncode=0)

        self.handler.type_text('path\\"file')

        call_args = mock_run.call_args
        script = call_args[0][0][2]
        # Should have escaped backslash and escaped quote
        self.assertIn('\\\\', script)


class TestOutputHandlerPropertyBased(unittest.TestCase):
    """Property-based tests for OutputHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OutputHandler()
        try:
            self.original_clipboard = pyperclip.paste()
        except Exception:
            self.original_clipboard = ""

    def tearDown(self):
        """Restore original clipboard."""
        try:
            pyperclip.copy(self.original_clipboard)
        except Exception:
            pass

    def test_clipboard_preserves_ascii(self):
        """Test clipboard preserves various ASCII strings."""
        test_cases = [
            "Hello World",
            "12345",
            "!@#$%^&*()",
            "Mixed 123 !@# Text",
            "a" * 100,
            "Tab\there",
        ]
        for text in test_cases:
            with self.subTest(text=text[:20]):
                self.handler.copy_to_clipboard(text)
                result = pyperclip.paste()
                self.assertEqual(result, text)

    def test_clipboard_preserves_unicode(self):
        """Test clipboard preserves unicode strings."""
        test_cases = [
            "cafe",
            "Hello",
            "Chinese",
            "Arabic",
            "Test",
        ]
        for text in test_cases:
            with self.subTest(text=text):
                self.handler.copy_to_clipboard(text)
                result = pyperclip.paste()
                self.assertEqual(result, text)


if __name__ == '__main__':
    unittest.main()
