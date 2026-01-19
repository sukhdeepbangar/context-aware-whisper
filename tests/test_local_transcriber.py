"""
Tests for LocalTranscriber module.

Includes unit tests, property-based tests, and integration tests.
"""

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from hypothesis import given, settings, strategies as st
from scipy.io import wavfile

from context_aware_whisper.local_transcriber import LocalTranscriber
from context_aware_whisper.exceptions import LocalTranscriptionError


class TestLocalTranscriberUnit(unittest.TestCase):
    """Unit tests for LocalTranscriber class using mocks."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        transcriber = LocalTranscriber()
        self.assertEqual(transcriber.model_name, "base.en")
        self.assertEqual(transcriber.models_dir, os.path.expanduser("~/.cache/whisper"))
        self.assertFalse(transcriber.model_loaded)

    def test_init_with_custom_model(self):
        """Test initialization with custom model name."""
        transcriber = LocalTranscriber(model_name="tiny.en")
        self.assertEqual(transcriber.model_name, "tiny.en")

    def test_init_with_custom_models_dir(self):
        """Test initialization with custom models directory."""
        custom_dir = "/custom/models/path"
        transcriber = LocalTranscriber(models_dir=custom_dir)
        self.assertEqual(transcriber.models_dir, custom_dir)

    def test_init_invalid_model_raises_error(self):
        """Test that invalid model name raises ValueError."""
        with self.assertRaises(ValueError) as context:
            LocalTranscriber(model_name="invalid_model")
        self.assertIn("Unknown model", str(context.exception))
        self.assertIn("invalid_model", str(context.exception))

    def test_available_models_list(self):
        """Test that AVAILABLE_MODELS contains expected models."""
        expected_models = ["tiny", "tiny.en", "base", "base.en", "small", "small.en"]
        for model in expected_models:
            self.assertIn(model, LocalTranscriber.AVAILABLE_MODELS)

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_transcribe_empty_audio(self, mock_model_class):
        """Test transcription with empty audio returns empty string."""
        transcriber = LocalTranscriber()
        result = transcriber.transcribe(b"")
        self.assertEqual(result, "")
        mock_model_class.assert_not_called()

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_transcribe_success(self, mock_model_class):
        """Test successful transcription."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_segment = MagicMock()
        mock_segment.text = "Hello world"
        mock_model.transcribe.return_value = [mock_segment]

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Hello world")
        mock_model.transcribe.assert_called_once()

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_transcribe_multiple_segments(self, mock_model_class):
        """Test transcription with multiple segments."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment1 = MagicMock()
        segment1.text = "Hello"
        segment2 = MagicMock()
        segment2.text = "world"
        mock_model.transcribe.return_value = [segment1, segment2]

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Hello world")

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_transcribe_strips_whitespace(self, mock_model_class):
        """Test that transcription result is stripped of whitespace."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_segment = MagicMock()
        mock_segment.text = "  Hello world  \n"
        mock_model.transcribe.return_value = [mock_segment]

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Hello world")

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_transcribe_empty_segments(self, mock_model_class):
        """Test transcription with empty/whitespace-only segments."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment1 = MagicMock()
        segment1.text = "   "
        segment2 = MagicMock()
        segment2.text = "Hello"
        segment3 = MagicMock()
        segment3.text = ""
        mock_model.transcribe.return_value = [segment1, segment2, segment3]

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Hello")

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_transcribe_failure_raises_error(self, mock_model_class):
        """Test that transcription failure raises LocalTranscriptionError."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.transcribe.side_effect = Exception("Model error")

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()

        with self.assertRaises(LocalTranscriptionError) as context:
            transcriber.transcribe(audio_bytes)
        self.assertIn("Transcription failed", str(context.exception))

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_model_load_failure_raises_error(self, mock_model_class):
        """Test that model loading failure raises LocalTranscriptionError."""
        mock_model_class.side_effect = Exception("Failed to load model")

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()

        with self.assertRaises(LocalTranscriptionError) as context:
            transcriber.transcribe(audio_bytes)
        self.assertIn("Failed to load whisper model", str(context.exception))

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_model_loaded_property(self, mock_model_class):
        """Test model_loaded property."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "test"
        mock_model.transcribe.return_value = [segment]

        transcriber = LocalTranscriber()
        self.assertFalse(transcriber.model_loaded)

        transcriber.transcribe(self._create_test_audio())
        self.assertTrue(transcriber.model_loaded)

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_unload_model(self, mock_model_class):
        """Test unload_model clears model from memory."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "test"
        mock_model.transcribe.return_value = [segment]

        transcriber = LocalTranscriber()
        transcriber.transcribe(self._create_test_audio())
        self.assertTrue(transcriber.model_loaded)

        transcriber.unload_model()
        self.assertFalse(transcriber.model_loaded)

    def test_get_model_path(self):
        """Test get_model_path returns correct path."""
        transcriber = LocalTranscriber(model_name="base.en")
        expected_path = Path(os.path.expanduser("~/.cache/whisper")) / "ggml-base.en.bin"
        self.assertEqual(transcriber.get_model_path(), expected_path)

    def test_is_model_downloaded_false(self):
        """Test is_model_downloaded returns False for non-existent model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            transcriber = LocalTranscriber(models_dir=temp_dir)
            self.assertFalse(transcriber.is_model_downloaded())

    def test_is_model_downloaded_true(self):
        """Test is_model_downloaded returns True when model file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "ggml-base.en.bin"
            model_path.write_bytes(b"dummy model data")

            transcriber = LocalTranscriber(models_dir=temp_dir)
            self.assertTrue(transcriber.is_model_downloaded())

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_download_model_already_exists(self, mock_model_class):
        """Test download_model when model already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "ggml-base.en.bin"
            model_path.write_bytes(b"dummy model data")

            transcriber = LocalTranscriber(models_dir=temp_dir)
            transcriber.download_model()

            mock_model_class.assert_not_called()

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_download_model_triggers_download(self, mock_model_class):
        """Test download_model triggers model loading when not present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            transcriber = LocalTranscriber(models_dir=temp_dir)
            transcriber.download_model()

            mock_model_class.assert_called_once()

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestLocalTranscriberProperties(unittest.TestCase):
    """Property-based tests for LocalTranscriber."""

    @given(st.sampled_from(LocalTranscriber.AVAILABLE_MODELS))
    @settings(max_examples=5)
    def test_valid_models_accepted(self, model_name):
        """Test that all available models are accepted."""
        transcriber = LocalTranscriber(model_name=model_name)
        self.assertEqual(transcriber.model_name, model_name)

    @given(st.text(min_size=1, max_size=20).filter(
        lambda x: x not in LocalTranscriber.AVAILABLE_MODELS
    ))
    @settings(max_examples=10)
    def test_invalid_models_rejected(self, model_name):
        """Test that invalid model names are rejected."""
        with self.assertRaises(ValueError):
            LocalTranscriber(model_name=model_name)

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=5)
    def test_custom_models_dir_accepted(self, models_dir):
        """Test that any string is accepted as models_dir."""
        transcriber = LocalTranscriber(models_dir=models_dir)
        self.assertEqual(transcriber.models_dir, models_dir)


