"""
Test suite for macOS Hotkey Detector.

Comprehensive tests covering:
- Initialization and configuration
- Event callback handling
- Fn key detection logic
- Cmd+H history toggle detection
- Recording state management
- Start/stop lifecycle
- Edge cases and error handling

Uses property-based testing with Hypothesis for state machine verification.
"""

import unittest
from unittest.mock import MagicMock, patch, Mock
from typing import Optional

import pytest
from hypothesis import given, strategies as st, settings, assume


# Mock Quartz constants and functions
class MockQuartz:
    """Mock Quartz module for testing."""
    kCGSessionEventTap = 0
    kCGHeadInsertEventTap = 0
    kCGEventTapOptionListenOnly = 0
    kCGEventFlagsChanged = 12
    kCGEventKeyDown = 10
    kCGKeyboardEventKeycode = 9
    kCGEventFlagMaskCommand = 0x100000

    @staticmethod
    def CGEventGetIntegerValueField(event, field):
        if hasattr(event, '_keycode'):
            return event._keycode
        return 0

    @staticmethod
    def CGEventTapEnable(tap, enable):
        pass


# Create mock event objects
class MockCGEvent:
    """Mock CGEvent for testing."""
    def __init__(self, keycode: int = 0, flags: int = 0):
        self._keycode = keycode
        self._flags = flags


# Constants matching the real implementation
FN_KEYCODE = 63
FN_FLAG = 0x800000
H_KEYCODE = 4
CMD_FLAG = 0x100000  # kCGEventFlagMaskCommand


class TestMacOSHotkeyDetectorInitialization(unittest.TestCase):
    """Tests for MacOSHotkeyDetector initialization."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_initialization_with_callbacks(self, mock_tap_create):
        """Test detector initializes with required callbacks."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()

        detector = MacOSHotkeyDetector(on_start, on_stop)

        self.assertEqual(detector.on_start, on_start)
        self.assertEqual(detector.on_stop, on_stop)
        self.assertIsNone(detector.on_history_toggle)
        self.assertFalse(detector.is_recording)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_initialization_with_history_toggle(self, mock_tap_create):
        """Test detector initializes with optional history toggle callback."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()
        on_history = MagicMock()

        detector = MacOSHotkeyDetector(on_start, on_stop, on_history)

        self.assertEqual(detector.on_history_toggle, on_history)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_initial_state(self, mock_tap_create):
        """Test detector has correct initial state."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        self.assertIsNone(detector._tap)
        self.assertFalse(detector._running)
        self.assertIsNone(detector._thread)
        self.assertFalse(detector._is_recording)


class TestMacOSHotkeyDetectorDescriptions(unittest.TestCase):
    """Tests for hotkey description methods."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_hotkey_description(self, mock_tap_create):
        """Test correct hotkey description is returned."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        self.assertEqual(detector.get_hotkey_description(), "Fn/Globe key")

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_history_toggle_description(self, mock_tap_create):
        """Test correct history toggle description is returned."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        self.assertEqual(detector.get_history_toggle_description(), "Cmd+H")


class TestMacOSHotkeyDetectorEventCallback(unittest.TestCase):
    """Tests for CGEvent callback handling."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_fn_key_press_starts_recording(self, mock_get_flags, mock_tap_create):
        """Test Fn key press starts recording."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        # Create event with Fn keycode and Fn flag pressed
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG  # Fn is pressed

        result = detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_start.assert_called_once()
        self.assertTrue(detector.is_recording)
        self.assertEqual(result, event)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_fn_key_release_stops_recording(self, mock_get_flags, mock_tap_create):
        """Test Fn key release stops recording."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)
        detector._is_recording = True  # Already recording

        # Create event with Fn keycode but Fn flag NOT pressed
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = 0  # Fn is released

        result = detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_stop.assert_called_once()
        self.assertFalse(detector.is_recording)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_fn_press_ignored_when_already_recording(self, mock_get_flags, mock_tap_create):
        """Test pressing Fn while already recording doesn't call start again."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        detector = MacOSHotkeyDetector(on_start, lambda: None)
        detector._is_recording = True  # Already recording

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG  # Fn is pressed

        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_start.assert_not_called()  # Should not call start again

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_fn_release_ignored_when_not_recording(self, mock_get_flags, mock_tap_create):
        """Test releasing Fn when not recording doesn't call stop."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, on_stop)
        detector._is_recording = False  # Not recording

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = 0  # Fn is released

        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_stop.assert_not_called()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_non_fn_key_ignored(self, mock_get_flags, mock_tap_create):
        """Test other keys don't trigger recording."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        # Create event with different keycode
        event = MockCGEvent(keycode=50)  # Not Fn key
        mock_get_flags.return_value = 0

        result = detector._event_callback(None, kCGEventFlagsChanged, event, None)

        on_start.assert_not_called()
        on_stop.assert_not_called()


class TestMacOSHotkeyDetectorHistoryToggle(unittest.TestCase):
    """Tests for history toggle hotkey (Cmd+H)."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_h_triggers_history_toggle(self, mock_get_flags, mock_tap_create):
        """Test Cmd+H triggers history toggle."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        # Create event with H keycode and Cmd flag pressed
        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG  # Cmd is pressed

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_called_once()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_h_without_cmd_does_not_trigger(self, mock_get_flags, mock_tap_create):
        """Test 'H' alone does not trigger history toggle."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = 0  # No Cmd

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_not_called()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_other_key_does_not_trigger(self, mock_get_flags, mock_tap_create):
        """Test Cmd+other key does not trigger history toggle."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        # Cmd+J (not H)
        event = MockCGEvent(keycode=38)  # 'J' key
        mock_get_flags.return_value = CMD_FLAG

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_not_called()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_no_callback_configured_no_error(self, mock_get_flags, mock_tap_create):
        """Test no error when history toggle not configured."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)  # No history callback

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG

        # Should not raise
        detector._event_callback(None, kCGEventKeyDown, event, None)


