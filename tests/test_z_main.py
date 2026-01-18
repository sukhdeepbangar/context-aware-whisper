"""
Tests for the main module.

Tests cover the HandFreeApp class state machine and orchestration logic.

PERFORMANCE NOTE: Mocks are set up in conftest.py - no need to duplicate here.
"""

import pytest
from unittest.mock import Mock, patch

from handfree.config import Config
from handfree.exceptions import TranscriptionError, OutputError, LocalTranscriptionError

# Mocks are already set up in conftest.py - no need to duplicate here
from main import HandFreeApp, AppState, main, get_transcriber


def make_config(**kwargs):
    """Helper to create Config with defaults for testing."""
    defaults = {
        "groq_api_key": "test-api-key",
        "transcriber": "groq",
        "whisper_model": "base.en",
        "language": None,
        "type_delay": 0.0,
        "sample_rate": 16000,
        "use_paste": False,
        "ui_enabled": False,  # Disable UI for tests
        "ui_position": "top-center",
        "history_enabled": False,
    }
    defaults.update(kwargs)
    return Config(**defaults)


class TestAppState:
    """Tests for the AppState enum."""

    def test_app_states_exist(self):
        """Verify all expected states are defined."""
        assert AppState.IDLE is not None
        assert AppState.RECORDING is not None
        assert AppState.TRANSCRIBING is not None

    def test_states_are_distinct(self):
        """Verify states are unique."""
        states = [AppState.IDLE, AppState.RECORDING, AppState.TRANSCRIBING]
        assert len(states) == len(set(states))


class TestHandFreeAppInit:
    """Tests for HandFreeApp initialization."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_init_creates_all_modules(self, mock_output, mock_get_transcriber,
                                       mock_recorder, mock_detector):
        """HandFreeApp initializes all required modules."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config()
        app = HandFreeApp(config=config)

        mock_recorder.assert_called_once()
        mock_get_transcriber.assert_called_once_with(config)
        mock_output.assert_called_once()
        mock_detector.assert_called_once()

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_init_default_state_is_idle(self, mock_output, mock_get_transcriber,
                                         mock_recorder, mock_detector):
        """HandFreeApp starts in IDLE state."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config()
        app = HandFreeApp(config=config)
        assert app.state == AppState.IDLE

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_init_not_running(self, mock_output, mock_get_transcriber,
                               mock_recorder, mock_detector):
        """HandFreeApp is not running after init."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config()
        app = HandFreeApp(config=config)
        assert app.is_running is False

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_init_custom_sample_rate(self, mock_output, mock_get_transcriber,
                                      mock_recorder, mock_detector):
        """HandFreeApp passes sample rate to AudioRecorder."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config(sample_rate=44100)
        app = HandFreeApp(config=config)
        mock_recorder.assert_called_once_with(sample_rate=44100)

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_init_custom_type_delay(self, mock_output, mock_get_transcriber,
                                     mock_recorder, mock_detector):
        """HandFreeApp passes type delay to OutputHandler."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config(type_delay=0.05)
        app = HandFreeApp(config=config)
        mock_output.assert_called_once_with(type_delay=0.05)


