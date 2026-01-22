"""
Transcriber Module
Sends audio to Groq Whisper API and returns transcription.
"""

import os
import time
from typing import Optional

from groq import Groq

from context_aware_whisper.exceptions import TranscriptionError


class Transcriber:
    """Transcribes audio using Groq Whisper API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize transcriber with Groq API key.

        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        self.client = Groq(api_key=self.api_key)
        self.model = "whisper-large-v3-turbo"

    def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        Transcribe audio to text.

        Args:
            audio_bytes: WAV audio file as bytes
            language: Optional language code (e.g., "en"). Auto-detected if None.
            prompt: Optional vocabulary hints (comma-separated words/phrases).
            max_retries: Maximum number of retry attempts on failure.

        Returns:
            Transcribed text string.

        Raises:
            TranscriptionError: If API call fails after retries.
        """
        if not audio_bytes:
            return ""

        last_error = None
        for attempt in range(max_retries):
            try:
                transcription = self.client.audio.transcriptions.create(
                    file=("audio.wav", audio_bytes),
                    model=self.model,
                    language=language,
                    prompt=prompt,
                    response_format="text"
                )
                # The response is the text directly when response_format="text"
                return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()

            except Exception as e:
                last_error = e
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    # Other error - retry immediately
                    print(f"Transcription error (attempt {attempt + 1}): {e}")

        raise TranscriptionError(f"Transcription failed after {max_retries} attempts: {last_error}")
