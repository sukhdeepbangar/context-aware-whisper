"""
Tests for transcriber integration in main.py.

Tests the get_transcriber() factory function and transcriber selection logic.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from context_aware_whisper.config import Config
from context_aware_whisper.transcriber import Transcriber
from context_aware_whisper.local_transcriber import LocalTranscriber
from main import get_transcriber


class TestGetTranscriberFactory:
    """Tests for the get_transcriber() factory function."""

    def test_groq_transcriber_selected_for_groq_config(self):
        """get_transcriber returns Transcriber for groq config."""
        config = Config(
            groq_api_key="test-api-key",
            transcriber="groq"
        )

        transcriber, mode = get_transcriber(config)

        assert isinstance(transcriber, Transcriber)
        assert mode == "groq (cloud)"

    def test_local_transcriber_selected_for_local_config(self):
        """get_transcriber returns LocalTranscriber for local config when model exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake model file
            model_path = Path(temp_dir) / "ggml-base.en.bin"
            model_path.write_bytes(b"fake model data")

            config = Config(
                transcriber="local",
                whisper_model="base.en",
                models_dir=temp_dir
            )

            transcriber, mode = get_transcriber(config)

            assert isinstance(transcriber, LocalTranscriber)
            assert "local" in mode
            assert "base.en" in mode

    def test_fallback_to_groq_when_model_missing_with_api_key(self):
        """get_transcriber falls back to Groq when local model missing and API key available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # No model file exists
            config = Config(
                groq_api_key="test-api-key",
                transcriber="local",
                whisper_model="base.en",
                models_dir=temp_dir
            )

            transcriber, mode = get_transcriber(config)

            assert isinstance(transcriber, Transcriber)
            assert "fallback" in mode

    @patch('main.LocalTranscriber')
    def test_model_download_triggered_when_no_fallback(self, mock_local_class):
        """get_transcriber triggers model download when no fallback available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_local = MagicMock()
            mock_local.is_model_downloaded.return_value = False
            mock_local_class.return_value = mock_local

            config = Config(
                groq_api_key=None,  # No fallback
                transcriber="local",
                whisper_model="base.en",
                models_dir=temp_dir
            )

            transcriber, mode = get_transcriber(config)

            mock_local.download_model.assert_called_once()

    def test_mode_string_contains_model_name_for_local(self):
        """Mode string includes model name for local transcription."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake model file
            model_path = Path(temp_dir) / "ggml-tiny.en.bin"
            model_path.write_bytes(b"fake model data")

            config = Config(
                transcriber="local",
                whisper_model="tiny.en",
                models_dir=temp_dir
            )

            transcriber, mode = get_transcriber(config)

            assert "tiny.en" in mode
            assert "whisper.cpp" in mode

    def test_mode_string_for_groq(self):
        """Mode string is correct for groq transcription."""
        config = Config(
            groq_api_key="test-api-key",
            transcriber="groq"
        )

        transcriber, mode = get_transcriber(config)

        assert mode == "groq (cloud)"


class TestTranscriberIntegrationProperties:
    """Property-based tests for transcriber integration."""

    @pytest.mark.parametrize("model_name", [
        "tiny", "tiny.en", "base", "base.en", "small", "small.en"
    ])
    def test_local_transcriber_with_various_models(self, model_name):
        """LocalTranscriber can be created with various model names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake model file
            model_path = Path(temp_dir) / f"ggml-{model_name}.bin"
            model_path.write_bytes(b"fake model data")

            config = Config(
                transcriber="local",
                whisper_model=model_name,
                models_dir=temp_dir
            )

            transcriber, mode = get_transcriber(config)

            assert isinstance(transcriber, LocalTranscriber)
            assert model_name in mode

    @pytest.mark.parametrize("transcriber_type", ["groq", "local"])
    def test_transcriber_type_selection(self, transcriber_type):
        """Transcriber type selection works for all valid types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            if transcriber_type == "local":
                # Create fake model file
                model_path = Path(temp_dir) / "ggml-base.en.bin"
                model_path.write_bytes(b"fake model data")

            config = Config(
                groq_api_key="test-api-key" if transcriber_type == "groq" else None,
                transcriber=transcriber_type,
                whisper_model="base.en",
                models_dir=temp_dir
            )

            transcriber, mode = get_transcriber(config)

            if transcriber_type == "groq":
                assert isinstance(transcriber, Transcriber)
            else:
                assert isinstance(transcriber, LocalTranscriber)


class TestFallbackLogic:
    """Tests for fallback logic when local model is not available."""

    def test_fallback_prints_warning(self, capsys):
        """Fallback prints warning message about model not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                groq_api_key="test-api-key",
                transcriber="local",
                whisper_model="base.en",
                models_dir=temp_dir
            )

            get_transcriber(config)

            captured = capsys.readouterr()
            assert "not found" in captured.out.lower() or "warning" in captured.out.lower()

    def test_fallback_prints_download_instructions(self, capsys):
        """Fallback prints instructions for downloading model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                groq_api_key="test-api-key",
                transcriber="local",
                whisper_model="base.en",
                models_dir=temp_dir
            )

            get_transcriber(config)

            captured = capsys.readouterr()
            assert "download" in captured.out.lower()


class TestConfigTranscriberValidation:
    """Tests for config validation related to transcriber settings."""

    def test_config_accepts_groq_transcriber(self):
        """Config accepts 'groq' as transcriber value."""
        config = Config(
            groq_api_key="test-key",
            transcriber="groq"
        )
        config.validate()  # Should not raise

    def test_config_accepts_local_transcriber(self):
        """Config accepts 'local' as transcriber value."""
        config = Config(
            transcriber="local",
            whisper_model="base.en"
        )
        config.validate()  # Should not raise

    def test_config_rejects_invalid_transcriber(self):
        """Config rejects invalid transcriber values."""
        config = Config(
            groq_api_key="test-key",
            transcriber="invalid"
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "CAW_TRANSCRIBER" in str(exc_info.value)

    def test_config_requires_groq_key_for_groq_transcriber(self):
        """Config requires GROQ_API_KEY when transcriber is groq."""
        config = Config(
            groq_api_key=None,
            transcriber="groq"
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "GROQ_API_KEY" in str(exc_info.value)

    def test_config_validates_whisper_model_for_local(self):
        """Config validates whisper model name for local transcription."""
        config = Config(
            transcriber="local",
            whisper_model="invalid-model"
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "CAW_WHISPER_MODEL" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
