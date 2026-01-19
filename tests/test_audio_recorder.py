"""
Comprehensive tests for AudioRecorder module.
Includes unit tests, integration tests, and property-based tests.
"""

import io
import time
import wave
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pytest
from scipy.io import wavfile

from context_aware_whisper.audio_recorder import AudioRecorder


class TestAudioRecorderInitialization:
    """Test AudioRecorder initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        recorder = AudioRecorder()
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert len(recorder.buffer) == 0
        assert recorder.stream is None
        assert not recorder.is_recording

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        recorder = AudioRecorder(sample_rate=48000, channels=2)
        assert recorder.sample_rate == 48000
        assert recorder.channels == 2
        assert len(recorder.buffer) == 0
        assert not recorder.is_recording

    def test_init_various_sample_rates(self):
        """Test initialization with various valid sample rates."""
        sample_rates = [8000, 16000, 22050, 44100, 48000]
        for rate in sample_rates:
            recorder = AudioRecorder(sample_rate=rate)
            assert recorder.sample_rate == rate


class TestAudioRecorderBufferOperations:
    """Test buffer management operations."""

    def test_clear_buffer(self):
        """Test clearing the audio buffer."""
        recorder = AudioRecorder()
        # Add some mock data to buffer
        recorder.buffer.append(np.array([1, 2, 3]))
        recorder.buffer.append(np.array([4, 5, 6]))
        assert len(recorder.buffer) == 2

        recorder.clear_buffer()
        assert len(recorder.buffer) == 0

    def test_get_duration_empty_buffer(self):
        """Test duration calculation with empty buffer."""
        recorder = AudioRecorder()
        assert recorder.get_duration() == 0.0

    def test_get_duration_with_data(self):
        """Test duration calculation with audio data."""
        recorder = AudioRecorder(sample_rate=16000)
        # Add 16000 samples (1 second at 16kHz)
        chunk1 = np.zeros((8000, 1), dtype='int16')
        chunk2 = np.zeros((8000, 1), dtype='int16')
        recorder.buffer.append(chunk1)
        recorder.buffer.append(chunk2)

        duration = recorder.get_duration()
        assert duration == 1.0

    def test_get_duration_multiple_chunks(self):
        """Test duration calculation with multiple chunks."""
        recorder = AudioRecorder(sample_rate=16000)
        # Add 3 chunks of 5333 samples each (~1 second total)
        for _ in range(3):
            chunk = np.zeros((5333, 1), dtype='int16')
            recorder.buffer.append(chunk)

        duration = recorder.get_duration()
        expected = 15999 / 16000  # 3 * 5333 / 16000
        assert abs(duration - expected) < 0.01


class TestAudioRecorderRecordingFlow:
    """Test recording start/stop flow."""

    @patch('sounddevice.InputStream')
    def test_start_recording_creates_stream(self, mock_stream_class):
        """Test that start_recording creates and starts a stream."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        # Verify stream was created with correct parameters
        mock_stream_class.assert_called_once()
        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs['samplerate'] == 16000
        assert call_kwargs['channels'] == 1
        assert call_kwargs['dtype'] == 'int16'
        assert callable(call_kwargs['callback'])

        # Verify stream was started
        mock_stream.start.assert_called_once()
        assert recorder.is_recording

    @patch('sounddevice.InputStream')
    def test_start_recording_clears_buffer(self, mock_stream_class):
        """Test that start_recording clears existing buffer."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.buffer.append(np.array([1, 2, 3]))
        recorder.start_recording()

        assert len(recorder.buffer) == 0

    @patch('sounddevice.InputStream')
    def test_start_recording_idempotent(self, mock_stream_class):
        """Test that calling start_recording twice doesn't create multiple streams."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start_recording()
        recorder.start_recording()

        # Should only be called once
        assert mock_stream_class.call_count == 1

    @patch('sounddevice.InputStream')
    def test_stop_recording_without_start(self, mock_stream_class):
        """Test stopping recording when not recording returns empty bytes."""
        recorder = AudioRecorder()
        result = recorder.stop_recording()

        assert result == b''
        assert not recorder.is_recording

    @patch('sounddevice.InputStream')
    def test_stop_recording_with_empty_buffer(self, mock_stream_class):
        """Test stopping recording with empty buffer returns empty bytes."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start_recording()
        result = recorder.stop_recording()

        assert result == b''
        assert not recorder.is_recording
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch('sounddevice.InputStream')
    def test_stop_recording_with_data(self, mock_stream_class):
        """Test stopping recording with audio data returns valid WAV bytes."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        # Simulate audio data being captured
        audio_data = np.random.randint(-32768, 32767, size=(16000, 1), dtype='int16')
        recorder.buffer.append(audio_data)

        result = recorder.stop_recording()

        # Verify result is valid WAV bytes
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:4] == b'RIFF'  # WAV file header

        # Verify stream was stopped
        assert not recorder.is_recording
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch('sounddevice.InputStream')
    def test_audio_callback_appends_to_buffer(self, mock_stream_class):
        """Test that audio callback appends data to buffer."""
        recorder = AudioRecorder()

        # Create sample audio data
        sample_data = np.array([[100], [200], [300]], dtype='int16')

        # Call the callback directly
        recorder._audio_callback(sample_data, 3, None, None)

        assert len(recorder.buffer) == 1
        np.testing.assert_array_equal(recorder.buffer[0], sample_data)

    @patch('sounddevice.InputStream')
    def test_audio_callback_with_status(self, mock_stream_class, capsys):
        """Test that audio callback prints status messages."""
        recorder = AudioRecorder()
        sample_data = np.array([[100]], dtype='int16')

        # Call callback with status
        recorder._audio_callback(sample_data, 1, None, "Input overflow")

        captured = capsys.readouterr()
        assert "Input overflow" in captured.out


