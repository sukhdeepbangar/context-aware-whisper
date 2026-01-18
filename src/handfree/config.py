"""
Configuration Module
Loads and validates settings from environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List

from dotenv import load_dotenv


# Valid UI position values
VALID_UI_POSITIONS = ["top-center", "top-right", "top-left", "bottom-center", "bottom-right", "bottom-left"]

# Valid transcriber backends
VALID_TRANSCRIBERS = ["groq", "local"]

# Valid whisper models (for local transcription)
VALID_WHISPER_MODELS = [
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
    "large-v1", "large-v2", "large-v3"
]


@dataclass
class Config:
    """Application configuration from environment variables."""

    # Transcriber backend - Required if groq, Optional if local
    groq_api_key: Optional[str] = None

    # Transcriber selection
    transcriber: str = "local"  # "groq" or "local"

    # Local transcription settings (whisper.cpp)
    whisper_model: str = "base.en"
    models_dir: str = field(default_factory=lambda: os.path.expanduser("~/.cache/whisper"))

    # Optional with defaults - Audio/Transcription
    language: Optional[str] = None  # Auto-detect if not set
    type_delay: float = 0.0
    sample_rate: int = 16000
    use_paste: bool = False
    skip_clipboard: bool = True  # If True, don't copy to clipboard (use keystroke typing)

    # Optional with defaults - UI
    ui_enabled: bool = True
    ui_position: str = "top-center"
    history_enabled: bool = True
    history_max_entries: int = 1000

    # Optional - Custom hotkey (e.g., "ctrl+shift+r")
    custom_hotkey: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Environment Variables:
            GROQ_API_KEY: Required when HANDFREE_TRANSCRIBER=groq. Groq API key.
            HANDFREE_TRANSCRIBER: Optional. Transcription backend: "groq" or "local" (default: local).
            HANDFREE_WHISPER_MODEL: Optional. Whisper model for local transcription (default: base.en).
            HANDFREE_MODELS_DIR: Optional. Directory for whisper models (default: ~/.cache/whisper).
            HANDFREE_LANGUAGE: Optional. Language code for transcription (auto-detect if not set).
            HANDFREE_TYPE_DELAY: Optional. Delay between keystrokes in seconds (default: 0).
            HANDFREE_SAMPLE_RATE: Optional. Audio sample rate in Hz (default: 16000).
            HANDFREE_USE_PASTE: Optional. Use clipboard paste instead of typing (default: false).
            HANDFREE_SKIP_CLIPBOARD: Optional. Don't copy to clipboard, only type (default: false).
            HANDFREE_UI_ENABLED: Optional. Enable visual UI indicator (default: true).
            HANDFREE_UI_POSITION: Optional. Indicator position: top-center, top-right, top-left,
                                  bottom-center, bottom-right, bottom-left (default: top-center).
            HANDFREE_HISTORY_ENABLED: Optional. Enable transcription history (default: true).
            HANDFREE_HISTORY_MAX: Optional. Maximum history entries (default: 1000).
            HANDFREE_HOTKEY: Optional. Custom hotkey (e.g., "ctrl+shift+r"). Platform default if not set.

        Returns:
            Config instance with loaded values.

        Raises:
            ValueError: If required configuration is missing.
        """
        load_dotenv()

        # Parse boolean environment variables
        def parse_bool(value: str, default: bool) -> bool:
            if not value:
                return default
            return value.lower() in ("true", "1", "yes")

        # Get transcriber setting first (needed to determine if GROQ_API_KEY is required)
        transcriber = os.environ.get("HANDFREE_TRANSCRIBER", "local").lower()

        # Get GROQ_API_KEY (required only for groq transcriber)
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if transcriber == "groq" and not groq_api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is required when using Groq transcription.\n"
                "Set it in your .env file or export it:\n"
                "  export GROQ_API_KEY=your_key_here\n\n"
                "Or switch to local transcription:\n"
                "  export HANDFREE_TRANSCRIBER=local"
            )

        return cls(
            groq_api_key=groq_api_key,
            transcriber=transcriber,
            whisper_model=os.environ.get("HANDFREE_WHISPER_MODEL", "base.en"),
            models_dir=os.environ.get("HANDFREE_MODELS_DIR", os.path.expanduser("~/.cache/whisper")),
            language=os.environ.get("HANDFREE_LANGUAGE"),
            type_delay=float(os.environ.get("HANDFREE_TYPE_DELAY", "0")),
            sample_rate=int(os.environ.get("HANDFREE_SAMPLE_RATE", "16000")),
            use_paste=parse_bool(os.environ.get("HANDFREE_USE_PASTE", ""), False),
            skip_clipboard=parse_bool(os.environ.get("HANDFREE_SKIP_CLIPBOARD", "true"), True),
            ui_enabled=parse_bool(os.environ.get("HANDFREE_UI_ENABLED", "true"), True),
            ui_position=os.environ.get("HANDFREE_UI_POSITION", "top-center").lower(),
            history_enabled=parse_bool(os.environ.get("HANDFREE_HISTORY_ENABLED", "true"), True),
            history_max_entries=int(os.environ.get("HANDFREE_HISTORY_MAX", "1000")),
            custom_hotkey=os.environ.get("HANDFREE_HOTKEY"),
        )

    def validate(self) -> List[str]:
        """
        Validate configuration values.

        Returns:
            List of warning messages (empty if no warnings).

        Raises:
            ValueError: If configuration values are invalid.
        """
        warnings = []

        # Validate transcriber backend
        if self.transcriber not in VALID_TRANSCRIBERS:
            raise ValueError(
                f"HANDFREE_TRANSCRIBER must be one of: {', '.join(VALID_TRANSCRIBERS)}. "
                f"Got: {self.transcriber}"
            )

        # Validate groq_api_key is present when using groq transcriber
        if self.transcriber == "groq" and not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is required when HANDFREE_TRANSCRIBER=groq"
            )

        # Validate whisper model (for local transcription)
        if self.transcriber == "local" and self.whisper_model not in VALID_WHISPER_MODELS:
            raise ValueError(
                f"HANDFREE_WHISPER_MODEL must be one of: {', '.join(VALID_WHISPER_MODELS)}. "
                f"Got: {self.whisper_model}"
            )

        if self.type_delay < 0:
            raise ValueError("HANDFREE_TYPE_DELAY must be non-negative")

        if self.sample_rate <= 0:
            raise ValueError("HANDFREE_SAMPLE_RATE must be positive")

        valid_sample_rates = [8000, 16000, 22050, 44100, 48000]
        if self.sample_rate not in valid_sample_rates:
            warnings.append(
                f"Unusual sample rate {self.sample_rate}. "
                f"Common values are: {valid_sample_rates}"
            )

        if self.ui_position not in VALID_UI_POSITIONS:
            raise ValueError(
                f"HANDFREE_UI_POSITION must be one of: {', '.join(VALID_UI_POSITIONS)}. "
                f"Got: {self.ui_position}"
            )

        if self.history_max_entries <= 0:
            raise ValueError("HANDFREE_HISTORY_MAX must be positive")

        if self.history_max_entries > 100000:
            warnings.append(
                f"Large history max ({self.history_max_entries}) may impact performance"
            )

        return warnings
