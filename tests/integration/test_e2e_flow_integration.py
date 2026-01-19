"""End-to-end integration tests."""

import pytest

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.requires_whisper
class TestE2EFlow:
    """End-to-end flow tests requiring whisper model."""

    @pytest.fixture(autouse=True)
    def preserve_clipboard(self):
        """Preserve and restore clipboard contents around tests."""
        if not PYPERCLIP_AVAILABLE:
            yield
            return

        try:
            original = pyperclip.paste()
        except Exception:
            original = ""
        yield
        try:
            pyperclip.copy(original)
        except Exception:
            pass

    def test_audio_file_to_clipboard(self, audio_fixtures_dir):
        """Test complete flow: audio file -> transcription -> clipboard."""
        from context_aware_whisper.local_transcriber import LocalTranscriber
        from context_aware_whisper.output_handler import OutputHandler

        audio_path = audio_fixtures_dir / "hello_world.wav"
        if not audio_path.exists():
            pytest.skip("Fixture hello_world.wav not found")

        # Transcribe
        transcriber = LocalTranscriber(model_name="base.en")
        text = transcriber.transcribe(audio_path.read_bytes())

        # Note: tone fallback fixtures may produce empty transcription
        # Just verify the flow works without error
        assert isinstance(text, str), "Transcription should return string"

        # Copy to clipboard (even if empty)
        output = OutputHandler()
        output.copy_to_clipboard(text)

        # Verify clipboard contains our text
        # Note: empty string may not be settable on all platforms
        if PYPERCLIP_AVAILABLE and text:
            assert pyperclip.paste() == text

    def test_silence_produces_minimal_output(self, audio_fixtures_dir):
        """Test that silence audio doesn't produce false transcriptions."""
        from context_aware_whisper.local_transcriber import LocalTranscriber

        audio_path = audio_fixtures_dir / "silence.wav"
        if not audio_path.exists():
            pytest.skip("Fixture silence.wav not found")

        transcriber = LocalTranscriber(model_name="base.en")
        text = transcriber.transcribe(audio_path.read_bytes())

        # Silence should produce very little or no output
        assert len(text.strip()) < 30, \
            f"Silence produced unexpected output: {text}"


@pytest.mark.integration
@pytest.mark.requires_whisper
@pytest.mark.requires_microphone
class TestE2EWithRecording:
    """End-to-end tests requiring both microphone and whisper."""

    def test_record_transcribe_clipboard(self, audio_fixtures_dir):
        """Test complete flow: mic recording -> transcription -> clipboard.

        Note: This test records actual audio, so results depend on environment.
        """
        import time
        from context_aware_whisper.audio_recorder import AudioRecorder
        from context_aware_whisper.local_transcriber import LocalTranscriber
        from context_aware_whisper.output_handler import OutputHandler

        # Record
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()
        time.sleep(1.0)  # Record 1 second
        wav_bytes = recorder.stop_recording()

        assert wav_bytes[:4] == b'RIFF', "Invalid WAV from recording"

        # Transcribe
        transcriber = LocalTranscriber(model_name="base.en")
        text = transcriber.transcribe(wav_bytes)

        # Result depends on what was recorded - just verify it runs
        assert isinstance(text, str)

        # Copy to clipboard
        output = OutputHandler()
        output.copy_to_clipboard(text)


@pytest.mark.integration
class TestStateTransitions:
    """Test state transition logic."""

    def test_idle_to_recording_state(self):
        """Test transition from IDLE to RECORDING."""
        from context_aware_whisper.audio_recorder import AudioRecorder

        recorder = AudioRecorder()

        # Should start in not-recording state
        assert not recorder.is_recording

        # After start, should be recording
        recorder.start_recording()
        assert recorder.is_recording

        # After stop, should not be recording
        recorder.stop_recording()
        assert not recorder.is_recording

    def test_multiple_state_transitions(self):
        """Test multiple state transitions work correctly."""
        from context_aware_whisper.audio_recorder import AudioRecorder

        recorder = AudioRecorder()

        for _ in range(3):
            assert not recorder.is_recording
            recorder.start_recording()
            assert recorder.is_recording
            recorder.stop_recording()
            assert not recorder.is_recording