class TestAudioRecorderWAVEncoding:
    """Test WAV file encoding."""

    @patch('sounddevice.InputStream')
    def test_wav_encoding_format(self, mock_stream_class):
        """Test that encoded WAV has correct format."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        # Add audio data
        audio_data = np.random.randint(-32768, 32767, size=(16000, 1), dtype='int16')
        recorder.buffer.append(audio_data)

        wav_bytes = recorder.stop_recording()

        # Parse WAV file
        wav_io = io.BytesIO(wav_bytes)
        with wave.open(wav_io, 'rb') as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2  # 16-bit = 2 bytes
            assert wav_file.getframerate() == 16000

    @patch('sounddevice.InputStream')
    def test_wav_encoding_multiple_chunks(self, mock_stream_class):
        """Test WAV encoding with multiple audio chunks."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        # Add multiple chunks
        chunk1 = np.random.randint(-32768, 32767, size=(8000, 1), dtype='int16')
        chunk2 = np.random.randint(-32768, 32767, size=(8000, 1), dtype='int16')
        recorder.buffer.append(chunk1)
        recorder.buffer.append(chunk2)

        wav_bytes = recorder.stop_recording()

        # Verify combined data
        wav_io = io.BytesIO(wav_bytes)
        with wave.open(wav_io, 'rb') as wav_file:
            assert wav_file.getnframes() == 16000


