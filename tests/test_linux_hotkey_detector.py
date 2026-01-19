"""
Test suite for Linux Hotkey Detector.

Comprehensive tests covering:
- Initialization and configuration
- Key press/release event handling
- Recording state management
- Key normalization (left/right variants)
- History toggle hotkey (Ctrl+H)
- Start/stop lifecycle
- Edge cases and error handling

Uses property-based testing with Hypothesis for state machine verification.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Set

import pytest
from hypothesis import given, strategies as st, settings, assume


class MockKey:
    """Mock pynput key for testing."""
    def __init__(self, name: str, char: str = None):
        self.name = name
        self.char = char

    def __eq__(self, other):
        if hasattr(other, 'name'):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"MockKey({self.name})"


# Create mock Key enum values
class MockKeyEnum:
    ctrl_l = MockKey('ctrl_l')
    ctrl_r = MockKey('ctrl_r')
    shift = MockKey('shift')
    shift_r = MockKey('shift_r')
    space = MockKey('space')
    alt = MockKey('alt')
    alt_r = MockKey('alt_r')
    enter = MockKey('enter')
    esc = MockKey('esc')


class MockKeyCode:
    """Mock KeyCode for character keys."""
    def __init__(self, char: str):
        self.char = char

    def __repr__(self):
        return f"MockKeyCode({self.char})"


class TestLinuxHotkeyDetectorInitialization(unittest.TestCase):
    """Tests for LinuxHotkeyDetector initialization."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_initialization_with_callbacks(self, mock_kb):
        """Test detector initializes with required callbacks."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()

        detector = LinuxHotkeyDetector(on_start, on_stop)

        self.assertEqual(detector.on_start, on_start)
        self.assertEqual(detector.on_stop, on_stop)
        self.assertIsNone(detector.on_history_toggle)
        self.assertFalse(detector.is_recording)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_initialization_with_history_toggle(self, mock_kb):
        """Test detector initializes with optional history toggle callback."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        on_start = MagicMock()
        on_stop = MagicMock()
        on_history = MagicMock()

        detector = LinuxHotkeyDetector(on_start, on_stop, on_history)

        self.assertEqual(detector.on_history_toggle, on_history)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_initial_state(self, mock_kb):
        """Test detector has correct initial state."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        self.assertIsNone(detector._listener)
        self.assertEqual(len(detector._pressed_keys), 0)
        self.assertFalse(detector._is_recording)


class TestLinuxHotkeyDetectorDescriptions(unittest.TestCase):
    """Tests for hotkey description methods."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_hotkey_description(self, mock_kb):
        """Test correct hotkey description is returned."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        self.assertEqual(detector.get_hotkey_description(), "Ctrl+Shift+Space")

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_history_toggle_description(self, mock_kb):
        """Test correct history toggle description is returned."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        self.assertEqual(detector.get_history_toggle_description(), "Ctrl+H")


class TestLinuxHotkeyDetectorKeyNormalization(unittest.TestCase):
    """Tests for key normalization."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_normalize_ctrl_r_to_ctrl_l(self, mock_kb):
        """Test right Ctrl is normalized to left Ctrl."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        normalized = detector._normalize_key(MockKeyEnum.ctrl_r)

        self.assertEqual(normalized, MockKeyEnum.ctrl_l)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_normalize_shift_r_to_shift(self, mock_kb):
        """Test right Shift is normalized to left Shift."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        normalized = detector._normalize_key(MockKeyEnum.shift_r)

        self.assertEqual(normalized, MockKeyEnum.shift)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_normalize_other_keys_unchanged(self, mock_kb):
        """Test other keys are not modified during normalization."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        for key in [MockKeyEnum.space, MockKeyEnum.ctrl_l, MockKeyEnum.shift]:
            normalized = detector._normalize_key(key)
            self.assertEqual(normalized, key)