class TestHandFreeAppStateMachine:
    """Tests for HandFreeApp state machine transitions."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.create_hotkey_detector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.get_transcriber') as mock_get_transcriber, \
             patch('main.create_output_handler') as mock_output:

            mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
            config = make_config()
            app = HandFreeApp(config=config)

            # Set up mock instances
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_handle_start_starts_recording(self, app):
        """Unmute event transitions from IDLE to RECORDING."""
        app._state = AppState.IDLE
        app.handle_start()

        assert app.state == AppState.RECORDING
        app.recorder.start_recording.assert_called_once()

    def test_handle_start_ignored_while_transcribing(self, app):
        """Unmute event is ignored during TRANSCRIBING state."""
        app._state = AppState.TRANSCRIBING
        app.handle_start()

        assert app.state == AppState.TRANSCRIBING
        app.recorder.start_recording.assert_not_called()

    def test_handle_stop_triggers_transcription(self, app):
        """Mute event triggers transcription when RECORDING."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 3.0
        app.recorder.stop_recording.return_value = b"wav-audio-data"
        app.transcriber.transcribe.return_value = "Hello world"

        app.handle_stop()

        app.recorder.stop_recording.assert_called_once()
        app.transcriber.transcribe.assert_called_once()
        app.output.output.assert_called_once_with("Hello world", use_paste=False, skip_clipboard=False)
        assert app.state == AppState.IDLE

    def test_handle_stop_ignored_when_idle(self, app):
        """Mute event is ignored in IDLE state."""
        app._state = AppState.IDLE
        app.handle_stop()

        app.recorder.stop_recording.assert_not_called()
        assert app.state == AppState.IDLE

    def test_handle_stop_handles_empty_audio(self, app):
        """Mute event handles empty recording gracefully."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 0.0
        app.recorder.stop_recording.return_value = b""

        app.handle_stop()

        app.transcriber.transcribe.assert_not_called()
        assert app.state == AppState.IDLE

    def test_handle_stop_handles_short_audio(self, app):
        """Mute event ignores very short recordings."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 0.05  # Less than 0.1s threshold
        app.recorder.stop_recording.return_value = b"tiny-audio"

        app.handle_stop()

        app.transcriber.transcribe.assert_not_called()
        assert app.state == AppState.IDLE

    def test_handle_stop_handles_transcription_error(self, app):
        """Mute event handles transcription errors gracefully."""
        from handfree.exceptions import TranscriptionError

        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 3.0
        app.recorder.stop_recording.return_value = b"wav-audio-data"
        app.transcriber.transcribe.side_effect = TranscriptionError("API error")

        app.handle_stop()

        assert app.state == AppState.IDLE
        app.output.output.assert_not_called()

    def test_handle_stop_handles_output_error(self, app):
        """Mute event handles output errors gracefully."""
        from handfree.exceptions import OutputError

        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 3.0
        app.recorder.stop_recording.return_value = b"wav-audio-data"
        app.transcriber.transcribe.return_value = "Hello world"
        app.output.output.side_effect = OutputError("Typing failed")

        app.handle_stop()

        assert app.state == AppState.IDLE

    def test_handle_stop_handles_empty_transcription(self, app):
        """Mute event handles empty transcription result."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 3.0
        app.recorder.stop_recording.return_value = b"wav-audio-data"
        app.transcriber.transcribe.return_value = ""

        app.handle_stop()

        assert app.state == AppState.IDLE
        app.output.output.assert_not_called()


class TestHandFreeAppLifecycle:
    """Tests for HandFreeApp start/stop lifecycle."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.create_hotkey_detector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.get_transcriber') as mock_get_transcriber, \
             patch('main.create_output_handler') as mock_output:

            mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
            config = make_config()
            app = HandFreeApp(config=config)
            app.recorder = Mock()
            app.detector = Mock()

            yield app

    def test_stop_sets_running_false(self, app):
        """Stop sets is_running to False."""
        app._running = True
        app.stop()
        assert app.is_running is False

    def test_stop_stops_detector(self, app):
        """Stop calls detector.stop()."""
        app._running = True
        app.stop()
        app.detector.stop.assert_called_once()

    def test_stop_stops_recording_if_active(self, app):
        """Stop stops recording if in RECORDING state."""
        app._running = True
        app._state = AppState.RECORDING
        app.stop()
        app.recorder.stop_recording.assert_called_once()

    def test_stop_idempotent(self, app):
        """Stop can be called multiple times safely."""
        app._running = True
        app.stop()
        app.stop()
        assert app.detector.stop.call_count == 1

    def test_stop_when_not_running(self, app):
        """Stop does nothing when not running."""
        app._running = False
        app.stop()
        app.detector.stop.assert_not_called()


class TestHandFreeAppLanguage:
    """Tests for language configuration."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_language_passed_to_transcriber(self, mock_output, mock_get_transcriber,
                                             mock_recorder, mock_detector):
        """Language is passed to transcriber.transcribe()."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config(language="en")
        app = HandFreeApp(config=config)

        # Set up mocks
        app.recorder = Mock()
        app.transcriber = Mock()
        app.output = Mock()

        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 3.0
        app.recorder.stop_recording.return_value = b"audio-data"
        app.transcriber.transcribe.return_value = "Hello"

        app.handle_stop()

        app.transcriber.transcribe.assert_called_once_with(
            b"audio-data",
            language="en"
        )


