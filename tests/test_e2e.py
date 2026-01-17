"""
End-to-End Integration Tests for HandFree.

Tests cover the complete application flow from hotkey detection to text output.
These tests verify component integration and the full transcription pipeline.

Test coverage for Step 8 of the implementation plan:
- 8.1 Test basic flow: press Fn -> speak -> release Fn -> text appears
- 8.2 Test empty recording: press -> immediately release
- 8.3 Test long recording: 60 seconds of speech
- 8.4 Test special characters: punctuation preserved
- 8.5 Test quick succession: multiple cycles
- 8.6 Test detector error: graceful error message
"""

import io
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import numpy as np
from scipy.io import wavfile

from handfree.exceptions import (
    TranscriptionError,
    OutputError,
    MuteDetectionError,
    AudioRecordingError,
)


def _setup_macos_mocks():
    """Set up mocks for macOS-specific modules if not already present."""
    if 'Foundation' not in sys.modules or isinstance(sys.modules['Foundation'], MagicMock):
        sys.modules['Foundation'] = MagicMock()
    if 'AVFAudio' not in sys.modules or isinstance(sys.modules['AVFAudio'], MagicMock):
        sys.modules['AVFAudio'] = MagicMock()


def _setup_tkinter_mock():
    """Set up mock for tkinter if not available."""
    try:
        import tkinter
    except ImportError:
        # Create mock tkinter module
        mock_tk = MagicMock()
        mock_tk.Tk = MagicMock()
        mock_tk.Toplevel = MagicMock()
        mock_tk.Canvas = MagicMock()
        mock_tk.TclError = Exception
        sys.modules['tkinter'] = mock_tk
        sys.modules['_tkinter'] = MagicMock()


# Set up mocks before importing main
_setup_macos_mocks()
_setup_tkinter_mock()
from main import HandFreeApp, AppState, main


