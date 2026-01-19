"""
Local Transcriber Module
Local speech-to-text transcription using whisper.cpp via pywhispercpp.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from pywhispercpp.model import Model

from context_aware_whisper.exceptions import LocalTranscriptionError


class LocalTranscriber:
    """Transcribes audio locally using whisper.cpp."""

    AVAILABLE_MODELS = [
        "tiny", "tiny.en",
        "base", "base.en",
        "small", "small.en",
        "medium", "medium.en",
        "large-v1", "large-v2", "large-v3"
    ]

    def __init__(
        self,
        model_name: str = "base.en",
        models_dir: Optional[str] = None
    ):
        """
        Initialize local transcriber with whisper.cpp.

        Args:
            model_name: Whisper model to use (e.g., "base.en", "small.en")
            models_dir: Directory for model files. Defaults to ~/.cache/whisper/
        """
        self.model_name = model_name
        self.models_dir = models_dir or os.path.expanduser("~/.cache/whisper")
        self._model: Optional[Model] = None

        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown model: {model_name}. "
                f"Available models: {', '.join(self.AVAILABLE_MODELS)}"
            )

    def _ensure_model_loaded(self) -> None:
        """Load the model if not already loaded."""
        if self._model is None:
            try:
                Path(self.models_dir).mkdir(parents=True, exist_ok=True)
                self._model = Model(
                    self.model_name,
                    models_dir=self.models_dir
                )
            except Exception as e:
                raise LocalTranscriptionError(
                    f"Failed to load whisper model '{self.model_name}': {e}"
                )

    def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """
        Transcribe audio to text locally.

        Args:
            audio_bytes: WAV audio file as bytes (16kHz, mono, 16-bit)
            language: Language code (default None, uses model default)

        Returns:
            Transcribed text string.

        Raises:
            LocalTranscriptionError: If transcription fails.
        """
        if not audio_bytes:
            return ""

        self._ensure_model_loaded()

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                segments = self._model.transcribe(temp_path)
                text = " ".join(
                    segment.text.strip()
                    for segment in segments
                    if segment.text.strip()
                )
                return text.strip()

            finally:
                os.unlink(temp_path)

        except LocalTranscriptionError:
            raise
        except Exception as e:
            raise LocalTranscriptionError(f"Transcription failed: {e}")

    def is_model_downloaded(self) -> bool:
        """Check if the configured model is available locally."""
        model_path = Path(self.models_dir) / f"ggml-{self.model_name}.bin"
        return model_path.exists()

    def download_model(self, show_progress: bool = True) -> None:
        """
        Download the configured model if not present.

        Args:
            show_progress: Whether to show download progress
        """
        if self.is_model_downloaded():
            print(f"Model '{self.model_name}' already downloaded.")
            return

        print(f"Downloading model '{self.model_name}'...")
        self._ensure_model_loaded()
        print(f"Model '{self.model_name}' downloaded successfully.")

    def get_model_path(self) -> Path:
        """Get the path to the model file."""
        return Path(self.models_dir) / f"ggml-{self.model_name}.bin"

    @property
    def model_loaded(self) -> bool:
        """Whether the model is currently loaded in memory."""
        return self._model is not None

    def unload_model(self) -> None:
        """Unload model from memory to free RAM."""
        self._model = None
