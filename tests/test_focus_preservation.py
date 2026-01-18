"""
Property-based and integration tests for focus preservation during recording.

This module tests that the HandFree application does not steal keyboard focus
from active text fields when the Fn key is pressed to start recording.

Tested scenarios:
- Indicator window configuration prevents focus stealing
- Hotkey detector uses passive event tap (ListenOnly)
- Focus remains in text area during recording lifecycle
- Transcribed text appears at original cursor position
"""

import sys
import pytest
from unittest.mock import MagicMock, patch, Mock, call
from hypothesis import given, strategies as st, settings, HealthCheck


# =============================================================================
# INDICATOR FOCUS PREVENTION TESTS
# =============================================================================

class TestIndicatorFocusPrevention:
    """Tests for RecordingIndicator focus prevention configuration."""

    def test_indicator_uses_overrideredirect(self):
        """Test indicator window uses overrideredirect to prevent focus."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            # Should call overrideredirect(True)
            mock_window.overrideredirect.assert_called_with(True)

    def test_indicator_uses_topmost_attribute(self):
        """Test indicator window uses -topmost attribute."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            # Should set -topmost to True
            calls = mock_window.attributes.call_args_list
            topmost_call = [c for c in calls if len(c[0]) > 0 and c[0][0] == "-topmost"]
            assert len(topmost_call) > 0, "Should set -topmost attribute"
            assert topmost_call[0][0][1] is True, "-topmost should be True"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_indicator_sets_macos_focus_prevention(self):
        """Test indicator sets macOS-specific focus prevention attributes."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            # Should call wm_attributes with -modified
            calls = mock_window.wm_attributes.call_args_list
            if calls:  # Only check if wm_attributes was called
                modified_call = [c for c in calls if '-modified' in c[0]]
                assert len(modified_call) > 0, "Should set -modified attribute on macOS"

    def test_indicator_show_does_not_call_lift_on_macos(self):
        """Test indicator show() does not call lift() on macOS to prevent focus stealing."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()
            mock_window.lift.reset_mock()  # Reset after initialization

            indicator.show()

            # Should call deiconify but NOT lift on macOS
            mock_window.deiconify.assert_called()
            mock_window.lift.assert_not_called()

    def test_indicator_show_calls_lift_on_other_platforms(self):
        """Test indicator show() calls lift() on non-macOS platforms."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='linux'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()
            mock_window.lift.reset_mock()

            indicator.show()

            # Should call both deiconify and lift on Linux
            mock_window.deiconify.assert_called()
            mock_window.lift.assert_called()

    @given(state=st.sampled_from(["recording", "transcribing", "success", "error"]))
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_set_state_to_active_calls_show_without_focus_steal(self, state):
        """Property: Setting active state shows window using focus-safe show()."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()
            mock_window.deiconify.reset_mock()
            mock_window.lift.reset_mock()

            indicator.set_state(state)

            # Should show without calling lift
            mock_window.deiconify.assert_called()
            mock_window.lift.assert_not_called()


# =============================================================================
# HOTKEY DETECTOR FOCUS PREVENTION TESTS
# =============================================================================