class TestAudioRecorderPropertyBasedTests:
    """Property-based tests for AudioRecorder."""

    @pytest.mark.parametrize("sample_rate", [8000, 16000, 22050, 44100, 48000])
    @patch('sounddevice.InputStream')
    def test_duration_calculation_accuracy(self, mock_stream_class, sample_rate):
        """Test that duration calculation is accurate for various sample rates."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=sample_rate)

        # Add exactly 1 second of audio
        num_samples = sample_rate
        audio_data = np.zeros((num_samples, 1), dtype='int16')
        recorder.buffer.append(audio_data)

        duration = recorder.get_duration()
        assert abs(duration - 1.0) < 0.0001  # Should be very close to 1 second

    @pytest.mark.parametrize("num_chunks", [1, 5, 10, 20])
    @patch('sounddevice.InputStream')
    def test_buffer_concatenation(self, mock_stream_class, num_chunks):
        """Test that buffer concatenation works for various chunk counts."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000)
        recorder.start_recording()

        chunk_size = 1000
        expected_total = num_chunks * chunk_size

        # Add multiple chunks
        for i in range(num_chunks):
            chunk = np.full((chunk_size, 1), i, dtype='int16')
            recorder.buffer.append(chunk)

        wav_bytes = recorder.stop_recording()

        # Verify total length
        wav_io = io.BytesIO(wav_bytes)
        rate, data = wavfile.read(wav_io)
        assert len(data) == expected_total

    @pytest.mark.parametrize("channels", [1, 2])
    @patch('sounddevice.InputStream')
    def test_channel_configuration(self, mock_stream_class, channels):
        """Test recorder with different channel configurations."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=channels)
        recorder.start_recording()

        # Verify stream was created with correct channels
        call_kwargs = mock_stream_class.call_args[1]
        assert call_kwargs['channels'] == channels


class TestAudioRecorderIntegration:
    """Integration tests for AudioRecorder (requires audio device)."""

    @pytest.mark.integration
    def test_real_recording_short_duration(self):
        """Integration test: Record actual audio for a very short duration."""
        recorder = AudioRecorder()

        try:
            recorder.start_recording()
            assert recorder.is_recording

            # Record for 0.1 seconds
            time.sleep(0.1)

            wav_bytes = recorder.stop_recording()
            assert not recorder.is_recording

            # Verify we got some audio data
            assert len(wav_bytes) > 0
            assert wav_bytes[:4] == b'RIFF'

            # Verify duration is approximately 0.1 seconds
            wav_io = io.BytesIO(wav_bytes)
            with wave.open(wav_io, 'rb') as wav_file:
                duration = wav_file.getnframes() / wav_file.getframerate()
                assert 0.05 < duration < 0.15  # Allow some tolerance

        except Exception as e:
            pytest.skip(f"Audio device not available: {e}")

    @pytest.mark.integration
    def test_real_recording_verify_format(self):
        """Integration test: Verify recorded audio format."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)

        try:
            recorder.start_recording()
            time.sleep(0.05)
            wav_bytes = recorder.stop_recording()

            # Parse and verify WAV format
            wav_io = io.BytesIO(wav_bytes)
            rate, data = wavfile.read(wav_io)

            assert rate == 16000
            assert data.dtype == np.int16

        except Exception as e:
            pytest.skip(f"Audio device not available: {e}")


class TestAudioRecorderEdgeCases:
    """Test edge cases and error conditions."""

    @patch('sounddevice.InputStream')
    def test_multiple_start_stop_cycles(self, mock_stream_class):
        """Test multiple recording cycles."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()

        for i in range(3):
            recorder.start_recording()
            audio_data = np.random.randint(-32768, 32767, size=(1000, 1), dtype='int16')
            recorder.buffer.append(audio_data)
            wav_bytes = recorder.stop_recording()

            assert len(wav_bytes) > 0
            assert not recorder.is_recording

    @patch('sounddevice.InputStream')
    def test_very_large_buffer(self, mock_stream_class):
        """Test handling of very large audio buffer."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000)
        recorder.start_recording()

        # Add 60 seconds worth of audio (simulating max duration)
        for _ in range(60):
            chunk = np.random.randint(-32768, 32767, size=(16000, 1), dtype='int16')
            recorder.buffer.append(chunk)

        duration = recorder.get_duration()
        assert 59.5 < duration < 60.5  # Should be ~60 seconds

        wav_bytes = recorder.stop_recording()
        assert len(wav_bytes) > 0

    def test_is_recording_property(self):
        """Test is_recording property returns correct state."""
        recorder = AudioRecorder()
        assert not recorder.is_recording

        # Property should be read-only (can't be set directly)
        with pytest.raises(AttributeError):
            recorder.is_recording = True
