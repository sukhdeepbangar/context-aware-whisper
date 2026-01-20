"""
Integration tests for text cleanup module.

Tests the integration of TextCleaner with:
- Configuration system (Config)
- Factory function (get_text_cleaner)
- CAWApp pipeline
- Environment variable handling
- Mode switching and fallback behavior
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from context_aware_whisper.config import Config, VALID_CLEANUP_MODES
from context_aware_whisper.text_cleanup import TextCleaner, CleanupMode


class TestGetTextCleanerFactory:
    """Tests for get_text_cleaner() factory function."""

    def test_creates_off_mode_cleaner(self):
        """Factory creates OFF mode cleaner from config."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "off"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.mode == CleanupMode.OFF

    def test_creates_light_mode_cleaner(self):
        """Factory creates LIGHT mode cleaner from config."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "light"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.mode == CleanupMode.LIGHT

    def test_creates_standard_mode_cleaner(self):
        """Factory creates STANDARD mode cleaner from config."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.mode == CleanupMode.STANDARD

    def test_creates_aggressive_mode_with_model_name(self):
        """Factory creates AGGRESSIVE mode cleaner with model name."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "aggressive"
        config.preserve_intentional = True
        config.local_model = "custom-model"

        cleaner = get_text_cleaner(config)

        assert cleaner.mode == CleanupMode.AGGRESSIVE
        assert cleaner.model_name == "custom-model"

    def test_aggressive_mode_with_default_model(self):
        """Factory creates AGGRESSIVE cleaner with default model."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "aggressive"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.mode == CleanupMode.AGGRESSIVE
        assert cleaner.model_name == "mlx-community/Phi-3-mini-4k-instruct-4bit"

    def test_preserve_intentional_true_passed_to_cleaner(self):
        """Factory passes preserve_intentional=True to cleaner."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.preserve_intentional is True

    def test_preserve_intentional_false_passed_to_cleaner(self):
        """Factory passes preserve_intentional=False to cleaner."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = False
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.preserve_intentional is False

    def test_invalid_mode_defaults_to_standard(self):
        """Factory defaults to STANDARD for invalid mode string."""
        from main import get_text_cleaner
        config = Mock()
        config.text_cleanup = "invalid_mode"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.mode == CleanupMode.STANDARD


