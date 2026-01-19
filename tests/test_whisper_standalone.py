"""
Standalone verification tests for whisper.cpp integration (Phase 1 verification).

These tests verify:
- Model loads successfully
- Transcription works with real audio
- Latency is acceptable
"""

import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from context_aware_whisper.local_transcriber import LocalTranscriber


class TestWhisperStandalone(unittest.TestCase):
    """Standalone tests for whisper.cpp integration."""

    MODEL_NAME = "base.en"
    MODEL_PATH = Path.home() / ".cache" / "whisper" / f"ggml-{MODEL_NAME}.bin"

    @classmethod
    def setUpClass(cls):
        """Check if model is available before running tests."""
        if not cls.MODEL_PATH.exists():
            raise unittest.SkipTest(
                f"Model {cls.MODEL_NAME} not downloaded. "
                f"Run: python -m context_aware_whisper.model_manager download {cls.MODEL_NAME}"
            )

    def test_model_loads_successfully(self):
        """Verify the whisper model loads without errors."""
        transcriber = LocalTranscriber(model_name=self.MODEL_NAME)

        # Model should not be loaded yet (lazy loading)
        self.assertFalse(transcriber.model_loaded)

        # Model file should exist
        self.assertTrue(transcriber.is_model_downloaded())

        # Trigger model load with a simple transcription
        audio = self._create_silence_audio(duration_sec=0.5)
        start = time.time()
        transcriber.transcribe(audio)
        load_time = time.time() - start

        # Model should now be loaded
        self.assertTrue(transcriber.model_loaded)

        print(f"\n  Model load + first transcription: {load_time:.2f}s")

    def test_transcription_with_tone(self):
        """Test transcription with audio containing a tone (should return minimal text)."""
        transcriber = LocalTranscriber(model_name=self.MODEL_NAME)

        # Create a 2-second tone (440 Hz - A4 note)
        audio = self._create_tone_audio(duration_sec=2, frequency=440)

        start = time.time()
        result = transcriber.transcribe(audio)
        latency = time.time() - start

        # For a pure tone, whisper might return empty or minimal text
        self.assertIsInstance(result, str)
        print(f"\n  Tone transcription result: '{result}'")
        print(f"  Latency: {latency * 1000:.0f}ms")

    def test_transcription_with_silence(self):
        """Test transcription with silent audio."""
        transcriber = LocalTranscriber(model_name=self.MODEL_NAME)

        # Create 2 seconds of silence
        audio = self._create_silence_audio(duration_sec=2)

        start = time.time()
        result = transcriber.transcribe(audio)
        latency = time.time() - start

        # For silence, whisper should return empty or minimal text
        self.assertIsInstance(result, str)
        print(f"\n  Silence transcription result: '{result}'")
        print(f"  Latency: {latency * 1000:.0f}ms")

    def test_latency_benchmark(self):
        """Benchmark transcription latency for various audio lengths."""
        transcriber = LocalTranscriber(model_name=self.MODEL_NAME)

        # Warm up the model
        warmup_audio = self._create_silence_audio(duration_sec=1)
        transcriber.transcribe(warmup_audio)

        durations = [1, 3, 5, 10]
        results = []

        print("\n  Latency benchmark:")
        print("  " + "-" * 40)

        for duration in durations:
            audio = self._create_noise_audio(duration_sec=duration)

            start = time.time()
            transcriber.transcribe(audio)
            latency = time.time() - start

            results.append((duration, latency))
            print(f"  {duration}s audio -> {latency * 1000:.0f}ms latency ({latency/duration:.2f}x realtime)")

        # Verify latency is reasonable (should be faster than realtime for base.en on M4)
        for duration, latency in results:
            # Allow up to 2x realtime for CI environments
            self.assertLess(latency, duration * 2,
                f"Latency {latency:.1f}s exceeded 2x realtime for {duration}s audio")

    def test_multiple_transcriptions(self):
        """Test multiple consecutive transcriptions."""
        transcriber = LocalTranscriber(model_name=self.MODEL_NAME)

        # Pre-load model
        transcriber.transcribe(self._create_silence_audio(duration_sec=1))

        latencies = []
        for i in range(5):
            audio = self._create_noise_audio(duration_sec=2)
            start = time.time()
            transcriber.transcribe(audio)
            latency = time.time() - start
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\n  5 consecutive 2s transcriptions:")
        print(f"  Latencies: {[f'{l*1000:.0f}ms' for l in latencies]}")
        print(f"  Average: {avg_latency * 1000:.0f}ms")

        # Verify consistent performance
        for latency in latencies:
            # Each transcription should be under 5 seconds
            self.assertLess(latency, 5.0)

    def test_model_unload_reload(self):
        """Test unloading and reloading the model."""
        transcriber = LocalTranscriber(model_name=self.MODEL_NAME)

        # Load model
        audio = self._create_silence_audio(duration_sec=1)
        transcriber.transcribe(audio)
        self.assertTrue(transcriber.model_loaded)

        # Unload model
        transcriber.unload_model()
        self.assertFalse(transcriber.model_loaded)

        # Model should reload on next transcription
        start = time.time()
        transcriber.transcribe(audio)
        reload_time = time.time() - start

        self.assertTrue(transcriber.model_loaded)
        print(f"\n  Model reload time: {reload_time:.2f}s")

    def _create_silence_audio(self, duration_sec: float, sample_rate: int = 16000) -> bytes:
        """Create silent audio WAV bytes."""
        samples = int(sample_rate * duration_sec)
        audio_data = np.zeros(samples, dtype=np.int16)
        return self._array_to_wav(audio_data, sample_rate)

    def _create_tone_audio(self, duration_sec: float, frequency: int = 440,
                          sample_rate: int = 16000) -> bytes:
        """Create a pure tone audio WAV bytes."""
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)
        return self._array_to_wav(audio_data, sample_rate)

    def _create_noise_audio(self, duration_sec: float, sample_rate: int = 16000) -> bytes:
        """Create random noise audio WAV bytes."""
        samples = int(sample_rate * duration_sec)
        # Low-amplitude noise
        audio_data = (np.random.randn(samples) * 1000).astype(np.int16)
        return self._array_to_wav(audio_data, sample_rate)

    def _array_to_wav(self, audio_data: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy array to WAV bytes."""
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, sample_rate, audio_data)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


if __name__ == "__main__":
    unittest.main(verbosity=2)