class TestLinuxHotkeyDetectorTriggerDetection(unittest.TestCase):
    """Tests for trigger key combination detection."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_check_trigger_all_keys_pressed(self, mock_kb):
        """Test trigger returns True when all required keys are pressed."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Simulate pressing Ctrl+Shift+Space
        detector._pressed_keys = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        self.assertTrue(detector._check_trigger())

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_check_trigger_right_ctrl_variant(self, mock_kb):
        """Test trigger works with right Ctrl key."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Simulate pressing RightCtrl+Shift+Space
        detector._pressed_keys = {MockKeyEnum.ctrl_r, MockKeyEnum.shift, MockKeyEnum.space}

        self.assertTrue(detector._check_trigger())

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_check_trigger_partial_keys(self, mock_kb):
        """Test trigger returns False when only some keys are pressed."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        # Only Ctrl pressed
        detector._pressed_keys = {MockKeyEnum.ctrl_l}
        self.assertFalse(detector._check_trigger())

        # Ctrl+Shift pressed (no Space)
        detector._pressed_keys = {MockKeyEnum.ctrl_l, MockKeyEnum.shift}
        self.assertFalse(detector._check_trigger())

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_check_trigger_no_keys(self, mock_kb):
        """Test trigger returns False when no keys are pressed."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = set()

        self.assertFalse(detector._check_trigger())


class TestLinuxHotkeyDetectorCtrlCheck(unittest.TestCase):
    """Tests for Ctrl key detection."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_is_ctrl_pressed_left(self, mock_kb):
        """Test detects left Ctrl as pressed."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = {MockKeyEnum.ctrl_l}

        self.assertTrue(detector._is_ctrl_pressed())

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_is_ctrl_pressed_right(self, mock_kb):
        """Test detects right Ctrl as pressed."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = {MockKeyEnum.ctrl_r}

        self.assertTrue(detector._is_ctrl_pressed())

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_is_ctrl_not_pressed(self, mock_kb):
        """Test detects when no Ctrl key is pressed."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = {MockKeyEnum.shift, MockKeyEnum.space}

        self.assertFalse(detector._is_ctrl_pressed())


class TestLinuxHotkeyDetectorKeyPress(unittest.TestCase):
    """Tests for key press event handling."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_press_adds_key(self, mock_kb):
        """Test key press adds key to pressed set."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._on_press(MockKeyEnum.ctrl_l)

        self.assertIn(MockKeyEnum.ctrl_l, detector._pressed_keys)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_press_triggers_recording_start(self, mock_kb):
        """Test pressing all trigger keys starts recording."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Press Ctrl, Shift, then Space
        detector._on_press(MockKeyEnum.ctrl_l)
        detector._on_press(MockKeyEnum.shift)
        detector._on_press(MockKeyEnum.space)

        on_start.assert_called_once()
        self.assertTrue(detector.is_recording)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_press_no_double_start(self, mock_kb):
        """Test pressing trigger while already recording doesn't call start again."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        detector = LinuxHotkeyDetector(on_start, lambda: None)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Start recording
        detector._pressed_keys = {MockKeyEnum.ctrl_l, MockKeyEnum.shift}
        detector._on_press(MockKeyEnum.space)

        # Press another key while recording
        detector._on_press(MockKeyEnum.alt)

        self.assertEqual(on_start.call_count, 1)


class TestLinuxHotkeyDetectorKeyRelease(unittest.TestCase):
    """Tests for key release event handling."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_release_removes_key(self, mock_kb):
        """Test key release removes key from pressed set."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = {MockKeyEnum.ctrl_l, MockKeyEnum.shift}
        detector._on_release(MockKeyEnum.ctrl_l)

        self.assertNotIn(MockKeyEnum.ctrl_l, detector._pressed_keys)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_release_triggers_recording_stop(self, mock_kb):
        """Test releasing a trigger key stops recording."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)

        # Start recording
        detector._pressed_keys = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}
        detector._is_recording = True

        # Release Space
        detector._on_release(MockKeyEnum.space)

        on_stop.assert_called_once()
        self.assertFalse(detector.is_recording)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_release_no_stop_if_not_recording(self, mock_kb):
        """Test releasing keys when not recording doesn't call stop."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, on_stop)

        detector._pressed_keys = {MockKeyEnum.ctrl_l}
        detector._on_release(MockKeyEnum.ctrl_l)

        on_stop.assert_not_called()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_on_release_nonexistent_key(self, mock_kb):
        """Test releasing a key that wasn't pressed doesn't raise error."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = set()
        # Should not raise
        detector._on_release(MockKeyEnum.space)