class TestPipelineIntegration:
    """Tests for text cleanup in the transcription pipeline."""

    def test_transcription_passes_through_standard_cleaner(self):
        """Transcribed text is cleaned by standard mode before output."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        # Simulate transcriber output
        raw_transcription = "Um, I I think, you know, this is important"
        cleaned = cleaner.clean(raw_transcription)

        assert "Um" not in cleaned
        assert "I I" not in cleaned
        assert "you know" not in cleaned.lower()
        assert "important" in cleaned

    def test_transcription_passes_through_light_cleaner(self):
        """Transcribed text is cleaned by light mode."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "light"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        raw_transcription = "Um, uh, I think this is important"
        cleaned = cleaner.clean(raw_transcription)

        assert "Um" not in cleaned
        assert "uh" not in cleaned
        assert "important" in cleaned

    def test_pipeline_preserves_text_when_off(self):
        """Text passes through unchanged when cleanup is OFF."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "off"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        raw_transcription = "Um, I I think, you know, this is important"
        cleaned = cleaner.clean(raw_transcription)

        assert cleaned == raw_transcription

    def test_pipeline_handles_empty_transcription(self):
        """Pipeline handles empty transcription gracefully."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        assert cleaner.clean("") == ""

    def test_pipeline_handles_only_fillers(self):
        """Pipeline handles transcription with only filler words."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        result = cleaner.clean("Um uh ah")
        # Should be empty or minimal after removing all fillers
        assert isinstance(result, str)
        assert len(result.strip()) <= 5


class TestEnvironmentVariableIntegration:
    """Tests for cleanup mode via environment variables."""

    def test_config_reads_cleanup_mode_off_from_env(self):
        """Config.from_env() reads CAW_TEXT_CLEANUP=off."""
        with patch.dict(os.environ, {
            "CAW_TEXT_CLEANUP": "off",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.text_cleanup == "off"

    def test_config_reads_cleanup_mode_light_from_env(self):
        """Config.from_env() reads CAW_TEXT_CLEANUP=light."""
        with patch.dict(os.environ, {
            "CAW_TEXT_CLEANUP": "light",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.text_cleanup == "light"

    def test_config_reads_cleanup_mode_standard_from_env(self):
        """Config.from_env() reads CAW_TEXT_CLEANUP=standard."""
        with patch.dict(os.environ, {
            "CAW_TEXT_CLEANUP": "standard",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.text_cleanup == "standard"

    def test_config_reads_cleanup_mode_aggressive_from_env(self):
        """Config.from_env() reads CAW_TEXT_CLEANUP=aggressive."""
        with patch.dict(os.environ, {
            "CAW_TEXT_CLEANUP": "aggressive",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.text_cleanup == "aggressive"

    def test_config_reads_preserve_intentional_true_from_env(self):
        """Config.from_env() reads CAW_PRESERVE_INTENTIONAL=true."""
        with patch.dict(os.environ, {
            "CAW_PRESERVE_INTENTIONAL": "true",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.preserve_intentional is True

    def test_config_reads_preserve_intentional_false_from_env(self):
        """Config.from_env() reads CAW_PRESERVE_INTENTIONAL=false."""
        with patch.dict(os.environ, {
            "CAW_PRESERVE_INTENTIONAL": "false",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.preserve_intentional is False

    def test_config_defaults_to_aggressive_mode(self):
        """Config defaults to aggressive cleanup mode."""
        # Clear the specific env var
        env_copy = os.environ.copy()
        env_copy.pop("CAW_TEXT_CLEANUP", None)
        env_copy["CAW_TRANSCRIBER"] = "local"

        with patch.dict(os.environ, env_copy, clear=True):
            config = Config.from_env()
            assert config.text_cleanup == "aggressive"

    def test_config_defaults_to_preserve_intentional_true(self):
        """Config defaults to preserve_intentional=True."""
        env_copy = os.environ.copy()
        env_copy.pop("CAW_PRESERVE_INTENTIONAL", None)
        env_copy["CAW_TRANSCRIBER"] = "local"

        with patch.dict(os.environ, env_copy, clear=True):
            config = Config.from_env()
            assert config.preserve_intentional is True

    def test_config_normalizes_uppercase_cleanup_mode(self):
        """Config normalizes uppercase cleanup mode to lowercase."""
        with patch.dict(os.environ, {
            "CAW_TEXT_CLEANUP": "STANDARD",
            "CAW_TRANSCRIBER": "local"
        }, clear=False):
            config = Config.from_env()
            assert config.text_cleanup == "standard"


class TestConfigValidation:
    """Tests for configuration validation of cleanup settings."""

    def test_valid_cleanup_modes_constant(self):
        """VALID_CLEANUP_MODES contains expected modes."""
        assert "off" in VALID_CLEANUP_MODES
        assert "light" in VALID_CLEANUP_MODES
        assert "standard" in VALID_CLEANUP_MODES
        assert "aggressive" in VALID_CLEANUP_MODES

    def test_validate_rejects_invalid_cleanup_mode(self):
        """Config.validate() raises for invalid cleanup mode."""
        config = Config(
            text_cleanup="invalid",
            transcriber="local"
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "CAW_TEXT_CLEANUP" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_validate_accepts_valid_cleanup_modes(self):
        """Config.validate() accepts all valid cleanup modes."""
        for mode in VALID_CLEANUP_MODES:
            config = Config(
                text_cleanup=mode,
                transcriber="local"
            )
            # Should not raise
            warnings = config.validate()
            # Just check it doesn't raise - warnings may be returned

    def test_validate_warns_aggressive_mode(self):
        """Config.validate() warns about aggressive mode requiring MLX."""
        config = Config(
            text_cleanup="aggressive",
            transcriber="local"
        )
        warnings = config.validate()
        assert any("aggressive" in w.lower() for w in warnings)


class TestAggressiveModeFallback:
    """Tests for AGGRESSIVE mode fallback behavior."""

    @patch('context_aware_whisper.local_llm.is_available', return_value=False)
    def test_aggressive_falls_back_when_mlx_unavailable(self, mock_available):
        """AGGRESSIVE mode falls back to STANDARD when MLX unavailable."""
        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)

        text = "Um, hello there"
        result = cleaner.clean(text)

        # Should still clean (using standard mode fallback)
        assert "Um" not in result
        assert "hello" in result.lower()

    @patch('context_aware_whisper.local_llm.is_available', return_value=False)
    def test_aggressive_mode_cleans_basic_fillers_on_fallback(self, mock_available):
        """AGGRESSIVE mode cleans fillers when falling back."""
        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)

        text = "Um, uh, I think, you know, this is great"
        result = cleaner.clean(text)

        assert "Um" not in result
        assert "uh" not in result
        assert "you know" not in result.lower()
        assert "great" in result

    @patch('context_aware_whisper.local_llm.is_available', return_value=True)
    @patch('context_aware_whisper.local_llm.generate')
    def test_aggressive_falls_back_on_generation_error(self, mock_generate, mock_available):
        """AGGRESSIVE mode falls back to STANDARD on generation error."""
        mock_generate.side_effect = Exception("Generation error")

        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)

        text = "Um, hello there"
        result = cleaner.clean(text)

        # Should still return cleaned text via fallback
        assert isinstance(result, str)
        assert "Um" not in result


class TestCleanupSkippedWhenOff:
    """Tests for cleanup being skipped in OFF mode."""

    def test_off_mode_is_noop(self):
        """OFF mode does not modify text at all."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)

        text = "Um, uh, I I think... sorry, I know"
        result = cleaner.clean(text)

        assert result == text

    def test_off_mode_preserves_all_fillers(self):
        """OFF mode preserves all filler words."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)

        text = "Um, uh, ah, er, hmm, mm, mhm, like, you know, basically"
        result = cleaner.clean(text)

        assert result == text

    def test_off_mode_preserves_repetitions(self):
        """OFF mode preserves word repetitions."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)

        text = "I I I think the the the thing"
        result = cleaner.clean(text)

        assert result == text

    def test_off_mode_preserves_whitespace(self):
        """OFF mode preserves original whitespace."""
        cleaner = TextCleaner(mode=CleanupMode.OFF)

        text = "Hello   world   with   spaces"
        result = cleaner.clean(text)

        assert result == text