class TestHandFreeAppUsePaste:
    """Tests for use_paste configuration."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @patch('main.create_hotkey_detector')
    @patch('main.AudioRecorder')
    @patch('main.get_transcriber')
    @patch('main.create_output_handler')
    def test_use_paste_passed_to_output(self, mock_output, mock_get_transcriber,
                                         mock_recorder, mock_detector):
        """use_paste is passed to output.output()."""
        mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
        config = make_config(use_paste=True)
        app = HandFreeApp(config=config)

        app.recorder = Mock()
        app.transcriber = Mock()
        app.output = Mock()

        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 3.0
        app.recorder.stop_recording.return_value = b"audio-data"
        app.transcriber.transcribe.return_value = "Hello"

        app.handle_stop()

        app.output.output.assert_called_once_with("Hello", use_paste=True, skip_clipboard=False)


class TestMainFunction:
    """Tests for the main() entry point function."""

    @patch('handfree.config.load_dotenv')
    def test_main_exits_without_api_key(self, mock_load_dotenv, monkeypatch):
        """main() exits with error when GROQ_API_KEY is not set and transcriber is groq."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "groq")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('main.HandFreeApp')
    @patch('main.signal.signal')
    def test_main_creates_app_with_env_config(self, mock_signal, mock_app_class, monkeypatch):
        """main() creates HandFreeApp with environment configuration."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_LANGUAGE", "es")
        monkeypatch.setenv("HANDFREE_TYPE_DELAY", "0.1")
        monkeypatch.setenv("HANDFREE_SAMPLE_RATE", "22050")
        monkeypatch.setenv("HANDFREE_USE_PASTE", "true")

        mock_app = Mock()
        mock_app_class.return_value = mock_app
        # Have run() raise an exception that will cause main() to exit
        mock_app.run.side_effect = Exception("test exit")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        # Now takes a config object instead of individual args
        mock_app_class.assert_called_once()
        call_kwargs = mock_app_class.call_args[1]
        assert "config" in call_kwargs
        config = call_kwargs["config"]
        assert config.groq_api_key == "test-key"
        assert config.language == "es"
        assert config.type_delay == 0.1
        assert config.sample_rate == 22050
        assert config.use_paste is True


class TestConfigModule:
    """Tests for the config module."""

    @patch('handfree.config.load_dotenv')
    def test_config_from_env_requires_api_key_for_groq(self, mock_load_dotenv, monkeypatch):
        """Config.from_env() raises error without API key when transcriber is groq."""
        # Ensure GROQ_API_KEY is not set
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("HANDFREE_TRANSCRIBER", "groq")  # Explicitly use groq

        from handfree.config import Config

        with pytest.raises(ValueError) as exc_info:
            Config.from_env()

        assert "GROQ_API_KEY" in str(exc_info.value)

    def test_config_from_env_loads_all_settings(self, monkeypatch):
        """Config.from_env() loads all environment settings."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_LANGUAGE", "fr")
        monkeypatch.setenv("HANDFREE_TYPE_DELAY", "0.5")
        monkeypatch.setenv("HANDFREE_SAMPLE_RATE", "44100")
        monkeypatch.setenv("HANDFREE_USE_PASTE", "yes")

        from handfree.config import Config

        config = Config.from_env()

        assert config.groq_api_key == "test-key"
        assert config.language == "fr"
        assert config.type_delay == 0.5
        assert config.sample_rate == 44100
        assert config.use_paste is True

    def test_config_validate_negative_delay(self, monkeypatch):
        """Config.validate() rejects negative type delay."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        from handfree.config import Config

        config = Config(groq_api_key="test-key", type_delay=-1.0)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_TYPE_DELAY" in str(exc_info.value)

    def test_config_validate_zero_sample_rate(self, monkeypatch):
        """Config.validate() rejects zero sample rate."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=0)

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "HANDFREE_SAMPLE_RATE" in str(exc_info.value)