class TestMacOSHotkeyDetectorLifecycle(unittest.TestCase):
    """Tests for start/stop lifecycle."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_start_sets_running_flag(self, mock_tap_create):
        """Test start() sets running flag and creates thread."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        with patch.object(detector, '_run_loop'), \
             patch('handfree.platform.macos.hotkey_detector.threading') as mock_threading:
            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            detector.start()

            self.assertTrue(detector._running)
            mock_threading.Thread.assert_called_once()
            mock_thread.start.assert_called_once()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_stop_clears_running_flag(self, mock_tap_create):
        """Test stop() clears running flag."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)
        detector._running = True
        detector._tap = MagicMock()

        detector.stop()

        self.assertFalse(detector._running)
        self.assertIsNone(detector._tap)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_stop_disables_tap(self, mock_tap_create):
        """Test stop() disables the event tap."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        mock_tap = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None)
        detector._running = True
        detector._tap = mock_tap

        with patch('handfree.platform.macos.hotkey_detector.Quartz') as mock_quartz:
            detector.stop()

            mock_quartz.CGEventTapEnable.assert_called_once_with(mock_tap, False)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_stop_without_start_no_error(self, mock_tap_create):
        """Test stop() without start() doesn't raise error."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        # Should not raise
        detector.stop()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_stop_with_none_tap_no_error(self, mock_tap_create):
        """Test stop() with None tap doesn't raise error."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)
        detector._running = True
        detector._tap = None

        # Should not raise
        detector.stop()


class TestMacOSHotkeyDetectorStateMachine(unittest.TestCase):
    """State machine tests."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_full_recording_cycle(self, mock_get_flags, mock_tap_create):
        """Test complete recording cycle: press Fn -> recording -> release Fn -> stop."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        # Press Fn
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG
        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        self.assertTrue(detector.is_recording)
        on_start.assert_called_once()

        # Release Fn
        mock_get_flags.return_value = 0
        detector._event_callback(None, kCGEventFlagsChanged, event, None)

        self.assertFalse(detector.is_recording)
        on_stop.assert_called_once()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_multiple_recording_cycles(self, mock_get_flags, mock_tap_create):
        """Test multiple consecutive recording cycles."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        for cycle in range(3):
            event = MockCGEvent(keycode=FN_KEYCODE)

            # Press Fn
            mock_get_flags.return_value = FN_FLAG
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

            # Release Fn
            mock_get_flags.return_value = 0
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

        self.assertEqual(on_start.call_count, 3)
        self.assertEqual(on_stop.call_count, 3)


class TestMacOSHotkeyDetectorRunLoop(unittest.TestCase):
    """Tests for CGEvent run loop."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz')
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventMaskBit')
    @patch('handfree.platform.macos.hotkey_detector.CFMachPortCreateRunLoopSource')
    @patch('handfree.platform.macos.hotkey_detector.CFRunLoopGetCurrent')
    @patch('handfree.platform.macos.hotkey_detector.CFRunLoopAddSource')
    @patch('handfree.platform.macos.hotkey_detector.CFRunLoopRunInMode')
    def test_run_loop_creates_event_tap(
        self, mock_run_in_mode, mock_add_source, mock_get_current,
        mock_create_source, mock_mask_bit, mock_tap_create, mock_quartz
    ):
        """Test _run_loop creates event tap correctly."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        mock_tap = MagicMock()
        mock_tap_create.return_value = mock_tap
        mock_source = MagicMock()
        mock_create_source.return_value = mock_source
        mock_loop = MagicMock()
        mock_get_current.return_value = mock_loop

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)
        detector._running = False  # Will exit loop immediately

        detector._run_loop()

        mock_tap_create.assert_called()
        self.assertEqual(detector._tap, mock_tap)

    @patch('handfree.platform.macos.hotkey_detector.Quartz')
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventMaskBit')
    def test_run_loop_handles_failed_tap_creation(
        self, mock_mask_bit, mock_tap_create, mock_quartz
    ):
        """Test _run_loop handles failed tap creation gracefully."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        mock_tap_create.return_value = None  # Failed to create tap

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)
        detector._running = True

        # Should not raise
        detector._run_loop()

        self.assertIsNone(detector._tap)