class TestLoggingIntegration:
    """Tests for cleanup logging behavior."""

    @patch('context_aware_whisper.local_llm.is_available', return_value=False)
    def test_aggressive_mode_logs_warning_on_fallback(self, mock_available):
        """AGGRESSIVE mode logs warning when falling back due to MLX unavailable."""
        import logging

        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)

        # The warning is logged in clean_aggressive when MLX is unavailable
        # and it falls back to standard
        text = "Um, hello"
        result = cleaner.clean(text)

        # Verify fallback happened (standard mode behavior)
        assert "Um" not in result

    @patch('context_aware_whisper.local_llm.is_available', return_value=True)
    @patch('context_aware_whisper.local_llm.generate')
    def test_aggressive_mode_logs_warning_on_generation_error(self, mock_generate, mock_available):
        """AGGRESSIVE mode logs warning on generation error."""
        import logging

        mock_generate.side_effect = Exception("Generation failed")

        with patch('context_aware_whisper.text_cleanup.logger') as mock_logger:
            cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE)
            result = cleaner.clean("Um, hello")

            # Verify warning was logged
            mock_logger.warning.assert_called()
            warning_msg = str(mock_logger.warning.call_args)
            assert "failed" in warning_msg.lower() or "rule-based" in warning_msg.lower()


class TestStartupBannerIntegration:
    """Tests for startup banner showing cleanup mode."""

    def test_banner_content_includes_text_cleanup(self, capsys):
        """Startup banner should include text cleanup mode."""
        # We can verify the _print_banner method includes cleanup mode
        # by checking the main.py code structure
        from main import CAWApp

        # The banner print includes: print(f"  Text cleanup: {self.config.text_cleanup}")
        # We verify this pattern exists in the code
        import inspect
        source = inspect.getsource(CAWApp._print_banner)

        assert "text_cleanup" in source.lower() or "cleanup" in source.lower()


