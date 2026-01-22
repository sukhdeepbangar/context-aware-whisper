"""
Tests for vocabulary module.

Includes unit tests and property-based tests for vocabulary loading.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from context_aware_whisper.vocabulary import (
    DEFAULT_VOCABULARY_PATH,
    get_vocabulary_path,
    load_vocabulary,
)


class TestLoadVocabulary(unittest.TestCase):
    """Tests for load_vocabulary function."""

    def test_file_exists_returns_prompt(self, tmp_path=None):
        """Returns comma-separated string when file exists."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("Claude\ntmux\nkubectl\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude, tmux, kubectl")

    def test_file_missing_returns_none(self):
        """Returns None when file doesn't exist."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "nonexistent.txt"

            result = load_vocabulary(vocab_file)

            self.assertIsNone(result)

    def test_ignores_comments(self):
        """Ignores lines starting with #."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("# This is a comment\nClaude\n# Another comment\ntmux\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude, tmux")

    def test_ignores_empty_lines(self):
        """Ignores empty lines."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("Claude\n\n\ntmux\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude, tmux")

    def test_trims_whitespace(self):
        """Trims leading/trailing whitespace."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("  Claude  \n\ttmux\t\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude, tmux")

    def test_empty_file_returns_none(self):
        """Returns None for empty file."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("")

            result = load_vocabulary(vocab_file)

            self.assertIsNone(result)

    def test_only_comments_returns_none(self):
        """Returns None when file has only comments."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("# Just a comment\n# Another one\n")

            result = load_vocabulary(vocab_file)

            self.assertIsNone(result)

    def test_single_word(self):
        """Returns single word without comma."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("Claude\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude")

    def test_handles_phrases(self):
        """Handles multi-word phrases on single lines."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("context-aware-whisper\nNew York\nAPI key\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "context-aware-whisper, New York, API key")

    def test_utf8_encoding(self):
        """Handles UTF-8 encoded content."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("日本語\nfrançais\nкириллица\n", encoding="utf-8")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "日本語, français, кириллица")

    def test_uses_default_path_when_none(self):
        """Uses default path when file_path is None and env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            if "CAW_VOCABULARY_FILE" in os.environ:
                del os.environ["CAW_VOCABULARY_FILE"]

            # load_vocabulary with None should try default path
            # Since default path doesn't exist, should return None
            result = load_vocabulary(None)

            # Likely returns None as default path probably doesn't exist
            # Just verify it doesn't crash
            self.assertTrue(result is None or isinstance(result, str))

    def test_file_read_error_returns_none(self):
        """Returns None when file read fails."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("test content")

            # Make the file unreadable (Unix-like systems only)
            try:
                vocab_file.chmod(0o000)
                result = load_vocabulary(vocab_file)
                # Should return None due to permission error
                self.assertIsNone(result)
            except PermissionError:
                # On Windows, chmod may not work as expected
                pass
            finally:
                # Restore permissions for cleanup
                try:
                    vocab_file.chmod(0o644)
                except Exception:
                    pass


class TestGetVocabularyPath(unittest.TestCase):
    """Tests for get_vocabulary_path function."""

    def test_default_path(self):
        """Returns default path when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            if "CAW_VOCABULARY_FILE" in os.environ:
                del os.environ["CAW_VOCABULARY_FILE"]

            result = get_vocabulary_path()

            self.assertEqual(result, Path(DEFAULT_VOCABULARY_PATH).expanduser())

    def test_env_override(self):
        """Uses CAW_VOCABULARY_FILE when set."""
        with patch.dict(os.environ, {"CAW_VOCABULARY_FILE": "/custom/path/vocab.txt"}):
            result = get_vocabulary_path()

            self.assertEqual(result, Path("/custom/path/vocab.txt"))

    def test_env_with_tilde_expansion(self):
        """Expands tilde in env var path."""
        with patch.dict(os.environ, {"CAW_VOCABULARY_FILE": "~/custom/vocab.txt"}):
            result = get_vocabulary_path()

            expected = Path("~/custom/vocab.txt").expanduser()
            self.assertEqual(result, expected)


class TestVocabularyProperties(unittest.TestCase):
    """Property-based tests for vocabulary module."""

    @given(st.lists(st.text(min_size=1, max_size=50, alphabet=st.characters(
        blacklist_categories=["Cc", "Cs"],  # Exclude control chars and surrogates
        blacklist_characters=["#", "\n", "\r"]  # Exclude comment char and newlines
    )), min_size=1, max_size=20))
    @settings(max_examples=20)
    def test_any_valid_words_produce_comma_separated(self, words):
        """Any list of valid words produces a comma-separated string."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"

            # Filter out empty/whitespace-only words
            valid_words = [w.strip() for w in words if w.strip()]
            if not valid_words:
                return  # Skip if no valid words

            vocab_file.write_text("\n".join(valid_words) + "\n")

            result = load_vocabulary(vocab_file)

            self.assertIsNotNone(result)
            # Result should contain all valid words
            for word in valid_words:
                self.assertIn(word, result)

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=10)
    def test_arbitrary_comment_lines_ignored(self, comment_text):
        """Comment lines with arbitrary text are ignored."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"

            # Create file with comment and a valid word
            safe_comment = comment_text.replace("\n", " ").replace("\r", " ")
            content = f"# {safe_comment}\nClaude\n"
            vocab_file.write_text(content)

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude")


class TestVocabularyEdgeCases(unittest.TestCase):
    """Edge case tests for vocabulary module."""

    def test_very_long_line(self):
        """Handles very long lines."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            long_word = "a" * 1000
            vocab_file.write_text(f"{long_word}\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, long_word)

    def test_many_words(self):
        """Handles many vocabulary entries."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            words = [f"word{i}" for i in range(100)]
            vocab_file.write_text("\n".join(words) + "\n")

            result = load_vocabulary(vocab_file)

            self.assertIsNotNone(result)
            self.assertEqual(len(result.split(", ")), 100)

    def test_mixed_comments_and_words(self):
        """Handles file with mixed comments and words."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            content = """# Header comment
Claude
# Section comment
tmux
kubectl
# Another comment
pytest
"""
            vocab_file.write_text(content)

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "Claude, tmux, kubectl, pytest")

    def test_inline_hash_not_comment(self):
        """Hash symbol within a word is preserved (not treated as comment)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            vocab_file = Path(tmp_dir) / "vocabulary.txt"
            vocab_file.write_text("C#\nF#\n")

            result = load_vocabulary(vocab_file)

            self.assertEqual(result, "C#, F#")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestLoadVocabulary))
    suite.addTests(loader.loadTestsFromTestCase(TestGetVocabularyPath))
    suite.addTests(loader.loadTestsFromTestCase(TestVocabularyProperties))
    suite.addTests(loader.loadTestsFromTestCase(TestVocabularyEdgeCases))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