class TestLinuxHotkeyDetectorHistoryToggle(unittest.TestCase):
    """Tests for history toggle hotkey (Ctrl+H)."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_history_toggle_on_ctrl_h(self, mock_kb):
        """Test Ctrl+H triggers history toggle."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_history = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, lambda: None, on_history)

        # Press Ctrl
        detector._on_press(MockKeyEnum.ctrl_l)

        # Press 'h' key
        h_key = MockKeyCode('h')
        detector._on_press(h_key)

        on_history.assert_called_once()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_history_toggle_uppercase_h(self, mock_kb):
        """Test Ctrl+H works with uppercase H."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_history = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, lambda: None, on_history)

        detector._on_press(MockKeyEnum.ctrl_l)

        h_key = MockKeyCode('H')
        detector._on_press(h_key)

        on_history.assert_called_once()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_history_toggle_not_triggered_with_shift(self, mock_kb):
        """Test Ctrl+Shift+H does not trigger history toggle."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_history = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, lambda: None, on_history)

        detector._on_press(MockKeyEnum.ctrl_l)
        detector._on_press(MockKeyEnum.shift)

        h_key = MockKeyCode('h')
        detector._on_press(h_key)

        on_history.assert_not_called()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_history_toggle_not_triggered_without_ctrl(self, mock_kb):
        """Test 'H' alone does not trigger history toggle."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_history = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, lambda: None, on_history)

        h_key = MockKeyCode('h')
        detector._on_press(h_key)

        on_history.assert_not_called()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_history_toggle_no_callback_configured(self, mock_kb):
        """Test no error when history toggle not configured."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)  # No history callback

        detector._on_press(MockKeyEnum.ctrl_l)

        h_key = MockKeyCode('h')
        # Should not raise
        detector._on_press(h_key)


class TestLinuxHotkeyDetectorLifecycle(unittest.TestCase):
    """Tests for start/stop lifecycle."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_start_creates_listener(self, mock_kb):
        """Test start() creates and starts a listener."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_listener_instance = MagicMock()
        mock_kb.Listener.return_value = mock_listener_instance

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)
        detector.start()

        mock_kb.Listener.assert_called_once()
        mock_listener_instance.start.assert_called_once()
        self.assertEqual(detector._listener, mock_listener_instance)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_stop_stops_listener(self, mock_kb):
        """Test stop() stops and clears the listener."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_listener_instance = MagicMock()
        mock_kb.Listener.return_value = mock_listener_instance

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)
        detector.start()
        detector.stop()

        mock_listener_instance.stop.assert_called_once()
        self.assertIsNone(detector._listener)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_stop_clears_pressed_keys(self, mock_kb):
        """Test stop() clears pressed keys set."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        detector._pressed_keys = {MockKeyEnum.ctrl_l, MockKeyEnum.shift}
        detector.stop()

        self.assertEqual(len(detector._pressed_keys), 0)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_stop_without_start(self, mock_kb):
        """Test stop() without start() doesn't raise error."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        # Should not raise
        detector.stop()


class TestLinuxHotkeyDetectorStateMachine(unittest.TestCase):
    """Property-based tests for state machine behavior."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_full_recording_cycle(self, mock_kb):
        """Test complete recording cycle: press all -> recording -> release any -> stop."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Start recording
        detector._on_press(MockKeyEnum.ctrl_l)
        detector._on_press(MockKeyEnum.shift)
        detector._on_press(MockKeyEnum.space)

        self.assertTrue(detector.is_recording)
        on_start.assert_called_once()

        # Stop recording by releasing Space
        detector._on_release(MockKeyEnum.space)

        self.assertFalse(detector.is_recording)
        on_stop.assert_called_once()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_multiple_recording_cycles(self, mock_kb):
        """Test multiple consecutive recording cycles."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        for cycle in range(3):
            # Start recording
            detector._on_press(MockKeyEnum.ctrl_l)
            detector._on_press(MockKeyEnum.shift)
            detector._on_press(MockKeyEnum.space)

            # Stop recording
            detector._on_release(MockKeyEnum.space)
            detector._on_release(MockKeyEnum.shift)
            detector._on_release(MockKeyEnum.ctrl_l)

        self.assertEqual(on_start.call_count, 3)
        self.assertEqual(on_stop.call_count, 3)


