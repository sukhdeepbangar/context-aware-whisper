"""
Tests for the Configuration Module

Comprehensive tests for Config class including:
- Loading from environment variables
- Validation of all configuration values
- New UI configuration options (ui_enabled, ui_position, history_enabled)
- Property-based tests for configuration ranges
"""

import pytest
import os
from unittest.mock import patch

from hypothesis import given, strategies as st


class TestConfigFromEnv:
    """Tests for Config.from_env() environment loading."""

    def test_from_env_requires_api_key_for_groq(self, monkeypatch):
        """from_env() raises error without GROQ_API_KEY when transcriber is groq."""
        # Remove the key from the environment
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        # Set transcriber to groq (which requires API key)
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "groq")

        # Mock load_dotenv to prevent it from reloading .env
        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            with pytest.raises(ValueError) as exc_info:
                Config.from_env()

            assert "GROQ_API_KEY" in str(exc_info.value)

    def test_from_env_no_api_key_ok_for_local(self, monkeypatch):
        """from_env() works without GROQ_API_KEY when transcriber is local (default)."""
        # Remove the key from the environment
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        # Local is now default, so no need to set it explicitly
        monkeypatch.delenv("HANDFREE_TRANSCRIBER", raising=False)

        # Mock load_dotenv to prevent it from reloading .env
        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.transcriber == "local"
            assert config.groq_api_key is None

    def test_from_env_loads_api_key(self, monkeypatch):
        """from_env() loads GROQ_API_KEY correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key-12345")

        from handfree.config import Config

        config = Config.from_env()
        assert config.groq_api_key == "test-api-key-12345"

    def test_from_env_default_values(self, monkeypatch):
        """from_env() uses correct defaults when env vars not set."""
        # Clear all optional env vars (no GROQ_API_KEY needed since local is default)
        for var in ["GROQ_API_KEY", "HANDFREE_LANGUAGE", "HANDFREE_TYPE_DELAY", "HANDFREE_SAMPLE_RATE",
                    "HANDFREE_USE_PASTE", "HANDFREE_SKIP_CLIPBOARD", "HANDFREE_UI_ENABLED", "HANDFREE_UI_POSITION",
                    "HANDFREE_HISTORY_ENABLED", "HANDFREE_HISTORY_MAX", "HANDFREE_HOTKEY",
                    "HANDFREE_TRANSCRIBER", "HANDFREE_WHISPER_MODEL", "HANDFREE_MODELS_DIR"]:
            monkeypatch.delenv(var, raising=False)

        from handfree.config import Config
        import os

        config = Config.from_env()

        assert config.transcriber == "local"  # Default is now local
        assert config.whisper_model == "base.en"
        assert config.models_dir == os.path.expanduser("~/.cache/whisper")
        assert config.language is None
        assert config.type_delay == 0.0
        assert config.sample_rate == 16000
        assert config.use_paste is False
        assert config.skip_clipboard is False  # Default is False (fast clipboard paste)
        assert config.ui_enabled is True
        assert config.ui_position == "top-center"
        assert config.history_enabled is True
        assert config.history_max_entries == 1000
        assert config.custom_hotkey is None

    def test_from_env_loads_all_settings(self, monkeypatch):
        """from_env() loads all environment settings correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "my-api-key")
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "groq")
        monkeypatch.setenv("HANDFREE_WHISPER_MODEL", "small.en")
        monkeypatch.setenv("HANDFREE_MODELS_DIR", "/custom/models")
        monkeypatch.setenv("HANDFREE_LANGUAGE", "es")
        monkeypatch.setenv("HANDFREE_TYPE_DELAY", "0.05")
        monkeypatch.setenv("HANDFREE_SAMPLE_RATE", "22050")
        monkeypatch.setenv("HANDFREE_USE_PASTE", "true")
        monkeypatch.setenv("HANDFREE_UI_ENABLED", "false")
        monkeypatch.setenv("HANDFREE_UI_POSITION", "bottom-right")
        monkeypatch.setenv("HANDFREE_HISTORY_ENABLED", "false")
        monkeypatch.setenv("HANDFREE_HISTORY_MAX", "500")
        monkeypatch.setenv("HANDFREE_HOTKEY", "ctrl+shift+r")

        from handfree.config import Config

        config = Config.from_env()

        assert config.groq_api_key == "my-api-key"
        assert config.transcriber == "groq"
        assert config.whisper_model == "small.en"
        assert config.models_dir == "/custom/models"
        assert config.language == "es"
        assert config.type_delay == 0.05
        assert config.sample_rate == 22050
        assert config.use_paste is True
        assert config.ui_enabled is False
        assert config.ui_position == "bottom-right"
        assert config.history_enabled is False
        assert config.history_max_entries == 500
        assert config.custom_hotkey == "ctrl+shift+r"


