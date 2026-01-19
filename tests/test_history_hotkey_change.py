"""
Test suite for History Hotkey Change (Cmd+H → Cmd+Shift+H).

Tests verify that:
1. History toggle now requires Cmd+Shift+H (not just Cmd+H)
2. Cmd+H alone no longer triggers history toggle
3. History panel UI shows correct hints (Cmd+Shift+H)
4. Description methods return updated hotkey strings

Property-based tests using Hypothesis verify:
- Various modifier combinations behave correctly
- State consistency across different key combinations
"""

import sys
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
    kCGEventFlagMaskShift = 0x20000

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
H_KEYCODE = 4  # 'h' key on macOS
CMD_FLAG = 0x100000  # kCGEventFlagMaskCommand
SHIFT_FLAG = 0x20000  # kCGEventFlagMaskShift


class TestHistoryHotkeyDescription(unittest.TestCase):
    """Tests for updated history hotkey description."""

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_history_toggle_description_is_cmd_shift_h(self, mock_tap_create):
        """Test history toggle description returns 'Cmd+Shift+H'."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        self.assertEqual(
            detector.get_history_toggle_description(),
            "Cmd+Shift+H"
        )

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_description_not_cmd_h(self, mock_tap_create):
        """Verify description is NOT the old 'Cmd+H'."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)

        self.assertNotEqual(
            detector.get_history_toggle_description(),
            "Cmd+H"
        )


class TestHistoryHotkeyDetection(unittest.TestCase):
    """Tests for history hotkey detection with Cmd+Shift+H."""

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_shift_h_triggers_history_toggle(self, mock_get_flags, mock_tap_create):
        """Test Cmd+Shift+H triggers history toggle."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG | SHIFT_FLAG  # Cmd+Shift pressed

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_called_once()

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_h_alone_does_not_trigger(self, mock_get_flags, mock_tap_create):
        """Test Cmd+H without Shift does NOT trigger history toggle."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG  # Only Cmd pressed, no Shift

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_not_called()

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_shift_h_alone_does_not_trigger(self, mock_get_flags, mock_tap_create):
        """Test Shift+H without Cmd does NOT trigger history toggle."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = SHIFT_FLAG  # Only Shift pressed, no Cmd

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_not_called()

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_h_alone_does_not_trigger(self, mock_get_flags, mock_tap_create):
        """Test H alone does NOT trigger history toggle."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = 0  # No modifiers

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_not_called()

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_shift_h_with_other_modifiers_still_triggers(self, mock_get_flags, mock_tap_create):
        """Test Cmd+Shift+H with additional modifiers (like Option) still triggers."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        # Cmd + Shift + Option (Option flag = 0x80000)
        mock_get_flags.return_value = CMD_FLAG | SHIFT_FLAG | 0x80000

        detector._event_callback(None, kCGEventKeyDown, event, None)

        on_history.assert_called_once()

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_no_callback_configured_no_error(self, mock_get_flags, mock_tap_create):
        """Test no error when history toggle not configured."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        detector = MacOSHotkeyDetector(lambda: None, lambda: None)  # No history callback

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG | SHIFT_FLAG

        # Should not raise
        detector._event_callback(None, kCGEventKeyDown, event, None)


class TestHistoryHotkeyConstants(unittest.TestCase):
    """Test that SHIFT_FLAG constant exists and is correct."""

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_shift_flag_constant_exists(self, mock_tap_create):
        """Test SHIFT_FLAG constant is defined in the module."""
        from context_aware_whisper.platform.macos import hotkey_detector

        self.assertTrue(hasattr(hotkey_detector, 'SHIFT_FLAG'))

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    def test_shift_flag_value(self, mock_tap_create):
        """Test SHIFT_FLAG has correct value (kCGEventFlagMaskShift)."""
        from context_aware_whisper.platform.macos import hotkey_detector

        # kCGEventFlagMaskShift should be 0x20000 (131072)
        self.assertEqual(
            hotkey_detector.SHIFT_FLAG,
            MockQuartz.kCGEventFlagMaskShift
        )