class TestMacOSHotkeyDetectorEdgeCases(unittest.TestCase):
    """Edge case tests."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_wrong_event_type_for_fn_ignored(self, mock_get_flags, mock_tap_create):
        """Test Fn key event with wrong event type is ignored."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_start = MagicMock()
        detector = MacOSHotkeyDetector(on_start, lambda: None)

        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG

        # Using kCGEventKeyDown instead of kCGEventFlagsChanged
        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_start.assert_not_called()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_h_with_other_modifiers(self, mock_get_flags, mock_tap_create):
        """Test Cmd+H with other modifiers (like Shift) still triggers."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        # Cmd + Shift + H (Shift flag = 0x20000)
        mock_get_flags.return_value = CMD_FLAG | 0x20000

        detector._event_callback(None, kCGEventKeyDown, event, None)

        # Cmd+H should still trigger even with shift held
        on_history.assert_called_once()

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_rapid_fn_key_events(self, mock_get_flags, mock_tap_create):
        """Test rapid Fn key press/release events are handled correctly."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        for _ in range(10):
            event = MockCGEvent(keycode=FN_KEYCODE)

            # Press
            mock_get_flags.return_value = FN_FLAG
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

            # Release
            mock_get_flags.return_value = 0
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

        self.assertEqual(on_start.call_count, 10)
        self.assertEqual(on_stop.call_count, 10)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_event_callback_returns_event(self, mock_tap_create):
        """Test event callback returns the event for pass-through."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        event = MockCGEvent(keycode=50)  # Random key

        with patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags', return_value=0):
            result = detector._event_callback(None, kCGEventFlagsChanged, event, None)

        self.assertEqual(result, event)


class TestMacOSHotkeyDetectorStateMachineHypothesis:
    """Property-based tests using Hypothesis."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    @given(st.lists(st.booleans(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_recording_state_consistency(self, mock_get_flags, mock_tap_create, fn_states):
        """Test recording state is always consistent with Fn key state."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

        for fn_pressed in fn_states:
            event = MockCGEvent(keycode=FN_KEYCODE)
            mock_get_flags.return_value = FN_FLAG if fn_pressed else 0
            detector._event_callback(None, kCGEventFlagsChanged, event, None)

        # Final state should match last Fn key state
        # (only if transitions happened properly)
        last_fn_pressed = fn_states[-1] if fn_states else False
        if last_fn_pressed:
            # If last press was Fn down, should be recording
            assert detector.is_recording is True
        else:
            # If last press was Fn up, should not be recording
            assert detector.is_recording is False

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags')
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_start_stop_callback_balance(self, mock_get_flags, mock_tap_create, num_cycles):
        """Test start and stop callbacks are called equal number of times."""
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventFlagsChanged

        on_start = MagicMock()
        on_stop = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop)

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


class TestMacOSHotkeyDetectorIntegration(unittest.TestCase):
    """Integration tests verifying detector works with platform factory."""

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('sys.platform', 'darwin')
    def test_factory_creates_macos_detector(self, mock_tap_create):
        """Test platform factory creates MacOSHotkeyDetector on macOS."""
        from handfree.platform import create_hotkey_detector
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = create_hotkey_detector(lambda: None, lambda: None)

        self.assertIsInstance(detector, MacOSHotkeyDetector)

    @patch('handfree.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('sys.platform', 'darwin')
    def test_factory_passes_history_toggle(self, mock_tap_create):
        """Test factory passes on_history_toggle to detector."""
        from handfree.platform import create_hotkey_detector

        on_history = MagicMock()
        detector = create_hotkey_detector(lambda: None, lambda: None, on_history)

        self.assertEqual(detector.on_history_toggle, on_history)


if __name__ == '__main__':
    unittest.main()