class TestLinuxHotkeyDetectorStateMachineHypothesis:
    """Property-based tests using Hypothesis."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    @given(st.lists(st.booleans(), min_size=3, max_size=3))
    @settings(max_examples=50)
    def test_recording_state_consistency(self, mock_kb, key_states):
        """Test recording state is consistent with pressed keys."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        keys = [MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space]

        for key, should_press in zip(keys, key_states):
            if should_press:
                detector._on_press(key)
            else:
                detector._on_release(key)

        all_pressed = all(key_states)
        if all_pressed:
            assert detector.is_recording is True


class TestLinuxHotkeyDetectorEdgeCases(unittest.TestCase):
    """Edge case tests."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_rapid_key_events(self, mock_kb):
        """Test rapid key press/release events are handled correctly."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        on_stop = MagicMock()
        detector = LinuxHotkeyDetector(on_start, on_stop)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Rapid press and release
        for _ in range(10):
            detector._on_press(MockKeyEnum.ctrl_l)
            detector._on_press(MockKeyEnum.shift)
            detector._on_press(MockKeyEnum.space)
            detector._on_release(MockKeyEnum.space)
            detector._on_release(MockKeyEnum.shift)
            detector._on_release(MockKeyEnum.ctrl_l)

        self.assertEqual(on_start.call_count, 10)
        self.assertEqual(on_stop.call_count, 10)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_key_without_char_attribute(self, mock_kb):
        """Test key without char attribute doesn't cause error in history toggle check."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_history = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, lambda: None, on_history)

        detector._on_press(MockKeyEnum.ctrl_l)

        # Press a key without char attribute (like function keys)
        class KeyWithoutChar:
            pass

        detector._on_press(KeyWithoutChar())

        on_history.assert_not_called()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_key_with_none_char(self, mock_kb):
        """Test key with None char attribute doesn't trigger history toggle."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_history = MagicMock()
        detector = LinuxHotkeyDetector(lambda: None, lambda: None, on_history)

        detector._on_press(MockKeyEnum.ctrl_l)

        key_with_none_char = MockKeyCode(None)
        key_with_none_char.char = None
        detector._on_press(key_with_none_char)

        on_history.assert_not_called()


class TestLinuxHotkeyDetectorWaylandConsiderations(unittest.TestCase):
    """Tests specific to Linux/Wayland considerations."""

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_inherits_from_base_class(self, mock_kb):
        """Test LinuxHotkeyDetector inherits from HotkeyDetectorBase."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector
        from context_aware_whisper.platform.base import HotkeyDetectorBase

        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        self.assertIsInstance(detector, HotkeyDetectorBase)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_trigger_keys_matches_specification(self, mock_kb):
        """Test trigger keys have expected count (Ctrl+Shift+Space)."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        detector = LinuxHotkeyDetector(lambda: None, lambda: None)

        # Verify the trigger keys constant has 3 keys (ctrl_l, shift, space)
        self.assertEqual(len(detector.TRIGGER_KEYS), 3)

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_right_shift_normalization_in_trigger(self, mock_kb):
        """Test right Shift works with trigger combination."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        detector = LinuxHotkeyDetector(on_start, lambda: None)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Press with right shift variant
        detector._on_press(MockKeyEnum.ctrl_l)
        detector._on_press(MockKeyEnum.shift_r)
        detector._on_press(MockKeyEnum.space)

        on_start.assert_called_once()

    @patch('context_aware_whisper.platform.linux.hotkey_detector.keyboard')
    def test_mixed_left_right_modifiers(self, mock_kb):
        """Test mixing left and right modifier keys."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector

        mock_kb.Key = MockKeyEnum
        on_start = MagicMock()
        detector = LinuxHotkeyDetector(on_start, lambda: None)
        # Patch TRIGGER_KEYS to use our mock values
        detector.TRIGGER_KEYS = {MockKeyEnum.ctrl_l, MockKeyEnum.shift, MockKeyEnum.space}

        # Mix right ctrl and right shift
        detector._on_press(MockKeyEnum.ctrl_r)
        detector._on_press(MockKeyEnum.shift_r)
        detector._on_press(MockKeyEnum.space)

        on_start.assert_called_once()


if __name__ == '__main__':
    unittest.main()