class TestExceptionsModule:
    """Tests for the exceptions module."""

    def test_all_exceptions_inherit_from_base(self):
        """All custom exceptions inherit from HandFreeError."""
        from handfree.exceptions import (
            HandFreeError,
            ConfigurationError,
            MuteDetectionError,
            AudioRecordingError,
            TranscriptionError,
            OutputError,
        )

        assert issubclass(ConfigurationError, HandFreeError)
        assert issubclass(MuteDetectionError, HandFreeError)
        assert issubclass(AudioRecordingError, HandFreeError)
        assert issubclass(TranscriptionError, HandFreeError)
        assert issubclass(OutputError, HandFreeError)

    def test_exceptions_can_be_raised_with_message(self):
        """Custom exceptions can be raised with a message."""
        from handfree.exceptions import TranscriptionError

        with pytest.raises(TranscriptionError) as exc_info:
            raise TranscriptionError("Test error message")

        assert "Test error message" in str(exc_info.value)


class TestStateMachineProperties:
    """Property-based tests for state machine invariants."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.create_hotkey_detector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.get_transcriber') as mock_get_transcriber, \
             patch('main.create_output_handler') as mock_output:

            mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
            config = make_config()
            app = HandFreeApp(config=config)
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_state_always_valid(self, app):
        """State is always one of the defined AppState values."""
        valid_states = {AppState.IDLE, AppState.RECORDING, AppState.TRANSCRIBING}
        assert app.state in valid_states

    def test_idle_to_recording_transition(self, app):
        """IDLE -> RECORDING transition via unmute."""
        app._state = AppState.IDLE
        app.handle_start()
        assert app.state == AppState.RECORDING

    def test_recording_to_idle_via_mute(self, app):
        """RECORDING -> IDLE transition via mute (after transcription)."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = 1.0
        app.recorder.stop_recording.return_value = b"audio"
        app.transcriber.transcribe.return_value = "text"

        app.handle_stop()
        assert app.state == AppState.IDLE

    def test_unmute_while_recording_restarts(self, app):
        """Unmute while recording restarts the recording (clears buffer)."""
        app._state = AppState.IDLE
        app.handle_start()
        assert app.state == AppState.RECORDING

        # Second unmute restarts recording (useful if user wants to start over)
        app.handle_start()
        assert app.state == AppState.RECORDING
        # Two calls to start_recording (original + restart)
        assert app.recorder.start_recording.call_count == 2

    def test_mute_without_recording_is_noop(self, app):
        """Mute in IDLE state is a no-op."""
        app._state = AppState.IDLE
        app.handle_stop()
        assert app.state == AppState.IDLE
        app.recorder.stop_recording.assert_not_called()

    @pytest.mark.parametrize("duration", [0.0, 0.01, 0.05, 0.09])
    def test_short_recordings_rejected(self, app, duration):
        """Recordings shorter than threshold are rejected."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = duration
        app.recorder.stop_recording.return_value = b"tiny"

        app.handle_stop()

        app.transcriber.transcribe.assert_not_called()
        assert app.state == AppState.IDLE

    @pytest.mark.parametrize("duration", [0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0])
    def test_valid_recordings_transcribed(self, app, duration):
        """Recordings at or above threshold are transcribed."""
        app._state = AppState.RECORDING
        app.recorder.get_duration.return_value = duration
        app.recorder.stop_recording.return_value = b"audio-data"
        app.transcriber.transcribe.return_value = "transcribed text"

        app.handle_stop()

        app.transcriber.transcribe.assert_called_once()
        assert app.state == AppState.IDLE


class TestStateMachineSequences:
    """Tests for sequences of state transitions."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.create_hotkey_detector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.get_transcriber') as mock_get_transcriber, \
             patch('main.create_output_handler') as mock_output:

            mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
            config = make_config()
            app = HandFreeApp(config=config)
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_full_cycle_returns_to_idle(self, app):
        """Complete unmute -> mute cycle returns to IDLE."""
        assert app.state == AppState.IDLE

        # Unmute
        app.handle_start()
        assert app.state == AppState.RECORDING

        # Mute
        app.recorder.get_duration.return_value = 2.0
        app.recorder.stop_recording.return_value = b"audio"
        app.transcriber.transcribe.return_value = "text"
        app.handle_stop()
        assert app.state == AppState.IDLE

    def test_multiple_cycles(self, app):
        """Multiple recording cycles work correctly."""
        for i in range(3):
            assert app.state == AppState.IDLE

            app.handle_start()
            assert app.state == AppState.RECORDING

            app.recorder.get_duration.return_value = 1.0 + i
            app.recorder.stop_recording.return_value = f"audio-{i}".encode()
            app.transcriber.transcribe.return_value = f"text-{i}"
            app.handle_stop()

            assert app.state == AppState.IDLE

        assert app.recorder.start_recording.call_count == 3
        assert app.transcriber.transcribe.call_count == 3

    def test_error_recovery_returns_to_idle(self, app):
        """Errors during transcription still return to IDLE."""
        app.handle_start()
        assert app.state == AppState.RECORDING

        app.recorder.get_duration.return_value = 2.0
        app.recorder.stop_recording.return_value = b"audio"
        app.transcriber.transcribe.side_effect = TranscriptionError("API down")

        app.handle_stop()
        assert app.state == AppState.IDLE

        # Should be able to start another recording
        app.handle_start()
        assert app.state == AppState.RECORDING


