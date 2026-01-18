"""
Tests for model_manager module.

Includes unit tests and property-based tests for the model management CLI.
"""

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import given, settings, strategies as st

from handfree.model_manager import (
    MODEL_SIZES,
    MODEL_DESCRIPTIONS,
    format_size,
    get_default_models_dir,
    list_models,
    download_model,
    show_model_info,
    create_parser,
    main,
)
from handfree.local_transcriber import LocalTranscriber


class TestFormatSize(unittest.TestCase):
    """Tests for format_size helper function."""

    def test_format_bytes(self):
        """Test formatting small byte values."""
        self.assertEqual(format_size(500), "0 KB")  # 500/1000 = 0.5 -> 0
        self.assertEqual(format_size(1000), "1 KB")

    def test_format_kilobytes(self):
        """Test formatting kilobyte values."""
        self.assertEqual(format_size(5000), "5 KB")
        self.assertEqual(format_size(999999), "1000 KB")

    def test_format_megabytes(self):
        """Test formatting megabyte values."""
        self.assertEqual(format_size(1_000_000), "1 MB")
        self.assertEqual(format_size(75_000_000), "75 MB")
        self.assertEqual(format_size(142_000_000), "142 MB")
        self.assertEqual(format_size(466_000_000), "466 MB")

    def test_format_gigabytes(self):
        """Test formatting gigabyte values."""
        self.assertEqual(format_size(1_000_000_000), "1.0 GB")
        self.assertEqual(format_size(1_500_000_000), "1.5 GB")
        self.assertEqual(format_size(3_000_000_000), "3.0 GB")


class TestFormatSizeProperties(unittest.TestCase):
    """Property-based tests for format_size."""

    @given(st.integers(min_value=0, max_value=10_000_000_000))
    @settings(max_examples=20)
    def test_format_size_returns_string(self, size):
        """Test that format_size always returns a string."""
        result = format_size(size)
        self.assertIsInstance(result, str)

    @given(st.integers(min_value=0, max_value=10_000_000_000))
    @settings(max_examples=20)
    def test_format_size_contains_unit(self, size):
        """Test that format_size result contains a size unit."""
        result = format_size(size)
        self.assertTrue(
            any(unit in result for unit in ["KB", "MB", "GB"]),
            f"Expected unit in '{result}'"
        )


class TestGetDefaultModelsDir(unittest.TestCase):
    """Tests for get_default_models_dir function."""

    def test_returns_path(self):
        """Test that function returns a Path object."""
        result = get_default_models_dir()
        self.assertIsInstance(result, Path)

    def test_path_ends_with_whisper(self):
        """Test that default path ends with 'whisper'."""
        result = get_default_models_dir()
        self.assertEqual(result.name, "whisper")

    def test_path_in_cache(self):
        """Test that default path is in .cache directory."""
        result = get_default_models_dir()
        self.assertEqual(result.parent.name, ".cache")


class TestModelConstants(unittest.TestCase):
    """Tests for model constants."""

    def test_model_sizes_has_all_models(self):
        """Test that MODEL_SIZES has entries for all available models."""
        for model in LocalTranscriber.AVAILABLE_MODELS:
            self.assertIn(model, MODEL_SIZES, f"Missing size for model: {model}")

    def test_model_descriptions_has_all_models(self):
        """Test that MODEL_DESCRIPTIONS has entries for all available models."""
        for model in LocalTranscriber.AVAILABLE_MODELS:
            self.assertIn(model, MODEL_DESCRIPTIONS, f"Missing description for model: {model}")

    def test_model_sizes_are_positive(self):
        """Test that all model sizes are positive."""
        for model, size in MODEL_SIZES.items():
            self.assertGreater(size, 0, f"Size for {model} should be positive")

    def test_english_models_exist(self):
        """Test that English-only models exist."""
        english_models = [m for m in LocalTranscriber.AVAILABLE_MODELS if m.endswith(".en")]
        self.assertGreater(len(english_models), 0)