def create_test_audio(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """
    Helper to create valid WAV audio bytes.

    Args:
        duration_sec: Duration of audio in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        WAV file as bytes.
    """
    # Generate simple sine wave (440 Hz tone)
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
    audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    # Encode as WAV
    wav_buffer = io.BytesIO()
    wavfile.write(wav_buffer, sample_rate, audio_data)
    wav_buffer.seek(0)
    return wav_buffer.getvalue()


class TestE2EBasicFlow:
    """
    Test 8.1: Basic flow - unmute -> speak -> mute -> text appears.

    Verifies the complete transcription pipeline works end-to-end.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with fully mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")

            # Create mock instances with proper return values
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_basic_flow_complete_cycle(self, mock_app):
        """
        Complete flow: IDLE -> unmute -> RECORDING -> mute -> TRANSCRIBING -> IDLE.

        Verifies that the state machine transitions correctly and all components
        are called in the right order.
        """
        # Initial state
        assert mock_app.state == AppState.IDLE

        # Step 1: User presses Fn key
        mock_app.handle_start()
        assert mock_app.state == AppState.RECORDING
        mock_app.recorder.start_recording.assert_called_once()

        # Step 2: User speaks (simulated by setting up mock returns)
        test_audio = create_test_audio(duration_sec=3.0)
        mock_app.recorder.get_duration.return_value = 3.0
        mock_app.recorder.stop_recording.return_value = test_audio
        mock_app.transcriber.transcribe.return_value = "Hello world, this is a test."

        # Step 3: User releases Fn key
        mock_app.handle_stop()

        # Verify all components were called correctly
        mock_app.recorder.stop_recording.assert_called_once()
        mock_app.transcriber.transcribe.assert_called_once_with(
            test_audio,
            language=None
        )
        mock_app.output.output.assert_called_once_with(
            "Hello world, this is a test.",
            use_paste=False
        )

        # State should return to IDLE
        assert mock_app.state == AppState.IDLE

    def test_transcribed_text_matches_output(self, mock_app):
        """Verify transcribed text is passed to output handler exactly."""
        mock_app._state = AppState.RECORDING

        # Various test strings with different content
        test_texts = [
            "Simple text",
            "Text with punctuation: Hello, World!",
            "Numbers 123 and symbols @#$%",
            "Multi-line\ntext\nhere",
            "Unicode: Caf\u00e9, na\u00efve, \u2603",
        ]

        for expected_text in test_texts:
            mock_app._state = AppState.RECORDING
            mock_app.recorder.get_duration.return_value = 2.0
            mock_app.recorder.stop_recording.return_value = create_test_audio()
            mock_app.transcriber.transcribe.return_value = expected_text
            mock_app.output.reset_mock()

            mock_app.handle_stop()

            # Verify exact text was passed to output
            mock_app.output.output.assert_called_once_with(
                expected_text,
                use_paste=False
            )

    def test_basic_flow_with_language_setting(self, mock_app):
        """Verify language setting is passed to transcriber."""
        mock_app.language = "en"
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = "English text"

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_called_once_with(
            mock_app.recorder.stop_recording.return_value,
            language="en"
        )

    def test_basic_flow_with_paste_mode(self, mock_app):
        """Verify use_paste setting is passed to output handler."""
        mock_app.use_paste = True
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = "Pasted text"

        mock_app.handle_stop()

        mock_app.output.output.assert_called_once_with(
            "Pasted text",
            use_paste=True
        )


class TestE2EEmptyRecording:
    """
    Test 8.2: Empty recording - unmute -> immediately mute.

    Verifies graceful handling when user mutes without speaking.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_empty_audio_bytes_handled(self, mock_app):
        """No crash when recording returns empty bytes."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 0.0
        mock_app.recorder.stop_recording.return_value = b""

        # Should not raise any exception
        mock_app.handle_stop()

        # Transcriber should NOT be called with empty audio
        mock_app.transcriber.transcribe.assert_not_called()
        mock_app.output.output.assert_not_called()
        assert mock_app.state == AppState.IDLE

    def test_short_recording_threshold(self, mock_app):
        """Recordings shorter than threshold are rejected."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 0.05  # 50ms, below 100ms threshold
        mock_app.recorder.stop_recording.return_value = create_test_audio(0.05)

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_not_called()
        assert mock_app.state == AppState.IDLE

    @pytest.mark.parametrize("duration", [0.0, 0.01, 0.05, 0.09, 0.099])
    def test_various_short_durations_rejected(self, mock_app, duration):
        """Various durations below threshold are all rejected."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = duration
        mock_app.recorder.stop_recording.return_value = create_test_audio(max(duration, 0.001))

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_not_called()
        assert mock_app.state == AppState.IDLE

    def test_immediate_mute_after_unmute(self, mock_app):
        """Simulates rapid unmute->mute sequence."""
        # Start recording
        mock_app.handle_start()
        assert mock_app.state == AppState.RECORDING

        # Immediately mute with no audio captured
        mock_app.recorder.get_duration.return_value = 0.0
        mock_app.recorder.stop_recording.return_value = b""

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_not_called()
        assert mock_app.state == AppState.IDLE

    def test_mute_when_idle_is_noop(self, mock_app):
        """Muting when not recording does nothing."""
        assert mock_app.state == AppState.IDLE

        mock_app.handle_stop()

        mock_app.recorder.stop_recording.assert_not_called()
        mock_app.transcriber.transcribe.assert_not_called()
        assert mock_app.state == AppState.IDLE


class TestE2ELongRecording:
    """
    Test 8.3: Long recording - 60 seconds of speech.

    Verifies the system handles longer recordings correctly.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_60_second_recording(self, mock_app):
        """60 second recording is processed correctly."""
        mock_app._state = AppState.RECORDING

        # Simulate 60 seconds of audio
        mock_app.recorder.get_duration.return_value = 60.0
        # Create representative audio bytes (actual 60s would be ~1.9MB)
        mock_app.recorder.stop_recording.return_value = create_test_audio(1.0)  # Use 1s for test speed
        mock_app.transcriber.transcribe.return_value = "This is a long transcription with many words spoken over 60 seconds."

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_called_once()
        mock_app.output.output.assert_called_once()
        assert mock_app.state == AppState.IDLE

    @pytest.mark.parametrize("duration", [10.0, 30.0, 60.0, 120.0, 300.0])
    def test_various_long_durations(self, mock_app, duration):
        """Various long durations are all processed."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = duration
        mock_app.recorder.stop_recording.return_value = create_test_audio(1.0)
        mock_app.transcriber.transcribe.return_value = f"Text for {duration}s recording"

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_called_once()
        mock_app.output.output.assert_called_once_with(
            f"Text for {duration}s recording",
            use_paste=False
        )
        assert mock_app.state == AppState.IDLE

    def test_max_duration_boundary(self, mock_app):
        """Test at the maximum expected duration (5 minutes = 300 seconds)."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 300.0
        mock_app.recorder.stop_recording.return_value = create_test_audio(1.0)
        mock_app.transcriber.transcribe.return_value = "Five minutes of speech."

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_called_once()
        assert mock_app.state == AppState.IDLE


class TestE2ESpecialCharacters:
    """
    Test 8.4: Special characters - punctuation preserved.

    Verifies that special characters, punctuation, and unicode are handled correctly.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    @pytest.mark.parametrize("text", [
        # Basic punctuation
        "Hello, World!",
        "What? Really!",
        "One. Two. Three.",
        "Semi;colon:colon",
        # Quotes and apostrophes
        "It's a test.",
        '"Quoted text"',
        "'Single quotes'",
        "Don't stop believing",
        # Special symbols
        "Email: test@example.com",
        "Price: $19.99",
        "100% complete",
        "A & B & C",
        "Path/to/file",
        # Parentheses and brackets
        "(parentheses)",
        "[brackets]",
        "{braces}",
        "<angle brackets>",
        # Math and comparison
        "2 + 2 = 4",
        "a < b > c",
        "x * y / z",
        # Unicode characters
        "Caf\u00e9 au lait",
        "Na\u00efve approach",
        "R\u00e9sum\u00e9",
        "\u00d1o\u00f1o",
        # Emoji (if supported)
        "\ud83d\udc4d Great job!",
        # Multi-line
        "Line 1\nLine 2\nLine 3",
        "Tab\there",
    ])
    def test_special_character_preservation(self, mock_app, text):
        """Special characters in transcription are preserved in output."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = text

        mock_app.handle_stop()

        # Verify exact text preservation
        mock_app.output.output.assert_called_once_with(text, use_paste=False)

    def test_empty_transcription_result(self, mock_app):
        """Empty string from transcriber is handled."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = ""

        mock_app.handle_stop()

        # Output should NOT be called for empty transcription
        mock_app.output.output.assert_not_called()
        assert mock_app.state == AppState.IDLE

    def test_whitespace_only_transcription(self, mock_app):
        """Whitespace-only transcription is handled."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = "   "  # Only spaces

        mock_app.handle_stop()

        # Note: Current implementation outputs whitespace-only text
        # This test documents current behavior
        mock_app.output.output.assert_called_once_with("   ", use_paste=False)


class TestE2EQuickSuccession:
    """
    Test 8.5: Quick succession - multiple recording cycles.

    Verifies the system handles rapid unmute/mute cycles correctly.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_multiple_cycles_sequential(self, mock_app):
        """Multiple recording cycles work correctly in sequence."""
        transcriptions = [
            "First message",
            "Second message",
            "Third message",
        ]

        for i, expected_text in enumerate(transcriptions):
            # Reset mocks for this cycle
            mock_app.recorder.reset_mock()
            mock_app.transcriber.reset_mock()
            mock_app.output.reset_mock()

            assert mock_app.state == AppState.IDLE

            # Unmute
            mock_app.handle_start()
            assert mock_app.state == AppState.RECORDING
            mock_app.recorder.start_recording.assert_called_once()

            # Set up recording result
            mock_app.recorder.get_duration.return_value = 1.0 + i
            mock_app.recorder.stop_recording.return_value = create_test_audio()
            mock_app.transcriber.transcribe.return_value = expected_text

            # Mute
            mock_app.handle_stop()

            assert mock_app.state == AppState.IDLE
            mock_app.output.output.assert_called_once_with(expected_text, use_paste=False)

    def test_five_rapid_cycles(self, mock_app):
        """Five rapid recording cycles all complete successfully."""
        num_cycles = 5

        for i in range(num_cycles):
            mock_app._state = AppState.IDLE

            mock_app.handle_start()
            assert mock_app.state == AppState.RECORDING

            mock_app.recorder.get_duration.return_value = 0.5
            mock_app.recorder.stop_recording.return_value = create_test_audio()
            mock_app.transcriber.transcribe.return_value = f"Cycle {i+1}"

            mock_app.handle_stop()
            assert mock_app.state == AppState.IDLE

        # Verify all cycles completed
        assert mock_app.recorder.start_recording.call_count == num_cycles
        assert mock_app.transcriber.transcribe.call_count == num_cycles
        assert mock_app.output.output.call_count == num_cycles

    def test_unmute_while_recording_restarts(self, mock_app):
        """Unmuting while already recording restarts the recording."""
        # First unmute
        mock_app.handle_start()
        assert mock_app.state == AppState.RECORDING
        assert mock_app.recorder.start_recording.call_count == 1

        # Second unmute (restart)
        mock_app.handle_start()
        assert mock_app.state == AppState.RECORDING
        assert mock_app.recorder.start_recording.call_count == 2

    def test_unmute_during_transcription_ignored(self, mock_app):
        """Unmute events during transcription are ignored."""
        mock_app._state = AppState.TRANSCRIBING

        mock_app.handle_start()

        # Should remain in TRANSCRIBING state
        assert mock_app.state == AppState.TRANSCRIBING
        mock_app.recorder.start_recording.assert_not_called()

    def test_cycle_with_error_then_success(self, mock_app):
        """Recovery after transcription error in previous cycle."""
        # First cycle - fails
        mock_app.handle_start()
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.side_effect = TranscriptionError("API error")

        mock_app.handle_stop()
        assert mock_app.state == AppState.IDLE
        mock_app.output.output.assert_not_called()

        # Second cycle - succeeds
        mock_app.transcriber.transcribe.side_effect = None
        mock_app.transcriber.transcribe.return_value = "Success after failure"

        mock_app.handle_start()
        mock_app.recorder.get_duration.return_value = 2.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()

        mock_app.handle_stop()

        assert mock_app.state == AppState.IDLE
        mock_app.output.output.assert_called_once_with("Success after failure", use_paste=False)


class TestE2EDetectorErrors:
    """
    Test 8.6: Detector error - graceful error handling.

    Verifies graceful handling when hotkey detection fails.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    def test_hotkey_detector_init_failure(self, monkeypatch):
        """Graceful handling when HotkeyDetector fails to initialize."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            mock_detector.side_effect = RuntimeError("Failed to create event tap")

            with pytest.raises(RuntimeError) as exc_info:
                HandFreeApp(api_key="test-key")

            assert "Failed to create event tap" in str(exc_info.value)

    def test_hotkey_detector_start_failure(self, monkeypatch):
        """Graceful handling when HotkeyDetector.start() fails."""
        with patch('main.HotkeyDetector') as mock_detector_class, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            mock_detector = Mock()
            mock_detector_class.return_value = mock_detector
            mock_detector.start.side_effect = RuntimeError("Failed to start hotkey detection")

            app = HandFreeApp(api_key="test-key")

            with pytest.raises(RuntimeError):
                app.run()

    def test_audio_recorder_failure(self, monkeypatch):
        """Graceful handling when audio recording fails."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder_class, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            mock_recorder_class.side_effect = AudioRecordingError("No audio device")

            with pytest.raises(AudioRecordingError):
                HandFreeApp(api_key="test-key")

    def test_transcription_api_failure(self, monkeypatch):
        """Graceful handling when transcription API fails."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            app._state = AppState.RECORDING
            app.recorder.get_duration.return_value = 2.0
            app.recorder.stop_recording.return_value = create_test_audio()
            app.transcriber.transcribe.side_effect = TranscriptionError("API unavailable")

            # Should not raise, should handle gracefully
            app.handle_stop()

            assert app.state == AppState.IDLE
            app.output.output.assert_not_called()

    def test_output_handler_failure(self, monkeypatch):
        """Graceful handling when output handler fails."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            app._state = AppState.RECORDING
            app.recorder.get_duration.return_value = 2.0
            app.recorder.stop_recording.return_value = create_test_audio()
            app.transcriber.transcribe.return_value = "Text to output"
            app.output.output.side_effect = OutputError("Typing failed")

            # Should not raise, should handle gracefully
            app.handle_stop()

            assert app.state == AppState.IDLE


class TestE2EEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def test_missing_api_key_exits(self, monkeypatch):
        """Application exits with error when API key is missing."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    def test_env_configuration_loaded(self, monkeypatch):
        """Environment configuration is loaded correctly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("HANDFREE_LANGUAGE", "es")
        monkeypatch.setenv("HANDFREE_TYPE_DELAY", "0.1")
        monkeypatch.setenv("HANDFREE_SAMPLE_RATE", "22050")
        monkeypatch.setenv("HANDFREE_USE_PASTE", "true")

        with patch('main.HandFreeApp') as mock_app_class, \
             patch('main.signal.signal'):

            mock_app = Mock()
            mock_app_class.return_value = mock_app
            mock_app.run.side_effect = Exception("test exit")

            with pytest.raises(SystemExit):
                main()

            mock_app_class.assert_called_once_with(
                language="es",
                type_delay=0.1,
                sample_rate=22050,
                use_paste=True
            )


class TestE2EPropertyBased:
    """Property-based tests for edge cases and invariants."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    @pytest.mark.parametrize("event_sequence", [
        ["unmute", "mute"],
        ["unmute", "unmute", "mute"],
        ["mute"],
        ["mute", "mute"],
        ["unmute", "mute", "unmute", "mute"],
        ["unmute", "mute", "mute"],
        ["mute", "unmute", "mute"],
    ])
    def test_event_sequences_end_in_valid_state(self, mock_app, event_sequence):
        """Any sequence of events ends in a valid state."""
        valid_states = {AppState.IDLE, AppState.RECORDING, AppState.TRANSCRIBING}

        # Set up successful transcription
        mock_app.recorder.get_duration.return_value = 1.0
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = "text"

        for event in event_sequence:
            if event == "unmute":
                mock_app.handle_start()
            else:
                mock_app.handle_stop()

            assert mock_app.state in valid_states

    @pytest.mark.parametrize("duration", [
        0.1,      # Minimum threshold
        0.5,
        1.0,
        5.0,
        30.0,
        60.0,
        120.0,
        300.0,    # 5 minutes - max expected
    ])
    def test_various_valid_durations_transcribed(self, mock_app, duration):
        """Various recording durations at or above threshold are transcribed."""
        mock_app._state = AppState.RECORDING
        mock_app.recorder.get_duration.return_value = duration
        mock_app.recorder.stop_recording.return_value = create_test_audio()
        mock_app.transcriber.transcribe.return_value = "Transcribed"

        mock_app.handle_stop()

        mock_app.transcriber.transcribe.assert_called_once()
        mock_app.output.output.assert_called_once()

    def test_state_machine_always_returns_to_idle(self, mock_app):
        """State machine always returns to IDLE after processing."""
        # Test various scenarios
        scenarios = [
            # Normal success
            {"duration": 2.0, "text": "Success"},
            # Empty transcription
            {"duration": 2.0, "text": ""},
            # Short recording
            {"duration": 0.05, "text": "Ignored"},
        ]

        for scenario in scenarios:
            mock_app._state = AppState.RECORDING
            mock_app.recorder.get_duration.return_value = scenario["duration"]
            mock_app.recorder.stop_recording.return_value = create_test_audio()
            mock_app.transcriber.transcribe.return_value = scenario["text"]

            mock_app.handle_stop()

            assert mock_app.state == AppState.IDLE

    def test_state_machine_error_recovery(self, mock_app):
        """State machine recovers from errors and returns to IDLE."""
        error_types = [
            TranscriptionError("API error"),
            OutputError("Output failed"),
            Exception("Unexpected error"),
        ]

        for error in error_types:
            mock_app._state = AppState.RECORDING
            mock_app.recorder.get_duration.return_value = 2.0
            mock_app.recorder.stop_recording.return_value = create_test_audio()
            mock_app.transcriber.transcribe.side_effect = error

            mock_app.handle_stop()

            assert mock_app.state == AppState.IDLE

            # Reset for next iteration
            mock_app.transcriber.transcribe.side_effect = None


class TestE2EGracefulShutdown:
    """Tests for graceful shutdown behavior."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up required environment variables."""
        monkeypatch.setenv("GROQ_API_KEY", "test-api-key")

    @pytest.fixture
    def mock_app(self):
        """Create a HandFreeApp with mocked dependencies."""
        with patch('main.HotkeyDetector') as mock_detector, \
             patch('main.AudioRecorder') as mock_recorder, \
             patch('main.Transcriber') as mock_transcriber, \
             patch('main.OutputHandler') as mock_output:

            app = HandFreeApp(api_key="test-key")
            app.recorder = Mock()
            app.transcriber = Mock()
            app.output = Mock()
            app.detector = Mock()

            yield app

    def test_stop_from_idle(self, mock_app):
        """Stop from IDLE state works correctly."""
        mock_app._running = True
        mock_app._state = AppState.IDLE

        mock_app.stop()

        assert not mock_app.is_running
        mock_app.detector.stop.assert_called_once()
        mock_app.recorder.stop_recording.assert_not_called()

    def test_stop_from_recording(self, mock_app):
        """Stop from RECORDING state stops recording."""
        mock_app._running = True
        mock_app._state = AppState.RECORDING

        mock_app.stop()

        assert not mock_app.is_running
        mock_app.detector.stop.assert_called_once()
        mock_app.recorder.stop_recording.assert_called_once()

    def test_stop_from_transcribing(self, mock_app):
        """Stop from TRANSCRIBING state works correctly."""
        mock_app._running = True
        mock_app._state = AppState.TRANSCRIBING

        mock_app.stop()

        assert not mock_app.is_running
        mock_app.detector.stop.assert_called_once()

    def test_stop_when_not_running_is_noop(self, mock_app):
        """Stop when not running does nothing."""
        mock_app._running = False

        mock_app.stop()

        mock_app.detector.stop.assert_not_called()

    def test_stop_is_idempotent(self, mock_app):
        """Stop can be called multiple times safely."""
        mock_app._running = True

        mock_app.stop()
        mock_app.stop()
        mock_app.stop()

        # Should only call detector.stop once
        assert mock_app.detector.stop.call_count == 1


# Integration marker for tests requiring actual hardware
@pytest.mark.integration
class TestE2EHardwareIntegration:
    """
    Integration tests that require actual hardware (microphone).

    These tests are marked with @pytest.mark.integration and skipped by default.
    Run with: pytest -m integration
    """

    @pytest.fixture(autouse=True)
    def check_hardware(self):
        """Skip if required hardware is not available."""
        pytest.skip("Hardware integration tests - run manually with microphone")

    def test_real_hotkey_detection(self):
        """Test actual Fn key detection."""
        pass  # Placeholder for manual testing

    def test_real_audio_recording(self):
        """Test actual audio recording from microphone."""
        pass  # Placeholder for manual testing

    def test_real_transcription(self):
        """Test actual transcription with Groq API."""
        pass  # Placeholder for manual testing
