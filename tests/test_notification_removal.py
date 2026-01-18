"""
Test suite for verifying notification removal from HotkeyDetector.

This test suite verifies that:
1. The HotkeyDetector no longer imports subprocess
2. The _show_indicator method has been removed
3. No osascript notifications are sent during recording events
4. The detector still functions correctly for Fn key detection

Tests are organized as:
- Static analysis tests (module structure)
- Behavior tests (no notifications during recording)
- Property-based tests using Hypothesis
"""

import unittest
from unittest.mock import MagicMock, patch, Mock
import inspect
import sys

import pytest
from hypothesis import given, strategies as st, settings


class TestNotificationRemovalModuleStructure(unittest.TestCase):
    """Static tests verifying notification code has been removed."""

    def test_no_subprocess_import(self):
        """Verify subprocess is not imported by hotkey_detector."""
        # Import the module
        from handfree import hotkey_detector

        # Check that subprocess is not in the module's namespace
        self.assertNotIn('subprocess', dir(hotkey_detector))

        # Check the actual imports in the module
        module_source = inspect.getsource(hotkey_detector)
        self.assertNotIn('import subprocess', module_source)

    def test_no_show_indicator_method(self):
        """Verify _show_indicator method has been removed."""
        from handfree.hotkey_detector import HotkeyDetector

        self.assertFalse(
            hasattr(HotkeyDetector, '_show_indicator'),
            "HotkeyDetector should not have _show_indicator method"
        )

    def test_no_display_notification_in_source(self):
        """Verify no 'display notification' osascript command in source."""
        from handfree import hotkey_detector

        module_source = inspect.getsource(hotkey_detector)
        self.assertNotIn('display notification', module_source)

    def test_no_osascript_in_source(self):
        """Verify no osascript calls in source."""
        from handfree import hotkey_detector

        module_source = inspect.getsource(hotkey_detector)
        self.assertNotIn('osascript', module_source)


# Mock Quartz constants for testing
class MockQuartz:
    """Mock Quartz module for testing without macOS dependencies."""
    kCGSessionEventTap = 0
    kCGHeadInsertEventTap = 0
    kCGEventTapOptionListenOnly = 0
    kCGEventFlagsChanged = 12
    kCGKeyboardEventKeycode = 9

    @staticmethod
    def CGEventGetIntegerValueField(event, field):
        if hasattr(event, '_keycode'):
            return event._keycode
        return 0

    @staticmethod
    def CGEventTapEnable(tap, enable):
        pass


class MockCGEvent:
    """Mock CGEvent for testing."""
    def __init__(self, keycode: int = 0, flags: int = 0):
        self._keycode = keycode
        self._flags = flags


# Constants matching the real implementation
FN_KEYCODE = 63
FN_FLAG = 0x800000


