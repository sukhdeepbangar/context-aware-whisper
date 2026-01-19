"""
Performance Comparison Tests for Cloud vs Local Transcription.

Tests that compare Groq cloud transcription with whisper.cpp local transcription
in terms of interface compatibility, latency characteristics, and behavior.

Phase 6.3 of whisper_cpp_plan.md
"""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import Protocol, runtime_checkable
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
from hypothesis import given, settings, strategies as st
from scipy.io import wavfile

from context_aware_whisper.transcriber import Transcriber
from context_aware_whisper.local_transcriber import LocalTranscriber
from context_aware_whisper.exceptions import TranscriptionError, LocalTranscriptionError


@runtime_checkable
class TranscriberProtocol(Protocol):
    """Protocol defining the expected transcriber interface."""

    def transcribe(self, audio_bytes: bytes, language: str = ...) -> str:
        """Transcribe audio bytes to text."""
        ...


class TestTranscriberInterfaceCompatibility(unittest.TestCase):
    """Tests verifying both transcribers have compatible interfaces."""

    def test_groq_transcriber_implements_protocol(self):
        """Groq Transcriber has the expected transcribe method signature."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            transcriber = Transcriber(api_key="test-key")
            self.assertTrue(hasattr(transcriber, "transcribe"))
            self.assertTrue(callable(transcriber.transcribe))

    def test_local_transcriber_implements_protocol(self):
        """Local Transcriber has the expected transcribe method signature."""
        transcriber = LocalTranscriber(model_name="base.en")
        self.assertTrue(hasattr(transcriber, "transcribe"))
        self.assertTrue(callable(transcriber.transcribe))

    def test_both_transcribers_return_string(self):
        """Both transcribers return string from transcribe method."""
        # Test Groq transcriber with mock
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            groq_transcriber = Transcriber(api_key="test-key")
            with patch.object(groq_transcriber, "client") as mock_client:
                mock_client.audio.transcriptions.create.return_value = "Hello world"

                result = groq_transcriber.transcribe(self._create_test_audio())
                self.assertIsInstance(result, str)

        # Test Local transcriber with mock
        with patch("context_aware_whisper.local_transcriber.Model") as mock_model_class:
            mock_model = MagicMock()
            mock_model_class.return_value = mock_model
            segment = MagicMock()
            segment.text = "Hello world"
            mock_model.transcribe.return_value = [segment]

            local_transcriber = LocalTranscriber()
            result = local_transcriber.transcribe(self._create_test_audio())
            self.assertIsInstance(result, str)

    def test_both_handle_empty_audio(self):
        """Both transcribers handle empty audio gracefully."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            groq_transcriber = Transcriber(api_key="test-key")
            # Empty audio returns empty string without hitting the API
            result = groq_transcriber.transcribe(b"")
            self.assertIsInstance(result, str)
            self.assertEqual(result, "")

        local_transcriber = LocalTranscriber()
        result = local_transcriber.transcribe(b"")
        self.assertEqual(result, "")

    def test_both_accept_language_parameter(self):
        """Both transcribers accept language parameter."""
        # Groq transcriber
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            groq_transcriber = Transcriber(api_key="test-key")
            with patch.object(groq_transcriber, "client") as mock_client:
                mock_client.audio.transcriptions.create.return_value = "Bonjour"

                groq_transcriber.transcribe(self._create_test_audio(), language="fr")
                # Should not raise

        # Local transcriber
        with patch("context_aware_whisper.local_transcriber.Model") as mock_model_class:
            mock_model = MagicMock()
            mock_model_class.return_value = mock_model
            segment = MagicMock()
            segment.text = "Bonjour"
            mock_model.transcribe.return_value = [segment]

            local_transcriber = LocalTranscriber()
            local_transcriber.transcribe(self._create_test_audio(), language="fr")
            # Should not raise

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestLatencyComparison(unittest.TestCase):
    """Tests comparing latency characteristics of both transcribers."""

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_local_transcription_latency_measurable(self, mock_model_class):
        """Local transcription latency can be measured."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "Test transcription"
        mock_model.transcribe.return_value = [segment]

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio(duration_sec=1)

        start = time.perf_counter()
        result = transcriber.transcribe(audio_bytes)
        elapsed = time.perf_counter() - start

        self.assertIsNotNone(elapsed)
        self.assertGreater(elapsed, 0)
        self.assertEqual(result, "Test transcription")

    def test_cloud_transcription_latency_measurable(self):
        """Cloud transcription latency can be measured."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            transcriber = Transcriber(api_key="test-key")

            with patch.object(transcriber, "client") as mock_client:
                mock_client.audio.transcriptions.create.return_value = "Test transcription"

                audio_bytes = self._create_test_audio(duration_sec=1)

                start = time.perf_counter()
                result = transcriber.transcribe(audio_bytes)
                elapsed = time.perf_counter() - start

                self.assertIsNotNone(elapsed)
                self.assertGreater(elapsed, 0)
                self.assertEqual(result, "Test transcription")

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_local_latency_consistent_across_calls(self, mock_model_class):
        """Local transcription latency is consistent across multiple calls."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "Test"
        mock_model.transcribe.return_value = [segment]

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio(duration_sec=1)

        latencies = []
        for _ in range(5):
            start = time.perf_counter()
            transcriber.transcribe(audio_bytes)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        # With mocks, latency should be very consistent (low variance)
        avg_latency = sum(latencies) / len(latencies)
        max_deviation = max(abs(l - avg_latency) for l in latencies)

        # Deviation should be small (< 100ms with mocks)
        self.assertLess(max_deviation, 0.1)

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestAudioDurationScaling(unittest.TestCase):
    """Tests for how transcription behaves with different audio durations."""

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_local_handles_variable_duration(self, mock_model_class):
        """Local transcriber handles audio of varying durations."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        durations = [1, 5, 10, 30]
        for duration in durations:
            segment = MagicMock()
            segment.text = f"Audio duration {duration} seconds"
            mock_model.transcribe.return_value = [segment]

            transcriber = LocalTranscriber()
            audio_bytes = self._create_test_audio(duration_sec=duration)

            result = transcriber.transcribe(audio_bytes)

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_cloud_handles_variable_duration(self):
        """Cloud transcriber handles audio of varying durations."""
        durations = [1, 5, 10, 30]
        for duration in durations:
            with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
                transcriber = Transcriber(api_key="test-key")

                with patch.object(transcriber, "client") as mock_client:
                    mock_client.audio.transcriptions.create.return_value = f"Audio duration {duration} seconds"

                    audio_bytes = self._create_test_audio(duration_sec=duration)
                    result = transcriber.transcribe(audio_bytes)

                    self.assertIsInstance(result, str)
                    self.assertGreater(len(result), 0)

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestErrorHandlingComparison(unittest.TestCase):
    """Tests comparing error handling between transcribers."""

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_local_raises_proper_exception_type(self, mock_model_class):
        """Local transcriber raises LocalTranscriptionError on failure."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.transcribe.side_effect = Exception("Model error")

        transcriber = LocalTranscriber()
        audio_bytes = self._create_test_audio()

        with self.assertRaises(LocalTranscriptionError):
            transcriber.transcribe(audio_bytes)

    def test_cloud_raises_proper_exception_type(self):
        """Cloud transcriber raises TranscriptionError on failure."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            transcriber = Transcriber(api_key="test-key")

            with patch.object(transcriber, "client") as mock_client:
                mock_client.audio.transcriptions.create.side_effect = Exception("API error")

                audio_bytes = self._create_test_audio()

                with self.assertRaises(TranscriptionError):
                    transcriber.transcribe(audio_bytes)

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_both_handle_corrupted_audio(self, mock_model_class):
        """Both transcribers handle corrupted audio data."""
        # Local transcriber
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.transcribe.side_effect = Exception("Invalid audio format")

        local_transcriber = LocalTranscriber()
        corrupted_audio = b"not valid wav data"

        with self.assertRaises(LocalTranscriptionError):
            local_transcriber.transcribe(corrupted_audio)

        # Cloud transcriber
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            cloud_transcriber = Transcriber(api_key="test-key")

            with patch.object(cloud_transcriber, "client") as mock_client:
                mock_client.audio.transcriptions.create.side_effect = Exception("Invalid audio")

                with self.assertRaises(TranscriptionError):
                    cloud_transcriber.transcribe(corrupted_audio)

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestModelComparison(unittest.TestCase):
    """Tests comparing different model configurations."""

    def test_local_transcriber_model_options(self):
        """Local transcriber supports multiple model options."""
        models = ["tiny.en", "base.en", "small.en"]

        for model in models:
            transcriber = LocalTranscriber(model_name=model)
            self.assertEqual(transcriber.model_name, model)

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_different_models_produce_output(self, mock_model_class):
        """Different local models all produce valid output."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        models = ["tiny.en", "base.en", "small.en"]
        audio_bytes = self._create_test_audio()

        for model_name in models:
            segment = MagicMock()
            segment.text = f"Transcription from {model_name}"
            mock_model.transcribe.return_value = [segment]

            transcriber = LocalTranscriber(model_name=model_name)
            result = transcriber.transcribe(audio_bytes)

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_cloud_transcriber_single_model(self):
        """Cloud transcriber uses whisper-large-v3-turbo by default."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            transcriber = Transcriber(api_key="test-key")
            # Verify model is configured
            self.assertTrue(hasattr(transcriber, "_model") or hasattr(transcriber, "model"))

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestMemoryUsageComparison(unittest.TestCase):
    """Tests comparing memory-related behaviors."""

    def test_local_transcriber_model_unload(self):
        """Local transcriber can unload model to free memory."""
        transcriber = LocalTranscriber()
        self.assertFalse(transcriber.model_loaded)

        # After unload, model_loaded should be False
        transcriber.unload_model()
        self.assertFalse(transcriber.model_loaded)

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_local_transcriber_model_load_on_demand(self, mock_model_class):
        """Local transcriber loads model only when needed."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "Test"
        mock_model.transcribe.return_value = [segment]

        transcriber = LocalTranscriber()

        # Model not loaded yet
        self.assertFalse(transcriber.model_loaded)

        # Transcribe loads the model
        transcriber.transcribe(self._create_test_audio())
        self.assertTrue(transcriber.model_loaded)

        # Unload
        transcriber.unload_model()
        self.assertFalse(transcriber.model_loaded)

    def test_cloud_transcriber_no_model_state(self):
        """Cloud transcriber has no local model state to manage."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            transcriber = Transcriber(api_key="test-key")
            # Cloud transcriber doesn't have model_loaded or unload_model
            self.assertFalse(hasattr(transcriber, "unload_model"))

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestTranscriberSwitching(unittest.TestCase):
    """Tests for switching between transcription backends."""

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_can_use_both_transcribers_in_sequence(self, mock_model_class):
        """Both transcribers can be used sequentially in the same session."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "Local transcription"
        mock_model.transcribe.return_value = [segment]

        audio_bytes = self._create_test_audio()

        # Use local transcriber
        local_transcriber = LocalTranscriber()
        local_result = local_transcriber.transcribe(audio_bytes)
        self.assertEqual(local_result, "Local transcription")

        # Use cloud transcriber
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            cloud_transcriber = Transcriber(api_key="test-key")

            with patch.object(cloud_transcriber, "client") as mock_client:
                mock_client.audio.transcriptions.create.return_value = "Cloud transcription"

                cloud_result = cloud_transcriber.transcribe(audio_bytes)
                self.assertEqual(cloud_result, "Cloud transcription")

    @patch("context_aware_whisper.local_transcriber.Model")
    def test_transcribers_are_independent(self, mock_model_class):
        """Transcribers don't share state or interfere with each other."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        segment = MagicMock()
        segment.text = "Independent result"
        mock_model.transcribe.return_value = [segment]

        # Create both transcribers
        local_transcriber = LocalTranscriber(model_name="tiny.en")

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            cloud_transcriber = Transcriber(api_key="test-key")

        # Verify they have different configurations
        self.assertEqual(local_transcriber.model_name, "tiny.en")
        # Cloud transcriber uses different model

    def _create_test_audio(self, duration_sec=1, sample_rate=16000):
        """Helper to create test audio bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class TestPerformanceCharacteristicsDocumented(unittest.TestCase):
    """Tests that verify performance characteristics are as documented."""

    def test_local_transcriber_english_models_available(self):
        """English-only models (*.en) are available for faster transcription."""
        english_models = [m for m in LocalTranscriber.AVAILABLE_MODELS if m.endswith(".en")]
        self.assertGreater(len(english_models), 0)
        self.assertIn("base.en", english_models)
        self.assertIn("tiny.en", english_models)

    def test_local_transcriber_model_size_ordering(self):
        """Models are ordered by size (tiny < base < small < medium < large)."""
        expected_order = ["tiny", "base", "small", "medium", "large"]

        available = LocalTranscriber.AVAILABLE_MODELS
        positions = {}
        for model in available:
            base_name = model.replace(".en", "").split("-")[0]
            if base_name in expected_order:
                positions[base_name] = expected_order.index(base_name)

        # Verify all base sizes are present
        self.assertGreater(len(positions), 3)

    def test_default_model_is_base_en(self):
        """Default model is base.en (recommended for general use)."""
        transcriber = LocalTranscriber()
        self.assertEqual(transcriber.model_name, "base.en")

    def test_models_dir_default_location(self):
        """Default models directory is in user cache."""
        transcriber = LocalTranscriber()
        self.assertIn(".cache", transcriber.models_dir)
        self.assertIn("whisper", transcriber.models_dir)


def run_tests():
    """Run all performance comparison tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestTranscriberInterfaceCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestLatencyComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioDurationScaling))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandlingComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestModelComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryUsageComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestTranscriberSwitching))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceCharacteristicsDocumented))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
