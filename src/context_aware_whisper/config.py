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

# Valid text cleanup modes
VALID_CLEANUP_MODES = ["off", "light", "standard", "aggressive"]


@dataclass
class Config:
    """Application configuration from environment variables."""

    # Transcriber backend - Required if groq, Optional if local
    groq_api_key: Optional[str] = None

    # Transcriber selection
    transcriber: str = "groq"  # "groq" or "local"

    # Local transcription settings (whisper.cpp)
    whisper_model: str = "base.en"
    models_dir: str = field(default_factory=lambda: os.path.expanduser("~/.cache/whisper"))

    # Optional with defaults - Audio/Transcription
    language: Optional[str] = None  # Auto-detect if not set
    type_delay: float = 0.0
    sample_rate: int = 16000
    use_paste: bool = False
    skip_clipboard: bool = False  # If True, use slow keystroke typing instead of fast clipboard paste

    # Optional with defaults - UI
    ui_enabled: bool = True
    ui_position: str = "top-center"
    history_enabled: bool = True
    history_max_entries: int = 1000

    # Optional - Custom hotkey (e.g., "ctrl+shift+r")
    custom_hotkey: Optional[str] = None

    # Text cleanup settings
    text_cleanup: str = "aggressive"  # off, light, standard, aggressive
    preserve_intentional: bool = True

    # Local LLM settings (for aggressive text cleanup on Apple Silicon)
    local_model: str = "mlx-community/Phi-3-mini-4k-instruct-4bit"

    # Vocabulary file path (optional override)
    vocabulary_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Environment Variables:
            GROQ_API_KEY: Required when CAW_TRANSCRIBER=groq. Groq API key.
            CAW_TRANSCRIBER: Optional. Transcription backend: "groq" or "local" (default: local).
            CAW_WHISPER_MODEL: Optional. Whisper model for local transcription (default: base.en).
            CAW_MODELS_DIR: Optional. Directory for whisper models (default: ~/.cache/whisper).
            CAW_LANGUAGE: Optional. Language code for transcription (auto-detect if not set).
            CAW_TYPE_DELAY: Optional. Delay between keystrokes in seconds (default: 0).
            CAW_SAMPLE_RATE: Optional. Audio sample rate in Hz (default: 16000).
            CAW_USE_PASTE: Optional. Use clipboard paste instead of typing (default: false).
            CAW_SKIP_CLIPBOARD: Optional. Don't copy to clipboard, only type (default: false).
            CAW_UI_ENABLED: Optional. Enable visual UI indicator (default: true).
            CAW_UI_POSITION: Optional. Indicator position: top-center, top-right, top-left,
                                  bottom-center, bottom-right, bottom-left (default: top-center).
            CAW_HISTORY_ENABLED: Optional. Enable transcription history (default: true).
            CAW_HISTORY_MAX: Optional. Maximum history entries (default: 1000).
            CAW_HOTKEY: Optional. Custom hotkey (e.g., "ctrl+shift+r"). Platform default if not set.
            CAW_TEXT_CLEANUP: Optional. Text cleanup mode: off, light, standard, aggressive (default: standard).
            CAW_PRESERVE_INTENTIONAL: Optional. Preserve intentional patterns like emphasis (default: true).
            CAW_LOCAL_MODEL: Optional. Local MLX model for aggressive cleanup (default: mlx-community/Phi-3-mini-4k-instruct-4bit).
            CAW_VOCABULARY_FILE: Optional. Custom vocabulary file path
                                 (default: ~/.config/context-aware-whisper/vocabulary.txt).

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
        transcriber = os.environ.get("CAW_TRANSCRIBER", "local").lower()

        # Get GROQ_API_KEY (required only for groq transcriber)
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if transcriber == "groq" and not groq_api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is required when using Groq transcription.\n"
                "Set it in your .env file or export it:\n"
                "  export GROQ_API_KEY=your_key_here\n\n"
                "Or switch to local transcription:\n"
                "  export CAW_TRANSCRIBER=local"
            )

        return cls(
            groq_api_key=groq_api_key,
            transcriber=transcriber,
            whisper_model=os.environ.get("CAW_WHISPER_MODEL", "base.en"),
            models_dir=os.environ.get("CAW_MODELS_DIR", os.path.expanduser("~/.cache/whisper")),
            language=os.environ.get("CAW_LANGUAGE"),
            type_delay=float(os.environ.get("CAW_TYPE_DELAY", "0")),
            sample_rate=int(os.environ.get("CAW_SAMPLE_RATE", "16000")),
            use_paste=parse_bool(os.environ.get("CAW_USE_PASTE", ""), False),
            skip_clipboard=parse_bool(os.environ.get("CAW_SKIP_CLIPBOARD", ""), False),
            ui_enabled=parse_bool(os.environ.get("CAW_UI_ENABLED", "true"), True),
            ui_position=os.environ.get("CAW_UI_POSITION", "top-center").lower(),
            history_enabled=parse_bool(os.environ.get("CAW_HISTORY_ENABLED", "true"), True),
            history_max_entries=int(os.environ.get("CAW_HISTORY_MAX", "1000")),
            custom_hotkey=os.environ.get("CAW_HOTKEY"),
            text_cleanup=os.environ.get("CAW_TEXT_CLEANUP", "aggressive").lower(),
            preserve_intentional=parse_bool(os.environ.get("CAW_PRESERVE_INTENTIONAL", "true"), True),
            local_model=os.environ.get(
                "CAW_LOCAL_MODEL",
                "mlx-community/Phi-3-mini-4k-instruct-4bit"
            ),
            vocabulary_file=os.environ.get("CAW_VOCABULARY_FILE"),
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
                f"CAW_TRANSCRIBER must be one of: {', '.join(VALID_TRANSCRIBERS)}. "
                f"Got: {self.transcriber}"
            )

        # Validate groq_api_key is present when using groq transcriber
        if self.transcriber == "groq" and not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is required when CAW_TRANSCRIBER=groq"
            )

        # Validate whisper model (for local transcription)
        if self.transcriber == "local" and self.whisper_model not in VALID_WHISPER_MODELS:
            raise ValueError(
                f"CAW_WHISPER_MODEL must be one of: {', '.join(VALID_WHISPER_MODELS)}. "
                f"Got: {self.whisper_model}"
            )

        if self.type_delay < 0:
            raise ValueError("CAW_TYPE_DELAY must be non-negative")

        if self.sample_rate <= 0:
            raise ValueError("CAW_SAMPLE_RATE must be positive")

        valid_sample_rates = [8000, 16000, 22050, 44100, 48000]
        if self.sample_rate not in valid_sample_rates:
            warnings.append(
                f"Unusual sample rate {self.sample_rate}. "
                f"Common values are: {valid_sample_rates}"
            )

        if self.ui_position not in VALID_UI_POSITIONS:
            raise ValueError(
                f"CAW_UI_POSITION must be one of: {', '.join(VALID_UI_POSITIONS)}. "
                f"Got: {self.ui_position}"
            )

        if self.history_max_entries <= 0:
            raise ValueError("CAW_HISTORY_MAX must be positive")

        if self.history_max_entries > 100000:
            warnings.append(
                f"Large history max ({self.history_max_entries}) may impact performance"
            )

        # Validate text cleanup mode
        if self.text_cleanup not in VALID_CLEANUP_MODES:
            raise ValueError(
                f"CAW_TEXT_CLEANUP must be one of: {', '.join(VALID_CLEANUP_MODES)}. "
                f"Got: {self.text_cleanup}"
            )

        # Warn if aggressive mode (requires MLX on Apple Silicon)
        if self.text_cleanup == "aggressive":
            warnings.append(
                "CAW_TEXT_CLEANUP=aggressive requires MLX (Apple Silicon). "
                "Install with: pip install 'context-aware-whisper[local-llm]'. "
                "Will fall back to 'standard' mode if unavailable."
            )

        return warnings