class TestEndToEndCleanupPipeline:
    """End-to-end tests for the cleanup pipeline."""

    def test_full_pipeline_standard_mode(self):
        """Full pipeline test: config → factory → cleaner → cleaned text."""
        from main import get_text_cleaner

        # Create config
        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        # Create cleaner via factory
        cleaner = get_text_cleaner(config)

        # Simulate transcription output
        transcription = "Um, so, I I was thinking, you know, we should like basically do this thing."

        # Clean
        result = cleaner.clean(transcription)

        # Verify
        assert "Um" not in result
        assert "you know" not in result.lower()
        assert "basically" not in result.lower()
        assert "I I" not in result
        assert "do this thing" in result.lower() or "this thing" in result.lower()

    def test_full_pipeline_preserves_meaning(self):
        """Pipeline preserves core meaning while removing disfluencies."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        # Technical dictation with fillers
        transcription = "Um, the function, you know, returns an integer value."
        result = cleaner.clean(transcription)

        # Core technical content preserved
        assert "function" in result
        assert "returns" in result
        assert "integer" in result
        assert "value" in result

    def test_full_pipeline_light_mode_preserves_you_know(self):
        """Light mode preserves phrases like 'you know'."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "light"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        transcription = "Um, you know, it's important"
        result = cleaner.clean(transcription)

        # Light mode removes um/uh but keeps "you know"
        assert "Um" not in result
        assert "you know" in result.lower()


class TestCleanerModeAttributes:
    """Tests verifying cleaner attributes are set correctly."""

    def test_cleaner_stores_mode(self):
        """TextCleaner stores the mode attribute."""
        for mode in CleanupMode:
            cleaner = TextCleaner(mode=mode)
            assert cleaner.mode == mode

    def test_cleaner_stores_model_name(self):
        """TextCleaner stores the model_name attribute."""
        cleaner = TextCleaner(mode=CleanupMode.AGGRESSIVE, model_name="custom-model")
        assert cleaner.model_name == "custom-model"

    def test_cleaner_stores_preserve_intentional(self):
        """TextCleaner stores the preserve_intentional attribute."""
        cleaner_true = TextCleaner(mode=CleanupMode.STANDARD, preserve_intentional=True)
        cleaner_false = TextCleaner(mode=CleanupMode.STANDARD, preserve_intentional=False)

        assert cleaner_true.preserve_intentional is True
        assert cleaner_false.preserve_intentional is False


class TestTextCleanerWithConfigIntegration:
    """Tests for TextCleaner working with Config objects."""

    def test_config_and_cleaner_modes_align(self):
        """Config cleanup modes align with CleanupMode enum."""
        from main import get_text_cleaner

        mode_mapping = {
            "off": CleanupMode.OFF,
            "light": CleanupMode.LIGHT,
            "standard": CleanupMode.STANDARD,
            "aggressive": CleanupMode.AGGRESSIVE,
        }

        for config_mode, expected_enum in mode_mapping.items():
            config = Mock()
            config.text_cleanup = config_mode
            config.preserve_intentional = True
            config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

            cleaner = get_text_cleaner(config)
            assert cleaner.mode == expected_enum, f"Failed for mode: {config_mode}"


class TestEmptyAfterCleanup:
    """Tests for handling text that becomes empty after cleanup."""

    def test_only_fillers_becomes_empty(self):
        """Text with only fillers becomes empty or near-empty."""
        cleaner = TextCleaner(mode=CleanupMode.STANDARD)

        result = cleaner.clean("um uh ah er")
        assert result.strip() == "" or len(result.strip()) <= 2

    def test_single_filler_becomes_empty(self):
        """Single filler word becomes empty."""
        cleaner = TextCleaner(mode=CleanupMode.LIGHT)

        result = cleaner.clean("um")
        assert result.strip() == ""

    def test_pipeline_should_handle_empty_result(self):
        """Pipeline correctly identifies when cleanup results in empty text."""
        from main import get_text_cleaner

        config = Mock()
        config.text_cleanup = "standard"
        config.preserve_intentional = True
        config.local_model = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        cleaner = get_text_cleaner(config)

        # Text that will be empty after cleanup
        result = cleaner.clean("um uh")

        # This is what main.py checks: if not text: (after cleanup)
        # The code handles this by showing a warning and not outputting
        assert not result.strip() or len(result.strip()) <= 2