class TestConfigBooleanParsing:
    """Tests for boolean environment variable parsing."""

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("No", False),
        ("NO", False),
        ("", False),  # Empty string is False for use_paste default
        ("anything", False),  # Unrecognized values are False
    ])
    def test_use_paste_boolean_parsing(self, value, expected, monkeypatch):
        """HANDFREE_USE_PASTE is parsed correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_USE_PASTE", value)

        from handfree.config import Config

        config = Config.from_env()
        assert config.use_paste is expected

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
    ])
    def test_ui_enabled_boolean_parsing(self, value, expected, monkeypatch):
        """HANDFREE_UI_ENABLED is parsed correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_UI_ENABLED", value)

        from handfree.config import Config

        config = Config.from_env()
        assert config.ui_enabled is expected

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("no", False),
    ])
    def test_history_enabled_boolean_parsing(self, value, expected, monkeypatch):
        """HANDFREE_HISTORY_ENABLED is parsed correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_HISTORY_ENABLED", value)

        from handfree.config import Config

        config = Config.from_env()
        assert config.history_enabled is expected

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("", False),  # Empty string defaults to False
    ])
    def test_skip_clipboard_boolean_parsing(self, value, expected, monkeypatch):
        """HANDFREE_SKIP_CLIPBOARD is parsed correctly."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)  # Not needed for local transcriber
        monkeypatch.setenv("HANDFREE_SKIP_CLIPBOARD", value)

        from handfree.config import Config

        config = Config.from_env()
        assert config.skip_clipboard is expected