class TestLocalTranscriberTempFileCleanup(unittest.TestCase):
    """Tests for temporary file cleanup."""

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_temp_file_cleaned_on_success(self, mock_model_class):
        """Test temp file is cleaned up after successful transcription."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "Hello"
        mock_model.transcribe.return_value = [segment]

        temp_files_before = set(Path(tempfile.gettempdir()).glob("*.wav"))

        transcriber = LocalTranscriber()
        transcriber.transcribe(self._create_test_audio())

        temp_files_after = set(Path(tempfile.gettempdir()).glob("*.wav"))
        new_files = temp_files_after - temp_files_before
        self.assertEqual(len(new_files), 0, "Temp file not cleaned up")

    @patch('context_aware_whisper.local_transcriber.Model')
    def test_temp_file_cleaned_on_error(self, mock_model_class):
        """Test temp file is cleaned up even when transcription fails."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.transcribe.side_effect = Exception("Error")

        temp_files_before = set(Path(tempfile.gettempdir()).glob("*.wav"))

        transcriber = LocalTranscriber()
        with self.assertRaises(LocalTranscriptionError):
            transcriber.transcribe(self._create_test_audio())

        temp_files_after = set(Path(tempfile.gettempdir()).glob("*.wav"))
        new_files = temp_files_after - temp_files_before
        self.assertEqual(len(new_files), 0, "Temp file not cleaned up after error")

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestLocalTranscriberIntegration(unittest.TestCase):
    """Integration tests with real whisper.cpp model (requires model download)."""

    @unittest.skipUnless(
        os.environ.get("RUN_LOCAL_TRANSCRIBER_INTEGRATION_TESTS"),
        "Set RUN_LOCAL_TRANSCRIBER_INTEGRATION_TESTS=1 to run integration tests"
    )
    def test_real_transcription_tiny_model(self):
        """Test actual transcription with tiny.en model."""
        transcriber = LocalTranscriber(model_name="tiny.en")

        sample_rate = 16000
        duration = 2
        audio_data = np.zeros(sample_rate * duration, dtype=np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        audio_bytes = wav_buffer.getvalue()

        result = transcriber.transcribe(audio_bytes)
        self.assertIsInstance(result, str)
        print(f"Integration test result: '{result}'")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestLocalTranscriberUnit))
    suite.addTests(loader.loadTestsFromTestCase(TestLocalTranscriberProperties))
    suite.addTests(loader.loadTestsFromTestCase(TestLocalTranscriberTempFileCleanup))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
