"""
Manual test script for AudioRecorder.
Record audio for 3 seconds and save to file for playback verification.
"""

import time
from audio_recorder import AudioRecorder


def main():
    """Test audio recording with real microphone input."""
    recorder = AudioRecorder()

    print("=" * 50)
    print("AudioRecorder Manual Test")
    print("=" * 50)
    print("\nThis will record 3 seconds of audio from your microphone.")
    print("Speak or make noise to test the recording.\n")

    input("Press Enter to start recording...")

    print("\n🎤 Recording for 3 seconds...")
    recorder.start_recording()

    # Record for 3 seconds
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    audio_bytes = recorder.stop_recording()
    duration = recorder.get_duration()

    print(f"\n✅ Recording stopped")
    print(f"   Recorded {len(audio_bytes)} bytes ({duration:.1f} seconds)")

    # Save for playback verification
    output_file = "test_recording.wav"
    with open(output_file, "wb") as f:
        f.write(audio_bytes)

    print(f"   Saved to {output_file}")
    print("\n" + "=" * 50)
    print("To verify quality, play the file:")
    print(f"  afplay {output_file}")
    print("=" * 50)


if __name__ == "__main__":
    main()