class TestConfigUIPosition:
    """Tests for UI position configuration."""

    @pytest.mark.parametrize("position", [
        "top-center",
        "top-right",
        "top-left",
        "bottom-center",
        "bottom-right",
        "bottom-left",
    ])
    def test_valid_ui_positions(self, position, monkeypatch):
        """All valid UI positions are accepted."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_UI_POSITION", position)

        from handfree.config import Config

        config = Config.from_env()
        config.validate()  # Should not raise

        assert config.ui_position == position

    @pytest.mark.parametrize("position", [
        "TOP-CENTER",  # Uppercase should be normalized
        "Top-Center",
        "TOP-RIGHT",
    ])
    def test_ui_position_case_insensitive(self, position, monkeypatch):
        """UI position is case-insensitive."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_UI_POSITION", position)

        from handfree.config import Config

        config = Config.from_env()
        # Position should be lowercased
        assert config.ui_position == position.lower()

    @pytest.mark.parametrize("invalid_position", [
        "center",
        "middle",
        "top",
        "bottom",
        "left",
        "right",
        "invalid",
        "",  # Empty string
    ])
    def test_invalid_ui_positions_rejected(self, invalid_position, monkeypatch):
        """Invalid UI positions are rejected during validation."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_UI_POSITION", invalid_position)

        from handfree.config import Config

        config = Config.from_env()

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_UI_POSITION" in str(exc_info.value)


class TestConfigValidation:
    """Tests for Config.validate() method."""

    def test_validate_returns_warnings_list(self, monkeypatch):
        """validate() returns list of warnings."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        from handfree.config import Config

        config = Config(groq_api_key="test-key")
        result = config.validate()

        assert isinstance(result, list)

    def test_validate_negative_type_delay(self, monkeypatch):
        """validate() rejects negative type delay."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", type_delay=-0.1)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_TYPE_DELAY" in str(exc_info.value)

    def test_validate_zero_sample_rate(self, monkeypatch):
        """validate() rejects zero sample rate."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=0)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_SAMPLE_RATE" in str(exc_info.value)

    def test_validate_negative_sample_rate(self, monkeypatch):
        """validate() rejects negative sample rate."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=-16000)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_SAMPLE_RATE" in str(exc_info.value)

    def test_validate_zero_history_max(self, monkeypatch):
        """validate() rejects zero history_max_entries."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", history_max_entries=0)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_HISTORY_MAX" in str(exc_info.value)

    def test_validate_negative_history_max(self, monkeypatch):
        """validate() rejects negative history_max_entries."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", history_max_entries=-100)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_HISTORY_MAX" in str(exc_info.value)

    def test_validate_warns_unusual_sample_rate(self, monkeypatch, capsys):
        """validate() warns for unusual sample rate."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=12345)
        warnings = config.validate()

        assert len(warnings) == 1
        assert "12345" in warnings[0]
        assert "sample rate" in warnings[0].lower()

    def test_validate_warns_large_history_max(self, monkeypatch):
        """validate() warns for very large history_max_entries."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", history_max_entries=200000)
        warnings = config.validate()

        assert len(warnings) == 1
        assert "200000" in warnings[0]
        assert "performance" in warnings[0].lower()

    @pytest.mark.parametrize("rate", [8000, 16000, 22050, 44100, 48000])
    def test_validate_standard_sample_rates_no_warning(self, rate):
        """validate() doesn't warn for standard sample rates."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=rate)
        warnings = config.validate()

        assert len(warnings) == 0


class TestConfigDataclass:
    """Tests for Config dataclass structure."""

    def test_config_has_all_required_fields(self):
        """Config has all required fields."""
        from handfree.config import Config
        import dataclasses

        fields = {f.name for f in dataclasses.fields(Config)}

        required_fields = {
            "groq_api_key",
            "transcriber",
            "whisper_model",
            "models_dir",
            "language",
            "type_delay",
            "sample_rate",
            "use_paste",
            "ui_enabled",
            "ui_position",
            "history_enabled",
            "history_max_entries",
            "custom_hotkey",
        }

        assert required_fields.issubset(fields), f"Missing fields: {required_fields - fields}"

    def test_config_direct_instantiation(self):
        """Config can be instantiated directly with values."""
        from handfree.config import Config

        config = Config(
            groq_api_key="test-key",
            transcriber="groq",
            whisper_model="small.en",
            models_dir="/custom/models",
            language="en",
            type_delay=0.1,
            sample_rate=44100,
            use_paste=True,
            ui_enabled=False,
            ui_position="bottom-right",
            history_enabled=False,
            history_max_entries=500,
            custom_hotkey="ctrl+alt+r",
        )

        assert config.groq_api_key == "test-key"
        assert config.transcriber == "groq"
        assert config.whisper_model == "small.en"
        assert config.models_dir == "/custom/models"
        assert config.language == "en"
        assert config.type_delay == 0.1
        assert config.sample_rate == 44100
        assert config.use_paste is True
        assert config.ui_enabled is False
        assert config.ui_position == "bottom-right"
        assert config.history_enabled is False
        assert config.history_max_entries == 500
        assert config.custom_hotkey == "ctrl+alt+r"


