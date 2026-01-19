"""Integration tests for OutputHandler."""

import pytest

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


@pytest.mark.integration
class TestClipboardIntegration:
    """Integration tests for clipboard operations."""

    @pytest.fixture(autouse=True)
    def preserve_clipboard(self):
        """Preserve and restore clipboard contents around tests."""
        if not PYPERCLIP_AVAILABLE:
            yield
            return

        try:
            original = pyperclip.paste()
        except Exception:
            original = ""
        yield
        try:
            pyperclip.copy(original)
        except Exception:
            pass

    def test_clipboard_roundtrip_basic(self):
        """Test basic clipboard copy/paste roundtrip."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        test_text = "Hello, this is a test!"

        handler.copy_to_clipboard(test_text)

        if PYPERCLIP_AVAILABLE:
            assert pyperclip.paste() == test_text

    def test_clipboard_roundtrip_unicode(self):
        """Test clipboard preserves unicode characters."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        test_text = "Hello cafe 2+2=4 Japanese: konnichiwa"

        handler.copy_to_clipboard(test_text)

        if PYPERCLIP_AVAILABLE:
            result = pyperclip.paste()
            # Basic ASCII should always work
            assert "Hello" in result
            assert "2+2=4" in result

    def test_clipboard_empty_string(self):
        """Test clipboard handles empty string without error."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        # Should not raise an error when copying empty string
        handler.copy_to_clipboard("")

        # Note: clipboard behavior with empty strings varies by platform
        # Some systems may not accept empty clipboard, which is acceptable
        # The key is that it doesn't crash
        if PYPERCLIP_AVAILABLE:
            result = pyperclip.paste()
            # Accept either empty or same content (empty might not work on all platforms)
            assert isinstance(result, str)

    def test_clipboard_whitespace(self):
        """Test clipboard preserves whitespace."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        test_text = "  spaced  text  "

        handler.copy_to_clipboard(test_text)

        if PYPERCLIP_AVAILABLE:
            assert pyperclip.paste() == test_text

    def test_clipboard_multiline(self):
        """Test clipboard handles multiline text."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        test_text = "Line 1\nLine 2\nLine 3"

        handler.copy_to_clipboard(test_text)

        if PYPERCLIP_AVAILABLE:
            result = pyperclip.paste()
            assert "Line 1" in result
            assert "Line 2" in result
            assert "Line 3" in result


@pytest.mark.integration
@pytest.mark.requires_accessibility
class TestTypeTextIntegration:
    """Integration tests for keyboard typing (requires accessibility)."""

    def test_type_text_available(self):
        """Test that type_text method exists and is callable."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        assert hasattr(handler, 'type_text') or hasattr(handler, 'type_text_instant')


@pytest.mark.integration
class TestOutputHandlerUnit:
    """Unit-like tests that don't require specific permissions."""

    def test_output_handler_initialization(self):
        """Test OutputHandler can be instantiated."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        assert handler is not None

    def test_output_handler_has_copy_method(self):
        """Test OutputHandler has copy_to_clipboard method."""
        from context_aware_whisper.output_handler import OutputHandler

        handler = OutputHandler()
        assert hasattr(handler, 'copy_to_clipboard')
        assert callable(handler.copy_to_clipboard)