class TestConfigProperties:
    """Property-based tests for configuration validation."""

    @pytest.mark.parametrize("delay", [0.0, 0.001, 0.1, 0.5, 1.0, 10.0])
    def test_valid_type_delays(self, delay, monkeypatch):
        """Valid type delays pass validation."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from handfree.config import Config

        config = Config(groq_api_key="test-key", type_delay=delay)
        config.validate()  # Should not raise

    @pytest.mark.parametrize("delay", [-0.001, -0.1, -1.0, -100.0])
    def test_negative_type_delays_rejected(self, delay, monkeypatch):
        """Negative type delays are rejected."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from handfree.config import Config

        config = Config(groq_api_key="test-key", type_delay=delay)
        with pytest.raises(ValueError):
            config.validate()

    @pytest.mark.parametrize("rate", [8000, 16000, 22050, 44100, 48000])
    def test_standard_sample_rates(self, rate, monkeypatch):
        """Standard sample rates pass validation."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=rate)
        config.validate()  # Should not raise

    @pytest.mark.parametrize("rate", [0, -1, -16000])
    def test_invalid_sample_rates_rejected(self, rate, monkeypatch):
        """Invalid sample rates are rejected."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from handfree.config import Config

        config = Config(groq_api_key="test-key", sample_rate=rate)
        with pytest.raises(ValueError):
            config.validate()

    @pytest.mark.parametrize("use_paste_env,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("Yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("", False),
    ])
    def test_use_paste_parsing(self, use_paste_env, expected, monkeypatch):
        """use_paste environment variable is parsed correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_USE_PASTE", use_paste_env)
        from handfree.config import Config

        config = Config.from_env()
        assert config.use_paste == expected


class TestRunLoopBehavior:
    """Tests for the run loop behavior."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.create_hotkey_detector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.get_transcriber') as mock_get_transcriber, \
             patch('main.create_output_handler') as mock_output:

            mock_get_transcriber.return_value = (Mock(), "groq (cloud)")
            config = make_config()
            app = HandFreeApp(config=config)
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_stop_from_idle_state(self, app):
        """Stop works correctly from IDLE state."""
        app._running = True
        app._state = AppState.IDLE
        app.stop()

        assert app.is_running is False
        app.detector.stop.assert_called_once()
        app.recorder.stop_recording.assert_not_called()

    def test_stop_from_recording_state(self, app):
        """Stop works correctly from RECORDING state."""
        app._running = True
        app._state = AppState.RECORDING
        app.stop()

        assert app.is_running is False
        app.detector.stop.assert_called_once()
        app.recorder.stop_recording.assert_called_once()

    def test_stop_from_transcribing_state(self, app):
        """Stop works correctly from TRANSCRIBING state."""
        app._running = True
        app._state = AppState.TRANSCRIBING
        app.stop()

        assert app.is_running is False
        app.detector.stop.assert_called_once()
        # Recording already stopped when entering TRANSCRIBING
        app.recorder.stop_recording.assert_not_called()