class TestValidUIPositions:
    """Tests for VALID_UI_POSITIONS constant."""

    def test_valid_positions_exported(self):
        """VALID_UI_POSITIONS is exported from config module."""
        from handfree.config import VALID_UI_POSITIONS

        assert isinstance(VALID_UI_POSITIONS, list)
        assert len(VALID_UI_POSITIONS) == 6

    def test_valid_positions_contains_expected_values(self):
        """VALID_UI_POSITIONS contains all expected values."""
        from handfree.config import VALID_UI_POSITIONS

        expected = [
            "top-center", "top-right", "top-left",
            "bottom-center", "bottom-right", "bottom-left"
        ]

        assert set(VALID_UI_POSITIONS) == set(expected)


class TestTranscriberConfiguration:
    """Tests for transcriber selection configuration."""

    def test_default_transcriber_is_local(self, monkeypatch):
        """Default transcriber is 'local'."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("HANDFREE_TRANSCRIBER", raising=False)

        from handfree.config import Config

        config = Config.from_env()
        assert config.transcriber == "local"

    def test_can_set_transcriber_to_local(self, monkeypatch):
        """Transcriber can be set to 'local'."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "local")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.transcriber == "local"

    def test_local_transcriber_does_not_require_api_key(self, monkeypatch):
        """Local transcriber doesn't require GROQ_API_KEY."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "local")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.groq_api_key is None
            config.validate()  # Should not raise

    def test_groq_transcriber_requires_api_key(self, monkeypatch):
        """Groq transcriber requires GROQ_API_KEY."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            with pytest.raises(ValueError) as exc_info:
                Config.from_env()

            assert "GROQ_API_KEY" in str(exc_info.value)

    def test_transcriber_case_insensitive(self, monkeypatch):
        """Transcriber setting is case-insensitive."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "LOCAL")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.transcriber == "local"

    def test_invalid_transcriber_fails_validation(self, monkeypatch):
        """Invalid transcriber value fails validation."""
        from handfree.config import Config

        config = Config(transcriber="invalid", groq_api_key="test")

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_TRANSCRIBER" in str(exc_info.value)

    @pytest.mark.parametrize("transcriber", ["groq", "local"])
    def test_valid_transcriber_values(self, transcriber, monkeypatch):
        """Valid transcriber values pass validation."""
        from handfree.config import Config

        # groq requires api_key, local doesn't
        api_key = "test-key" if transcriber == "groq" else None
        config = Config(transcriber=transcriber, groq_api_key=api_key)
        config.validate()  # Should not raise


class TestWhisperModelConfiguration:
    """Tests for whisper model configuration (local transcription)."""

    def test_default_whisper_model(self, monkeypatch):
        """Default whisper model is 'base.en'."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "local")
        monkeypatch.delenv("HANDFREE_WHISPER_MODEL", raising=False)

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.whisper_model == "base.en"

    def test_can_set_whisper_model(self, monkeypatch):
        """Whisper model can be set via environment variable."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "local")
        monkeypatch.setenv("HANDFREE_WHISPER_MODEL", "small.en")

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.whisper_model == "small.en"

    @pytest.mark.parametrize("model", [
        "tiny", "tiny.en",
        "base", "base.en",
        "small", "small.en",
        "medium", "medium.en",
        "large-v1", "large-v2", "large-v3"
    ])
    def test_valid_whisper_models(self, model):
        """All valid whisper models pass validation."""
        from handfree.config import Config

        config = Config(transcriber="local", whisper_model=model)
        config.validate()  # Should not raise

    def test_invalid_whisper_model_fails_validation(self):
        """Invalid whisper model fails validation."""
        from handfree.config import Config

        config = Config(transcriber="local", whisper_model="invalid-model")

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_WHISPER_MODEL" in str(exc_info.value)

    def test_whisper_model_not_validated_for_groq(self):
        """Whisper model validation is skipped for groq transcriber."""
        from handfree.config import Config

        # Invalid model but using groq - should not fail
        config = Config(
            transcriber="groq",
            groq_api_key="test-key",
            whisper_model="invalid-model"
        )
        config.validate()  # Should not raise


class TestModelsDirectory:
    """Tests for models directory configuration."""

    def test_default_models_dir(self, monkeypatch):
        """Default models directory is ~/.cache/whisper."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "local")
        monkeypatch.delenv("HANDFREE_MODELS_DIR", raising=False)

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config
            import os

            config = Config.from_env()
            assert config.models_dir == os.path.expanduser("~/.cache/whisper")

    def test_can_set_models_dir(self, monkeypatch):
        """Models directory can be set via environment variable."""
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "local")
        monkeypatch.setenv("HANDFREE_MODELS_DIR", "/custom/path/models")

        with patch('handfree.config.load_dotenv'):
            from handfree.config import Config

            config = Config.from_env()
            assert config.models_dir == "/custom/path/models"


