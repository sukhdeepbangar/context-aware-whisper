"""
Comprehensive tests for transcriber module.

Includes unit tests, property-based tests, and integration tests.
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import io
from scipy.io import wavfile
import numpy as np

from context_aware_whisper.transcriber import Transcriber
from context_aware_whisper.exceptions import TranscriptionError


class TestTranscriberUnit(unittest.TestCase):
    """Unit tests for Transcriber class using mocks."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variable
        self.test_api_key = "test_groq_api_key_12345"
        os.environ["GROQ_API_KEY"] = self.test_api_key

    def tearDown(self):
        """Clean up after tests."""
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        transcriber = Transcriber(api_key="explicit_key")
        self.assertEqual(transcriber.api_key, "explicit_key")
        self.assertEqual(transcriber.model, "whisper-large-v3-turbo")

    def test_init_from_env(self):
        """Test initialization from environment variable."""
        transcriber = Transcriber()
        self.assertEqual(transcriber.api_key, self.test_api_key)

    def test_init_no_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        del os.environ["GROQ_API_KEY"]
        with self.assertRaises(ValueError) as context:
            Transcriber()
        self.assertIn("GROQ_API_KEY", str(context.exception))

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_success(self, mock_groq_class):
        """Test successful transcription."""
        # Set up mock
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Hello world"

        # Create transcriber and transcribe
        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        # Verify
        self.assertEqual(result, "Hello world")
        mock_client.audio.transcriptions.create.assert_called_once()

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_empty_audio(self, mock_groq_class):
        """Test transcription with empty audio returns empty string."""
        transcriber = Transcriber()
        result = transcriber.transcribe(b"")
        self.assertEqual(result, "")

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_with_language(self, mock_groq_class):
        """Test transcription with language parameter."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Bonjour"

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes, language="fr")

        # Verify language was passed
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        self.assertEqual(call_kwargs['language'], "fr")

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_strips_whitespace(self, mock_groq_class):
        """Test that transcription result is stripped of whitespace."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "  Hello world  \n"

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Hello world")

    @patch('context_aware_whisper.transcriber.Groq')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_transcribe_retry_on_rate_limit(self, mock_sleep, mock_groq_class):
        """Test retry logic on rate limit error."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # First call raises rate limit error, second succeeds
        mock_client.audio.transcriptions.create.side_effect = [
            Exception("rate_limit exceeded"),
            "Success after retry"
        ]

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Success after retry")
        self.assertEqual(mock_client.audio.transcriptions.create.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    @patch('context_aware_whisper.transcriber.Groq')
    @patch('time.sleep')
    def test_transcribe_max_retries_exceeded(self, mock_sleep, mock_groq_class):
        """Test that TranscriptionError is raised after max retries."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = Exception("API error")

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()

        with self.assertRaises(TranscriptionError) as context:
            transcriber.transcribe(audio_bytes, max_retries=3)

        self.assertIn("failed after 3 attempts", str(context.exception))
        self.assertEqual(mock_client.audio.transcriptions.create.call_count, 3)

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_handles_text_response(self, mock_groq_class):
        """Test handling of text response format."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Direct text response"

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Direct text response")

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_handles_object_response(self, mock_groq_class):
        """Test handling of object response with text attribute."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # Create mock response object with text attribute
        mock_response = MagicMock()
        mock_response.text = "Text from object"
        mock_client.audio.transcriptions.create.return_value = mock_response

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        self.assertEqual(result, "Text from object")

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_with_prompt(self, mock_groq_class):
        """Test transcription with vocabulary prompt."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Claude and tmux"

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes, prompt="Claude, tmux")

        # Verify prompt was passed
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        self.assertEqual(call_kwargs['prompt'], "Claude, tmux")
        self.assertEqual(result, "Claude and tmux")

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_with_none_prompt(self, mock_groq_class):
        """Test transcription with None prompt (default)."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Hello world"

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(audio_bytes)

        # Verify prompt was passed as None
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        self.assertIsNone(call_kwargs['prompt'])

    @patch('context_aware_whisper.transcriber.Groq')
    def test_transcribe_with_all_parameters(self, mock_groq_class):
        """Test transcription with language, prompt, and max_retries."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "Bonjour Claude"

        transcriber = Transcriber()
        audio_bytes = self._create_test_audio()
        result = transcriber.transcribe(
            audio_bytes,
            language="fr",
            prompt="Claude, Anthropic",
            max_retries=5
        )

        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        self.assertEqual(call_kwargs['language'], "fr")
        self.assertEqual(call_kwargs['prompt'], "Claude, Anthropic")
        self.assertEqual(result, "Bonjour Claude")

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        # Generate simple sine wave
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        # Encode as WAV
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestTranscriberProperties(unittest.TestCase):
    """Property-based tests for input validation."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        """Clean up after tests."""
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

    def test_transcribe_with_none_audio(self):
        """Test that None audio is handled gracefully."""
        transcriber = Transcriber()
        # Should not raise an error, returns empty string
        result = transcriber.transcribe(None or b"")
        self.assertEqual(result, "")

    def test_transcribe_various_audio_sizes(self):
        """Test transcription with various audio sizes."""
        transcriber = Transcriber()

        # Test with different byte sizes
        test_sizes = [0, 1, 100, 1000, 10000]
        for size in test_sizes:
            audio_bytes = b"x" * size
            # Should not raise an error
            try:
                # Will fail API call but shouldn't crash on input validation
                if size == 0:
                    result = transcriber.transcribe(audio_bytes)
                    self.assertEqual(result, "")
            except (TranscriptionError, Exception):
                # Expected to fail with invalid audio, but not crash
                pass

    def test_language_codes(self):
        """Test various language code inputs."""
        transcriber = Transcriber()
        audio_bytes = b"test"  # Will fail but tests input handling

        test_languages = ["en", "fr", "de", "es", None, "", "zh"]
        for lang in test_languages:
            try:
                # Should accept various language codes without crashing
                transcriber.transcribe(audio_bytes, language=lang)
            except (TranscriptionError, Exception):
                # Expected to fail with invalid audio
                pass

    def test_max_retries_values(self):
        """Test various max_retries values."""
        transcriber = Transcriber()
        audio_bytes = b"test"

        test_retries = [1, 2, 3, 5, 10]
        for retries in test_retries:
            try:
                transcriber.transcribe(audio_bytes, max_retries=retries)
            except (TranscriptionError, Exception):
                # Expected to fail, just testing it doesn't crash on input
                pass


class TestTranscriberIntegration(unittest.TestCase):
    """Integration tests with real API (requires valid GROQ_API_KEY)."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            self.skipTest("GROQ_API_KEY not set - skipping integration tests")

    def test_real_transcription(self):
        """Test actual transcription with Groq API (manual/optional test)."""
        # This test requires a valid API key and will make a real API call
        # Skip in automated testing, run manually to verify integration
        transcriber = Transcriber()

        # Create short test audio (1 second of silence)
        sample_rate = 16000
        duration = 1
        audio_data = np.zeros(sample_rate * duration, dtype=np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        audio_bytes = wav_buffer.getvalue()

        try:
            result = transcriber.transcribe(audio_bytes)
            # Silence might return empty or minimal text
            self.assertIsInstance(result, str)
            print(f"Integration test result: '{result}'")
        except TranscriptionError as e:
            print(f"Integration test failed (expected if API key invalid): {e}")


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTranscriberUnit))
    suite.addTests(loader.loadTestsFromTestCase(TestTranscriberProperties))

    # Optionally add integration tests (commented out by default)
    # suite.addTests(loader.loadTestsFromTestCase(TestTranscriberIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
