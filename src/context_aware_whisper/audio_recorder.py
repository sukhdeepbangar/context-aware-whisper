"""
Audio Recorder Module
Captures audio from microphone and stores in memory buffer.
"""

import io
import threading
from collections import deque
from typing import Optional

import numpy as np
import sounddevice as sd
from scipy.io import wavfile


class AudioRecorder:
    """Records audio from microphone to memory buffer."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio recorder.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Whisper)
            channels: Number of audio channels (default 1 for mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer: deque = deque()
        self._lock = threading.Lock()
        self.stream: Optional[sd.InputStream] = None
        self._is_recording = False

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info, status) -> None:
        """Callback for audio stream - appends chunks to buffer."""
        if status:
            print(f"Audio callback status: {status}")
        with self._lock:
            self.buffer.append(indata.copy())

    def start_recording(self) -> None:
        """Begin capturing audio from default input device."""
        if self._is_recording:
            return

        with self._lock:
            self.buffer.clear()
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            callback=self._audio_callback
        )
        self.stream.start()
        self._is_recording = True

    def stop_recording(self) -> bytes:
        """
        Stop recording and return audio as WAV bytes.

        Returns:
            WAV file contents as bytes, ready for API upload.
        """
        if not self._is_recording:
            return b''

        self.stream.stop()
        self.stream.close()
        self.stream = None
        self._is_recording = False

        with self._lock:
            if not self.buffer:
                return b''

            # Combine all chunks
            audio_data = np.concatenate(list(self.buffer))

        # Encode as WAV in memory
        wav_buffer = io.BytesIO()
        wavfile.write(wav_buffer, self.sample_rate, audio_data)
        wav_buffer.seek(0)

        return wav_buffer.getvalue()

    def get_duration(self) -> float:
        """Return current recording duration in seconds."""
        with self._lock:
            if not self.buffer:
                return 0.0
            total_samples = sum(chunk.shape[0] for chunk in self.buffer)
            return total_samples / self.sample_rate

    def clear_buffer(self) -> None:
        """Discard any recorded audio."""
        with self._lock:
            self.buffer.clear()

    @property
    def is_recording(self) -> bool:
        """Whether recording is currently active."""
        return self._is_recording
