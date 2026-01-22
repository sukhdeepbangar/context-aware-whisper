"""
Vocabulary Module
Loads custom vocabulary hints from user file for transcription.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_VOCABULARY_PATH = "~/.config/context-aware-whisper/vocabulary.txt"


def get_vocabulary_path() -> Path:
    """Get the vocabulary file path from env var or default."""
    custom_path = os.environ.get("CAW_VOCABULARY_FILE")
    if custom_path:
        return Path(custom_path).expanduser()
    return Path(DEFAULT_VOCABULARY_PATH).expanduser()


def load_vocabulary(file_path: Optional[Path] = None) -> Optional[str]:
    """
    Load vocabulary hints from file.

    Reads fresh every call (no caching) so user can edit anytime.

    Args:
        file_path: Path to vocabulary file. Uses default if None.

    Returns:
        Comma-separated vocabulary string, or None if file doesn't exist.
    """
    path = file_path or get_vocabulary_path()

    if not path.exists():
        return None

    try:
        words = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                words.append(line)

        if not words:
            return None

        prompt = ", ".join(words)
        logger.debug(f"Loaded vocabulary ({len(words)} terms)")
        return prompt

    except Exception as e:
        logger.warning(f"Failed to read vocabulary file {path}: {e}")
        return None