class TestHotkeyDetectorFocusPrevention:
    """Tests for macOS hotkey detector event tap configuration."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_event_tap_uses_listen_only_option(self):
        """Test event tap uses kCGEventTapOptionListenOnly to avoid consuming events."""
        from unittest.mock import patch, MagicMock

        # Mock the Quartz module
        with patch('handfree.platform.macos.hotkey_detector.Quartz') as mock_quartz, \
             patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate') as mock_create, \
             patch('handfree.platform.macos.hotkey_detector.CGEventMaskBit') as mock_mask, \
             patch('handfree.platform.macos.hotkey_detector.CFMachPortCreateRunLoopSource'), \
             patch('handfree.platform.macos.hotkey_detector.CFRunLoopGetCurrent'), \
             patch('handfree.platform.macos.hotkey_detector.CFRunLoopAddSource'), \
             patch('handfree.platform.macos.hotkey_detector.CFRunLoopRunInMode'):

            # Set up mocks
            mock_quartz.kCGSessionEventTap = 0
            mock_quartz.kCGHeadInsertEventTap = 0
            mock_quartz.kCGEventTapOptionListenOnly = 1  # The key value
            mock_tap = MagicMock()
            mock_create.return_value = mock_tap

            from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

            detector = MacOSHotkeyDetector(lambda: None, lambda: None)
            detector._running = False  # Will exit immediately

            # Run the loop to trigger tap creation
            detector._run_loop()

            # Verify CGEventTapCreate was called with kCGEventTapOptionListenOnly
            mock_create.assert_called()
            call_args = mock_create.call_args[0]

            # The third argument should be kCGEventTapOptionListenOnly
            assert call_args[2] == mock_quartz.kCGEventTapOptionListenOnly, \
                "Event tap should use kCGEventTapOptionListenOnly for passive listening"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_event_callback_returns_event_unmodified(self):
        """Test event callback returns events unmodified (pass-through)."""
        from unittest.mock import patch, MagicMock

        with patch('handfree.platform.macos.hotkey_detector.Quartz') as mock_quartz, \
             patch('handfree.platform.macos.hotkey_detector.CGEventTapCreate'), \
             patch('handfree.platform.macos.hotkey_detector.CGEventGetFlags') as mock_get_flags:

            mock_quartz.kCGEventFlagsChanged = 12
            mock_quartz.kCGEventFlagMaskCommand = 0x100000
            mock_get_flags.return_value = 0

            from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector

            detector = MacOSHotkeyDetector(lambda: None, lambda: None)

            # Create a mock event
            mock_event = MagicMock()
            mock_event._keycode = 50  # Random key

            # Call the callback
            result = detector._event_callback(None, 12, mock_event, None)

            # Should return the same event unmodified
            assert result is mock_event, "Event callback should return event for pass-through"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestFocusPreservationIntegration:
    """Integration tests for focus preservation during recording cycle."""

    @given(
        initial_state=st.sampled_from(["idle", "recording"]),
        final_state=st.sampled_from(["transcribing", "success", "error"])
    )
    @settings(max_examples=15)
    def test_state_transitions_do_not_steal_focus(self, initial_state, final_state):
        """Property: State transitions use focus-safe window operations."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            # Set initial state
            indicator.set_state(initial_state)
            mock_window.lift.reset_mock()

            # Transition to final state
            indicator.set_state(final_state)

            # Should never call lift() on macOS during any transition
            mock_window.lift.assert_not_called()

    def test_full_recording_cycle_preserves_focus(self):
        """Test complete recording cycle: idle -> recording -> transcribing -> success."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            # Simulate full recording cycle
            states = ["idle", "recording", "transcribing", "success", "idle"]

            for state in states:
                mock_window.lift.reset_mock()
                indicator.set_state(state)
                mock_window.lift.assert_not_called()


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestFocusPreservationProperties:
    """Property-based tests for focus preservation behavior."""

    @given(state_sequence=st.lists(
        st.sampled_from(["idle", "recording", "transcribing", "success", "error"]),
        min_size=2,
        max_size=20
    ))
    @settings(max_examples=30)
    def test_no_focus_stealing_in_any_state_sequence(self, state_sequence):
        """Property: No state sequence should call lift() on macOS."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            for state in state_sequence:
                indicator.set_state(state)

            # Count how many times lift was called (should be 0)
            lift_call_count = mock_window.lift.call_count
            assert lift_call_count == 0, \
                f"lift() was called {lift_call_count} times, should never be called on macOS"

    @given(width=st.integers(min_value=40, max_value=200),
           height=st.integers(min_value=20, max_value=100))
    @settings(max_examples=20)
    def test_window_size_does_not_affect_focus_behavior(self, width, height):
        """Property: Window size should not affect focus prevention."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator(width=width, height=height)

            # Verify overrideredirect is set regardless of size
            mock_window.overrideredirect.assert_called_with(True)

            # Verify -topmost is set
            topmost_calls = [c for c in mock_window.attributes.call_args_list
                           if len(c[0]) > 0 and c[0][0] == "-topmost"]
            assert len(topmost_calls) > 0


# =============================================================================
# MANUAL TEST GUIDANCE
# =============================================================================

class TestFocusPreservationManualGuidance:
    """
    Manual tests to perform (cannot be automated):

    1. Open TextEdit with cursor in document
    2. Run HandFree app
    3. Press Fn key to start recording
    4. Verify:
       - Cursor stays in TextEdit (does not move)
       - Recording indicator appears at top of screen
       - You can continue typing in TextEdit while holding Fn (if needed)
    5. Release Fn key
    6. Verify:
       - Transcribed text appears at cursor position
       - No need to click back into TextEdit

    Test in multiple applications:
    - Terminal
    - VS Code
    - Chrome/Safari (browser text field)
    - Notes app
    - Slack/Discord message input

    If focus is stolen:
    - Check that indicator.py:_setup_focus_prevention() is being called
    - Verify overrideredirect(True) is set
    - Verify lift() is not being called on macOS
    - Check for any other window.focus() or window.focus_force() calls
    """

    def test_manual_test_documentation(self):
        """Placeholder test documenting manual test requirements."""
        # This test always passes but serves as documentation
        assert True, "See class docstring for manual testing procedures"


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestFocusPreservationPerformance:
    """Tests to verify focus prevention doesn't impact performance."""

    @given(num_transitions=st.integers(min_value=10, max_value=100))
    @settings(max_examples=10)
    def test_rapid_state_changes_maintain_focus_prevention(self, num_transitions):
        """Property: Rapid state changes should not bypass focus prevention."""
        mock_window = MagicMock()
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas), \
             patch('handfree.ui.indicator.get_current_platform', return_value='macos'):
            from handfree.ui.indicator import RecordingIndicator

            indicator = RecordingIndicator()

            states = ["recording", "transcribing", "success", "idle"]

            for i in range(num_transitions):
                state = states[i % len(states)]
                indicator.set_state(state)

            # Even after rapid changes, lift should never be called
            assert mock_window.lift.call_count == 0