class TestListModels(unittest.TestCase):
    """Tests for list_models function."""

    def test_list_models_output(self):
        """Test that list_models produces output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                list_models(temp_dir)

            output = captured.getvalue()
            self.assertIn("Available whisper.cpp models", output)
            self.assertIn("base.en", output)
            self.assertIn("Not downloaded", output)

    def test_list_models_shows_downloaded(self):
        """Test that list_models shows downloaded models."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake model file
            model_path = Path(temp_dir) / "ggml-base.en.bin"
            model_path.write_bytes(b"x" * 1000)

            captured = io.StringIO()
            with patch('sys.stdout', captured):
                list_models(temp_dir)

            output = captured.getvalue()
            self.assertIn("Downloaded", output)


class TestDownloadModel(unittest.TestCase):
    """Tests for download_model function."""

    def test_download_invalid_model(self):
        """Test that downloading invalid model fails."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            result = download_model("invalid_model")

        self.assertFalse(result)
        output = captured.getvalue()
        self.assertIn("Unknown model", output)

    def test_download_already_exists(self):
        """Test behavior when model already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake model file
            model_path = Path(temp_dir) / "ggml-base.en.bin"
            model_path.write_bytes(b"x" * 1000)

            captured = io.StringIO()
            with patch('sys.stdout', captured):
                result = download_model("base.en", models_dir=temp_dir)

            self.assertTrue(result)
            output = captured.getvalue()
            self.assertIn("already downloaded", output)

    def test_download_triggers_download(self):
        """Test that download_model triggers download when model missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock LocalTranscriber where it's used
            with patch('handfree.model_manager.LocalTranscriber') as mock_transcriber_class:
                # Need to set AVAILABLE_MODELS on the mock class for the check
                mock_transcriber_class.AVAILABLE_MODELS = LocalTranscriber.AVAILABLE_MODELS
                mock_transcriber = MagicMock()
                mock_transcriber_class.return_value = mock_transcriber
                mock_transcriber.is_model_downloaded.return_value = False
                mock_transcriber.get_model_path.return_value = Path(temp_dir) / "model.bin"

                captured = io.StringIO()
                with patch('sys.stdout', captured):
                    result = download_model("base.en", models_dir=temp_dir)

                self.assertTrue(result)
                mock_transcriber.download_model.assert_called_once()

    def test_download_force_redownload(self):
        """Test that force flag triggers re-download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('handfree.model_manager.LocalTranscriber') as mock_transcriber_class:
                # Need to set AVAILABLE_MODELS on the mock class for the check
                mock_transcriber_class.AVAILABLE_MODELS = LocalTranscriber.AVAILABLE_MODELS
                mock_transcriber = MagicMock()
                mock_transcriber_class.return_value = mock_transcriber
                mock_transcriber.is_model_downloaded.return_value = True
                mock_transcriber.get_model_path.return_value = Path(temp_dir) / "model.bin"

                captured = io.StringIO()
                with patch('sys.stdout', captured):
                    result = download_model("base.en", models_dir=temp_dir, force=True)

                self.assertTrue(result)
                mock_transcriber.download_model.assert_called_once()