class TestHistoryHotkeyPropertyBased:
    """Property-based tests using Hypothesis for modifier combinations."""

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    @given(
        has_cmd=st.booleans(),
        has_shift=st.booleans(),
        has_option=st.booleans(),
        has_ctrl=st.booleans()
    )
    @settings(max_examples=50)
    def test_only_cmd_shift_triggers(
        self, mock_get_flags, mock_tap_create,
        has_cmd, has_shift, has_option, has_ctrl
    ):
        """Test that ONLY Cmd+Shift combination triggers history toggle."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        # Build flags
        flags = 0
        if has_cmd:
            flags |= CMD_FLAG
        if has_shift:
            flags |= SHIFT_FLAG
        if has_option:
            flags |= 0x80000  # Option key
        if has_ctrl:
            flags |= 0x40000  # Control key

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = flags

        detector._event_callback(None, kCGEventKeyDown, event, None)

        # Should only trigger if BOTH cmd AND shift are pressed
        if has_cmd and has_shift:
            assert on_history.call_count == 1
        else:
            assert on_history.call_count == 0

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    @given(num_presses=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_multiple_cmd_shift_h_presses(self, mock_get_flags, mock_tap_create, num_presses):
        """Test multiple Cmd+Shift+H presses all trigger correctly."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG | SHIFT_FLAG

        for _ in range(num_presses):
            detector._event_callback(None, kCGEventKeyDown, event, None)

        assert on_history.call_count == num_presses


class TestHistoryPanelUIHints(unittest.TestCase):
    """Tests for history panel UI showing correct hotkey hints."""

    def test_get_modifier_key_returns_cmd_on_darwin(self):
        """Test modifier key is 'Cmd' on macOS."""
        with patch.object(sys, 'platform', 'darwin'):
            # Re-import to get fresh value
            from context_aware_whisper.ui import history
            # Reload to pick up patched platform
            import importlib
            importlib.reload(history)

            modifier = history._get_modifier_key()
            self.assertEqual(modifier, "Cmd")

    def test_get_modifier_key_returns_ctrl_on_others(self):
        """Test modifier key is 'Ctrl' on non-macOS platforms."""
        with patch.object(sys, 'platform', 'linux'):
            from context_aware_whisper.ui import history
            import importlib
            importlib.reload(history)

            modifier = history._get_modifier_key()
            self.assertEqual(modifier, "Ctrl")


class TestHistoryHotkeyNotConflictWithSystem(unittest.TestCase):
    """Tests verifying Cmd+Shift+H doesn't conflict with system shortcuts."""

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_cmd_h_allowed_to_pass_through_for_system(self, mock_get_flags, mock_tap_create):
        """Test Cmd+H alone is not intercepted, allowing system 'Hide' to work."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        on_history = MagicMock()
        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history)

        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG  # Just Cmd+H

        result = detector._event_callback(None, kCGEventKeyDown, event, None)

        # Callback not called
        on_history.assert_not_called()
        # Event returned for pass-through
        self.assertEqual(result, event)


class TestHistoryHotkeyIntegration(unittest.TestCase):
    """Integration tests for the complete hotkey change."""

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_full_workflow_cmd_shift_h(self, mock_get_flags, mock_tap_create):
        """Test complete workflow: press Cmd+Shift+H toggles history."""
        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector, kCGEventKeyDown

        toggle_count = 0

        def on_history_toggle():
            nonlocal toggle_count
            toggle_count += 1

        detector = MacOSHotkeyDetector(lambda: None, lambda: None, on_history_toggle)

        # First toggle
        event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG | SHIFT_FLAG
        detector._event_callback(None, kCGEventKeyDown, event, None)
        self.assertEqual(toggle_count, 1)

        # Second toggle (would hide panel)
        detector._event_callback(None, kCGEventKeyDown, event, None)
        self.assertEqual(toggle_count, 2)

    @patch('context_aware_whisper.platform.macos.hotkey_detector.Quartz', MockQuartz)
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventTapCreate')
    @patch('context_aware_whisper.platform.macos.hotkey_detector.CGEventGetFlags')
    def test_history_toggle_does_not_interfere_with_recording(self, mock_get_flags, mock_tap_create):
        """Test history toggle doesn't affect recording state."""
        from context_aware_whisper.platform.macos.hotkey_detector import (
            MacOSHotkeyDetector, kCGEventKeyDown, kCGEventFlagsChanged
        )

        on_start = MagicMock()
        on_stop = MagicMock()
        on_history = MagicMock()
        detector = MacOSHotkeyDetector(on_start, on_stop, on_history)

        FN_KEYCODE = 63
        FN_FLAG = 0x800000

        # Start recording
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = FN_FLAG
        detector._event_callback(None, kCGEventFlagsChanged, event, None)
        self.assertTrue(detector.is_recording)
        on_start.assert_called_once()

        # Toggle history while recording
        h_event = MockCGEvent(keycode=H_KEYCODE)
        mock_get_flags.return_value = CMD_FLAG | SHIFT_FLAG
        detector._event_callback(None, kCGEventKeyDown, h_event, None)
        on_history.assert_called_once()

        # Recording should still be active
        self.assertTrue(detector.is_recording)

        # Stop recording
        event = MockCGEvent(keycode=FN_KEYCODE)
        mock_get_flags.return_value = 0
        detector._event_callback(None, kCGEventFlagsChanged, event, None)
        self.assertFalse(detector.is_recording)
        on_stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
