"""
Demo script for the transcriber module.

This demonstrates how to use the AudioRecorder with Transcriber.
Note: Requires a valid GROQ_API_KEY to actually transcribe.
"""

import time
import os
from audio_recorder import AudioRecorder
from transcriber import Transcriber, TranscriptionError


def demo_record_and_transcribe():
    """Demo: Record audio and transcribe it."""
    print("=" * 60)
    print("HandFree Transcriber Demo")
    print("=" * 60)
    print()

    # Check for API key
    if not os.environ.get("GROQ_API_KEY"):
        print("⚠️  GROQ_API_KEY not set in environment")
        print("   This demo will record audio but cannot transcribe without a valid API key.")
        print()
        print("To run the full demo:")
        print("  export GROQ_API_KEY=your_key_here")
        print("  python demo_transcriber.py")
        print()
        transcribe_enabled = False
    else:
        transcribe_enabled = True
        print("✓ GROQ_API_KEY found")
        print()

    # Initialize modules
    recorder = AudioRecorder()
    if transcribe_enabled:
        try:
            transcriber = Transcriber()
            print("✓ Transcriber initialized")
        except ValueError as e:
            print(f"✗ Transcriber initialization failed: {e}")
            transcribe_enabled = False

    print()
    print("Recording for 3 seconds...")
    print("Speak now!")
    print()

    # Record audio
    recorder.start_recording()
    time.sleep(3)
    audio_bytes = recorder.stop_recording()

    duration = recorder.get_duration()
    print(f"✓ Recorded {len(audio_bytes)} bytes ({duration:.1f}s)")
    print()

    if transcribe_enabled and audio_bytes:
        print("Sending to Groq Whisper API for transcription...")
        try:
            start_time = time.time()
            text = transcriber.transcribe(audio_bytes)
            elapsed = time.time() - start_time

            print()
            print("=" * 60)
            print("TRANSCRIPTION RESULT:")
            print("=" * 60)
            print(f"{text}")
            print("=" * 60)
            print()
            print(f"⏱️  Transcription latency: {elapsed*1000:.0f}ms")

        except TranscriptionError as e:
            print(f"✗ Transcription failed: {e}")
    else:
        print("Skipping transcription (no API key or no audio)")

    print()
    print("Demo complete!")


if __name__ == "__main__":
    demo_record_and_transcribe()