class TestShowModelInfo(unittest.TestCase):
    """Tests for show_model_info function."""

    def test_info_invalid_model(self):
        """Test that info for invalid model shows error."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            show_model_info("invalid_model")

        output = captured.getvalue()
        self.assertIn("Unknown model", output)

    def test_info_valid_model(self):
        """Test that info shows details for valid model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                show_model_info("base.en", models_dir=temp_dir)

            output = captured.getvalue()
            self.assertIn("Model: base.en", output)
            self.assertIn("Description:", output)
            self.assertIn("Status: Not downloaded", output)

    def test_info_downloaded_model(self):
        """Test that info shows correct status for downloaded model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a fake model file
            model_path = Path(temp_dir) / "ggml-base.en.bin"
            model_path.write_bytes(b"x" * 142_000_000)

            captured = io.StringIO()
            with patch('sys.stdout', captured):
                show_model_info("base.en", models_dir=temp_dir)

            output = captured.getvalue()
            self.assertIn("Status: Downloaded", output)
            self.assertIn("Actual size:", output)

    def test_info_english_model_languages(self):
        """Test that English model shows 'English only'."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            show_model_info("base.en")

        output = captured.getvalue()
        self.assertIn("English only", output)

    def test_info_multilingual_model_languages(self):
        """Test that multilingual model shows 'Multilingual'."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            show_model_info("base")

        output = captured.getvalue()
        self.assertIn("Multilingual", output)


class TestCLIParser(unittest.TestCase):
    """Tests for command-line argument parser."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        self.assertIsNotNone(parser)

    def test_parse_list_command(self):
        """Test parsing 'list' command."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        self.assertEqual(args.command, "list")

    def test_parse_download_command(self):
        """Test parsing 'download' command."""
        parser = create_parser()
        args = parser.parse_args(["download", "base.en"])
        self.assertEqual(args.command, "download")
        self.assertEqual(args.model, "base.en")
        self.assertFalse(args.force)

    def test_parse_download_with_force(self):
        """Test parsing 'download' command with --force."""
        parser = create_parser()
        args = parser.parse_args(["download", "base.en", "-f"])
        self.assertEqual(args.command, "download")
        self.assertTrue(args.force)

    def test_parse_info_command(self):
        """Test parsing 'info' command."""
        parser = create_parser()
        args = parser.parse_args(["info", "small.en"])
        self.assertEqual(args.command, "info")
        self.assertEqual(args.model, "small.en")

    def test_parse_custom_models_dir(self):
        """Test parsing --models-dir option."""
        parser = create_parser()
        args = parser.parse_args(["--models-dir", "/custom/path", "list"])
        self.assertEqual(args.models_dir, "/custom/path")


class TestMainFunction(unittest.TestCase):
    """Tests for main entry point."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            result = main([])

        self.assertEqual(result, 0)

    def test_main_list_command(self):
        """Test main with list command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                result = main(["--models-dir", temp_dir, "list"])

            self.assertEqual(result, 0)
            output = captured.getvalue()
            self.assertIn("Available whisper.cpp models", output)

    def test_main_info_command(self):
        """Test main with info command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                result = main(["--models-dir", temp_dir, "info", "base.en"])

            self.assertEqual(result, 0)
            output = captured.getvalue()
            self.assertIn("Model: base.en", output)

    def test_main_download_invalid(self):
        """Test main with download of invalid model."""
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            result = main(["download", "invalid"])

        self.assertEqual(result, 1)


class TestModelListingProperties(unittest.TestCase):
    """Property-based tests for model listing."""

    @given(st.sampled_from(LocalTranscriber.AVAILABLE_MODELS))
    @settings(max_examples=5)
    def test_all_models_have_valid_info(self, model_name):
        """Test that all available models have valid info."""
        self.assertIn(model_name, MODEL_SIZES)
        self.assertIn(model_name, MODEL_DESCRIPTIONS)
        self.assertGreater(MODEL_SIZES[model_name], 0)
        self.assertGreater(len(MODEL_DESCRIPTIONS[model_name]), 0)

    @given(st.sampled_from(LocalTranscriber.AVAILABLE_MODELS))
    @settings(max_examples=5)
    def test_show_info_runs_without_error(self, model_name):
        """Test that show_model_info runs for all models."""
        with tempfile.TemporaryDirectory() as temp_dir:
            captured = io.StringIO()
            with patch('sys.stdout', captured):
                show_model_info(model_name, models_dir=temp_dir)

            output = captured.getvalue()
            self.assertIn(f"Model: {model_name}", output)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestFormatSize))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatSizeProperties))
    suite.addTests(loader.loadTestsFromTestCase(TestGetDefaultModelsDir))
    suite.addTests(loader.loadTestsFromTestCase(TestModelConstants))
    suite.addTests(loader.loadTestsFromTestCase(TestListModels))
    suite.addTests(loader.loadTestsFromTestCase(TestDownloadModel))
    suite.addTests(loader.loadTestsFromTestCase(TestShowModelInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestCLIParser))
    suite.addTests(loader.loadTestsFromTestCase(TestMainFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestModelListingProperties))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