class TestValidTranscribers:
    """Tests for VALID_TRANSCRIBERS constant."""

    def test_valid_transcribers_exported(self):
        """VALID_TRANSCRIBERS is exported from config module."""
        from handfree.config import VALID_TRANSCRIBERS

        assert isinstance(VALID_TRANSCRIBERS, list)
        assert len(VALID_TRANSCRIBERS) == 2

    def test_valid_transcribers_contains_expected_values(self):
        """VALID_TRANSCRIBERS contains expected values."""
        from handfree.config import VALID_TRANSCRIBERS

        assert set(VALID_TRANSCRIBERS) == {"groq", "local"}


class TestValidWhisperModels:
    """Tests for VALID_WHISPER_MODELS constant."""

    def test_valid_whisper_models_exported(self):
        """VALID_WHISPER_MODELS is exported from config module."""
        from handfree.config import VALID_WHISPER_MODELS

        assert isinstance(VALID_WHISPER_MODELS, list)
        assert len(VALID_WHISPER_MODELS) == 11

    def test_valid_whisper_models_contains_expected_values(self):
        """VALID_WHISPER_MODELS contains all expected models."""
        from handfree.config import VALID_WHISPER_MODELS

        expected = [
            "tiny", "tiny.en",
            "base", "base.en",
            "small", "small.en",
            "medium", "medium.en",
            "large-v1", "large-v2", "large-v3"
        ]

        assert set(VALID_WHISPER_MODELS) == set(expected)


class TestConfigPropertyBased:
    """Property-based tests for configuration validation."""

    @given(delay=st.floats(min_value=0.0, max_value=100.0, allow_nan=False))
    def test_valid_type_delays_pass_validation(self, delay):
        """Non-negative type delays pass validation."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", type_delay=delay)
        config.validate()  # Should not raise

    @given(delay=st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False))
    def test_negative_type_delays_fail_validation(self, delay):
        """Negative type delays fail validation."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", type_delay=delay)

        with pytest.raises(ValueError):
            config.validate()

    @given(rate=st.integers(min_value=1, max_value=192000))
    def test_positive_sample_rates_pass_validation(self, rate):
        """Positive sample rates pass validation (may warn for unusual rates)."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=rate)
        config.validate()  # Should not raise (may return warnings)

    @given(rate=st.integers(max_value=0))
    def test_non_positive_sample_rates_fail_validation(self, rate):
        """Non-positive sample rates fail validation."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=rate)

        with pytest.raises(ValueError):
            config.validate()

    @given(max_entries=st.integers(min_value=1, max_value=100000))
    def test_valid_history_max_pass_validation(self, max_entries):
        """Valid history max entries pass validation."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", history_max_entries=max_entries)
        config.validate()  # Should not raise

    @given(max_entries=st.integers(max_value=0))
    def test_invalid_history_max_fail_validation(self, max_entries):
        """Non-positive history max entries fail validation."""
        from handfree.config import Config

        config = Config(groq_api_key="test-key", history_max_entries=max_entries)

        with pytest.raises(ValueError):
            config.validate()
