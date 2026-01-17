"""
Test script for MuteDetector
Tests AirPods mute/unmute detection by printing state changes.
"""

from mute_detector import MuteDetector
from Foundation import NSRunLoop, NSDate, NSDefaultRunLoopMode


def on_mute():
    """Callback when AirPods are muted."""
    print("MUTED")


def on_unmute():
    """Callback when AirPods are unmuted."""
    print("UNMUTED")


def main():
    """Main test function."""
    detector = MuteDetector(on_mute=on_mute, on_unmute=on_unmute)

    try:
        detector.start()
        print("Listening for mute events. Press Ctrl+C to exit.")
        print("Press your AirPods stem to toggle mute/unmute state.")
        print("")

        # Run event loop
        while True:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
    except KeyboardInterrupt:
        print("\nStopping detector...")
        detector.stop()
        print("Stopped.")
    except Exception as e:
        print(f"Error: {e}")
        detector.stop()


if __name__ == "__main__":
    main()