class TestHotkeyDetectorNoNotifications(unittest.TestCase):
    """Tests verifying no notifications are sent during recording events."""

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    @patch('subprocess.run')
    def test_fn_press_does_not_call_subprocess(
        self, mock_subprocess_run, mock_get_flags, mock_tap_create
    ):
        """Test that pressing Fn key does not call subprocess."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = HotkeyDetector(on_start, on_stop)

        # Simulate Fn key press
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG

        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        # Verify no subprocess was called
        mock_subprocess_run.assert_not_called()

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    @patch('subprocess.run')
    def test_fn_release_does_not_call_subprocess(
        self, mock_subprocess_run, mock_get_flags, mock_tap_create
    ):
        """Test that releasing Fn key does not call subprocess."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = HotkeyDetector(on_start, on_stop)
        detector._is_recording = True  # Simulate already recording

        # Simulate Fn key release
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = 0

        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        # Verify no subprocess was called
        mock_subprocess_run.assert_not_called()

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    @patch('subprocess.run')
    def test_full_recording_cycle_no_subprocess(
        self, mock_subprocess_run, mock_get_flags, mock_tap_create
    ):
        """Test complete recording cycle does not call subprocess."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = HotkeyDetector(on_start, on_stop)

        event = MockCGEvent(keycode=FN_KEYCODE)

        # Press Fn
        mock_get_flags.return_value = FN_FLAG
        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        # Release Fn
        mock_get_flags.return_value = 0
        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        # Verify callbacks were called but no subprocess
        on_start.assert_called_once()
        on_stop.assert_called_once()
        mock_subprocess_run.assert_not_called()


class TestHotkeyDetectorStillFunctions(unittest.TestCase):
    """Tests verifying the detector still functions correctly after notification removal."""

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    def test_fn_press_starts_recording(self, mock_get_flags, mock_tap_create):
        """Test Fn key press still starts recording."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = HotkeyDetector(on_start, on_stop)

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG

        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_start.assert_called_once()
        self.assertTrue(detector.is_recording)

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    def test_fn_release_stops_recording(self, mock_get_flags, mock_tap_create):
        """Test Fn key release still stops recording."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = HotkeyDetector(on_start, on_stop)
        detector._is_recording = True

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = 0

        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_stop.assert_called_once()
        self.assertFalse(detector.is_recording)

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    def test_event_still_passed_through(self, mock_get_flags, mock_tap_create):
        """Test events are still passed through correctly."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        detector = HotkeyDetector(lambda: None, lambda: None)

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = 0

        result = detector._event_callback(None, kCGEventFlagsChanged, event, None)

        self.assertEqual(result, event)


class TestHotkeyDetectorPropertyBased:
    """Property-based tests using Hypothesis."""

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    @patch('subprocess.run')
    @given(st.lists(st.booleans(), min_size=1, max_size=50))
    @settings(max_examples=30)
    def test_no_subprocess_in_any_sequence(
        self, mock_subprocess_run, mock_get_flags, mock_tap_create, fn_states
    ):
        """Property: subprocess is never called regardless of Fn key sequence."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        detector = HotkeyDetector(lambda: None, lambda: None)

        for fn_pressed in fn_states:
            event = MockCGEvent(keycode=FN_KEYCODE)
            mock_get_flags.return_value = FN_FLAG if fn_pressed else 0
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

        mock_subprocess_run.assert_not_called()

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_callbacks_still_called_correctly(
        self, mock_get_flags, mock_tap_create, num_cycles
    ):
        """Property: callbacks are called correct number of times."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = HotkeyDetector(on_start, on_stop)

        for _ in range(num_cycles):
            event = MockCGEvent(keycode=FN_KEYCODE)

            # Press Fn
            mock_get_flags.return_value = FN_FLAG
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

            # Release Fn
            mock_get_flags.return_value = 0
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

        assert on_start.call_count == num_cycles
        assert on_stop.call_count == num_cycles


class TestNoNotificationSideEffects(unittest.TestCase):
    """Tests that there are no other notification-related side effects."""

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    def test_no_threading_for_notifications(self, mock_tap_create):
        """Verify no extra threading is created for notifications."""
        from handfree.hotkey_detector import HotkeyDetector
        import threading

        initial_thread_count = threading.active_count()

        detector = HotkeyDetector(lambda: None, lambda: None)

        # Thread count should not increase just from creating detector
        # (run loop thread is only created on start())
        self.assertEqual(threading.active_count(), initial_thread_count)

    @patch('handfree.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.hotkey_detector.CGEventTapCreate')
    @patch('handfree.hotkey_detector.CGEventGetFlags')
    def test_callbacks_execute_immediately(self, mock_get_flags, mock_tap_create):
        """Verify callbacks execute synchronously, not in background thread."""
        from handfree.hotkey_detector import HotkeyDetector
        from handfree.hotkey_detector import kCGEventFlagsChanged

        execution_order = []

        def on_start():
            execution_order.append('start')

        detector = HotkeyDetector(on_start, lambda: None)

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG

        detector._event_callback(None, kCGEventFlagsChanged, event, None)
        execution_order.append('after_callback')

        # on_start should be called before 'after_callback'
        self.assertEqual(execution_order, ['start', 'after_callback'])


if __name__ == '__main__':
    unittest.main()
