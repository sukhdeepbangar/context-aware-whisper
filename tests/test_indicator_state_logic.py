"""
Property-based tests for RecordingIndicator state logic.

This module tests the state machine behavior of RecordingIndicator using
hypothesis for property-based testing. These tests verify:
- State transitions are valid
- State configuration is consistent
- Animation timing is correct
- Position calculations are accurate
- Transparency handling works across platforms
"""

import pytest
from hypothesis import given, assume, settings, strategies as st, HealthCheck
from unittest.mock import MagicMock, patch
import re


# =============================================================================
# HYPOTHESIS STRATEGIES
# =============================================================================

# Strategy for valid states
valid_states = st.sampled_from(["idle", "recording", "transcribing", "success", "error"])

# Strategy for invalid states
invalid_states = st.text(min_size=1, max_size=20).filter(
    lambda x: x not in ["idle", "recording", "transcribing", "success", "error"]
)

# Strategy for valid positions
valid_positions = st.sampled_from([
    "top-center", "top-right", "top-left",
    "bottom-center", "bottom-right", "bottom-left"
])

# Strategy for invalid positions
invalid_positions = st.text(min_size=1, max_size=30).filter(
    lambda x: x not in ["top-center", "top-right", "top-left",
                        "bottom-center", "bottom-right", "bottom-left"]
)

# Strategy for opacity values
opacity_values = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_mock_tkinter():
    """Create comprehensive tkinter mocks for indicator testing."""
    mock_window = MagicMock()
    mock_window.winfo_screenwidth.return_value = 1920
    mock_window.winfo_screenheight.return_value = 1080
    mock_window.winfo_vrootx.return_value = 0
    mock_window.winfo_vrooty.return_value = 0
    mock_canvas = MagicMock()
    return mock_window, mock_canvas


def create_indicator_with_mocks(position="top-center", width=60, height=24):
    """Create a RecordingIndicator with mocked tkinter."""
    mock_window, mock_canvas = create_mock_tkinter()

    with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
         patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas):
        from handfree.ui.indicator import RecordingIndicator
        indicator = RecordingIndicator(width=width, height=height, position=position)
        return indicator, mock_window, mock_canvas


# =============================================================================
# STATE CONFIGURATION PROPERTY TESTS
# =============================================================================

class TestStateConfigurationProperties:
    """Property-based tests for state configuration consistency."""

    @given(state=valid_states)
    @settings(max_examples=20)
    def test_all_states_have_valid_config(self, state):
        """Property: Every valid state has a complete configuration tuple."""
        from handfree.ui.indicator import RecordingIndicator

        config = RecordingIndicator.STATE_CONFIG
        assert state in config
        state_config = config[state]

        # Must have exactly 4 elements: (bg_color, text_color, text, opacity)
        assert len(state_config) == 4

        bg_color, text_color, text, opacity = state_config

        # Colors must be valid hex strings
        assert isinstance(bg_color, str)
        assert bg_color.startswith("#")
        assert len(bg_color) == 7  # #RRGGBB format

        assert isinstance(text_color, str)
        assert text_color.startswith("#")
        assert len(text_color) == 7

        # Text must be string
        assert isinstance(text, str)

        # Opacity must be in valid range
        assert isinstance(opacity, (int, float))
        assert 0 <= opacity <= 1

    @given(state=valid_states)
    @settings(max_examples=20)
    def test_active_states_are_more_opaque_than_idle(self, state):
        """Property: All active states (non-idle) should be more opaque than idle."""
        from handfree.ui.indicator import RecordingIndicator

        config = RecordingIndicator.STATE_CONFIG
        idle_opacity = config["idle"][3]
        state_opacity = config[state][3]

        if state == "idle":
            assert state_opacity < 0.5, "Idle should be semi-transparent"
        else:
            assert state_opacity > idle_opacity, f"{state} should be more opaque than idle"

    def test_all_colors_are_unique_except_error_recording(self):
        """Property: Background colors should be unique, except error uses same as recording."""
        from handfree.ui.indicator import RecordingIndicator

        config = RecordingIndicator.STATE_CONFIG
        colors = {state: config[state][0] for state in config}

        # idle, transcribing, and success should have unique colors
        assert colors["idle"] != colors["transcribing"]
        assert colors["idle"] != colors["success"]
        assert colors["transcribing"] != colors["success"]

        # error uses the same red as recording
        assert colors["error"] == colors["recording"]


# =============================================================================
# STATE TRANSITION PROPERTY TESTS
# =============================================================================

class TestStateTransitionProperties:
    """Property-based tests for state transition logic."""

    @given(state=valid_states)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_setting_valid_state_updates_current_state(self, state):
        """Property: Setting a valid state always updates _current_state."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator.set_state(state)
        assert indicator._current_state == state

    @given(state=invalid_states)
    @settings(max_examples=20)
    def test_setting_invalid_state_raises_error(self, state):
        """Property: Setting an invalid state always raises ValueError."""
        indicator, _, _ = create_indicator_with_mocks()

        with pytest.raises(ValueError) as exc_info:
            indicator.set_state(state)

        assert "Invalid state" in str(exc_info.value)

    @given(states=st.lists(valid_states, min_size=1, max_size=10))
    @settings(max_examples=20)
    def test_state_sequence_always_ends_in_final_state(self, states):
        """Property: After a sequence of state changes, the indicator is in the last state."""
        indicator, _, _ = create_indicator_with_mocks()

        for state in states:
            indicator.set_state(state)

        assert indicator._current_state == states[-1]

    @given(initial_state=st.sampled_from(["recording", "transcribing", "success", "error"]))
    @settings(max_examples=15)
    def test_idle_state_always_hides_window(self, initial_state):
        """Property: Setting state to idle always hides the window."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # First set to a non-idle state
        indicator.set_state(initial_state)

        # Then set to idle
        indicator.set_state("idle")

        # Window should be hidden (withdraw called)
        mock_window.withdraw.assert_called()

    @given(state=st.sampled_from(["recording", "transcribing", "success", "error"]))
    @settings(max_examples=20)
    def test_non_idle_state_always_shows_window(self, state):
        """Property: Setting state to any non-idle state shows the window."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        indicator.set_state(state)

        # Window should be shown (deiconify called)
        mock_window.deiconify.assert_called()


# =============================================================================
# ANIMATION PROPERTY TESTS
# =============================================================================

class TestAnimationProperties:
    """Property-based tests for animation timing and behavior."""

    def test_flash_timing_is_consistent(self):
        """Property: Flash animation timing should be internally consistent."""
        from handfree.ui.indicator import RecordingIndicator

        # Animation step time should fit within total duration
        total_animation_time = RecordingIndicator.FLASH_STEPS * RecordingIndicator.FLASH_INTERVAL_MS
        assert total_animation_time <= RecordingIndicator.FLASH_DURATION_MS

        # There should be meaningful delay before animation starts
        pre_animation_delay = RecordingIndicator.FLASH_DURATION_MS - total_animation_time
        assert pre_animation_delay >= 0

    @given(state=st.sampled_from(["success", "error"]))
    @settings(max_examples=10)
    def test_flash_states_schedule_animation(self, state):
        """Property: Success and error states always schedule flash animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Reset mock to clear initialization calls
        mock_window.after.reset_mock()

        indicator.set_state(state)

        # Should have scheduled at least one animation callback
        assert mock_window.after.called, f"State {state} should schedule animation"

    @given(state=st.sampled_from(["idle", "recording", "transcribing"]))
    @settings(max_examples=15)
    def test_non_flash_states_do_not_schedule_animation(self, state):
        """Property: Non-flash states (idle, recording, transcribing) should not schedule animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Reset mock to clear initialization calls
        mock_window.after.reset_mock()

        indicator.set_state(state)

        # Check that _flash_after_ids is empty (no animation scheduled)
        assert len(indicator._flash_after_ids) == 0

    def test_cancel_animations_clears_all_pending(self):
        """Property: cancel_animations always clears the pending callback list."""
        indicator, _, _ = create_indicator_with_mocks()

        # Add some fake callback IDs
        indicator._flash_after_ids = ["id1", "id2", "id3"]

        indicator._cancel_animations()

        assert indicator._flash_after_ids == []


# =============================================================================
# POSITION PROPERTY TESTS
# =============================================================================

class TestPositionProperties:
    """Property-based tests for position calculations."""

    @given(position=valid_positions)
    @settings(max_examples=12)
    def test_valid_positions_are_accepted(self, position):
        """Property: All valid positions are accepted without error."""
        indicator, _, _ = create_indicator_with_mocks(position=position)
        assert indicator._position == position

    @given(position=invalid_positions)
    @settings(max_examples=20)
    def test_invalid_positions_fall_back_to_default(self, position):
        """Property: Invalid positions fall back to top-center."""
        indicator, _, _ = create_indicator_with_mocks(position=position)
        assert indicator._position == "top-center"

    @given(position=valid_positions)
    @settings(max_examples=12)
    def test_set_position_validates_input(self, position):
        """Property: set_position accepts all valid positions."""
        indicator, _, _ = create_indicator_with_mocks()
        indicator.set_position(position)
        assert indicator._position == position

    @given(position=invalid_positions)
    @settings(max_examples=20)
    def test_set_position_rejects_invalid(self, position):
        """Property: set_position rejects invalid positions with ValueError."""
        indicator, _, _ = create_indicator_with_mocks()

        with pytest.raises(ValueError):
            indicator.set_position(position)

    @given(
        screen_width=st.integers(min_value=800, max_value=3840),
        screen_height=st.integers(min_value=600, max_value=2160),
        indicator_width=st.integers(min_value=40, max_value=120),
        indicator_height=st.integers(min_value=20, max_value=60)
    )
    @settings(max_examples=20)
    def test_position_stays_within_screen_bounds(
        self, screen_width, screen_height, indicator_width, indicator_height
    ):
        """Property: Positioned indicator always stays within screen bounds."""
        from handfree.ui.indicator import VALID_POSITIONS

        mock_window = MagicMock()
        mock_window.winfo_screenwidth.return_value = screen_width
        mock_window.winfo_screenheight.return_value = screen_height
        mock_window.winfo_vrootx.return_value = 0
        mock_window.winfo_vrooty.return_value = 0
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas):

            from handfree.ui.indicator import RecordingIndicator

            for position in VALID_POSITIONS:
                indicator = RecordingIndicator(
                    width=indicator_width,
                    height=indicator_height,
                    position=position
                )

                # Get the geometry call
                geometry_call = mock_window.geometry.call_args[0][0]

                # Parse geometry string: WxH+X+Y
                match = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geometry_call)
                assert match is not None, f"Invalid geometry format: {geometry_call}"

                x = int(match.group(3))
                y = int(match.group(4))

                # Verify position is within screen bounds
                assert x >= 0, f"X position {x} should be >= 0 for {position}"
                assert y >= 0, f"Y position {y} should be >= 0 for {position}"
                assert x + indicator_width <= screen_width, \
                    f"Right edge {x + indicator_width} exceeds screen width {screen_width} for {position}"
                assert y + indicator_height <= screen_height, \
                    f"Bottom edge {y + indicator_height} exceeds screen height {screen_height} for {position}"


# =============================================================================
# TRANSPARENCY PROPERTY TESTS
# =============================================================================

class TestTransparencyProperties:
    """Property-based tests for platform-specific transparency."""

    @given(opacity=opacity_values)
    @settings(max_examples=20)
    def test_opacity_override_uses_provided_value(self, opacity):
        """Property: opacity_override always uses the provided value."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Reset mock
        mock_window.attributes.reset_mock()

        indicator._draw_state(opacity_override=opacity)

        # Should have set alpha to the override value
        mock_window.attributes.assert_called_with("-alpha", opacity)

    @given(state=valid_states)
    @settings(max_examples=20)
    def test_draw_state_uses_config_opacity_by_default(self, state):
        """Property: Without override, _draw_state uses config opacity."""
        from handfree.ui.indicator import RecordingIndicator

        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = state

        # Reset mock
        mock_window.attributes.reset_mock()

        indicator._draw_state()

        expected_opacity = RecordingIndicator.STATE_CONFIG[state][3]
        mock_window.attributes.assert_called_with("-alpha", expected_opacity)


# =============================================================================
# CANVAS DRAWING PROPERTY TESTS
# =============================================================================

class TestCanvasDrawingProperties:
    """Property-based tests for canvas drawing operations."""

    @given(state=valid_states)
    @settings(max_examples=20)
    def test_draw_state_clears_canvas_first(self, state):
        """Property: Drawing a state always clears the canvas first."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        # Reset mock
        mock_canvas.delete.reset_mock()

        indicator._current_state = state
        indicator._draw_state()

        # Canvas should be cleared with "all"
        mock_canvas.delete.assert_called_with("all")

    @given(state=valid_states)
    @settings(max_examples=20)
    def test_draw_state_creates_rectangle(self, state):
        """Property: Drawing a state always creates a background rectangle."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        # Reset mock
        mock_canvas.create_rectangle.reset_mock()

        indicator._current_state = state
        indicator._draw_state()

        # Should create a rectangle
        mock_canvas.create_rectangle.assert_called()

    @given(state=st.sampled_from(["recording", "transcribing", "success", "error"]))
    @settings(max_examples=20)
    def test_non_idle_states_create_text(self, state):
        """Property: Non-idle states (with text) create text on canvas."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        # Reset mock
        mock_canvas.create_text.reset_mock()

        indicator._current_state = state
        indicator._draw_state()

        # Should create text
        mock_canvas.create_text.assert_called()

    def test_idle_state_does_not_create_text(self):
        """Property: Idle state (empty text) does not create text on canvas."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        # Reset mock
        mock_canvas.create_text.reset_mock()

        indicator._current_state = "idle"
        indicator._draw_state()

        # Should NOT create text for idle (empty text)
        mock_canvas.create_text.assert_not_called()


# =============================================================================
# MULTI-MONITOR PROPERTY TESTS
# =============================================================================

class TestMultiMonitorProperties:
    """Property-based tests for multi-monitor support."""

    @given(
        offset_x=st.integers(min_value=0, max_value=7680),
        offset_y=st.integers(min_value=0, max_value=4320)
    )
    @settings(max_examples=20)
    def test_display_offset_is_applied_to_position(self, offset_x, offset_y):
        """Property: Display offset is always applied to window position."""
        from handfree.ui.indicator import RecordingIndicator

        mock_window = MagicMock()
        mock_window.winfo_screenwidth.return_value = 1920
        mock_window.winfo_screenheight.return_value = 1080
        mock_window.winfo_vrootx.return_value = offset_x
        mock_window.winfo_vrooty.return_value = offset_y
        mock_canvas = MagicMock()

        with patch('handfree.ui.indicator.tk.Toplevel', return_value=mock_window), \
             patch('handfree.ui.indicator.tk.Canvas', return_value=mock_canvas):

            indicator = RecordingIndicator(position="top-center")

            geometry_call = mock_window.geometry.call_args[0][0]

            match = re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', geometry_call)
            assert match is not None

            x = int(match.group(3))
            y = int(match.group(4))

            # Position should include offset when offset is non-zero
            if offset_x > 0 or offset_y > 0:
                assert x >= offset_x, f"X {x} should be >= offset {offset_x}"
                assert y >= offset_y, f"Y {y} should be >= offset {offset_y}"


# =============================================================================
# LIFECYCLE PROPERTY TESTS
# =============================================================================

class TestLifecycleProperties:
    """Property-based tests for indicator lifecycle management."""

    @given(states=st.lists(valid_states, min_size=1, max_size=20))
    @settings(max_examples=15)
    def test_destroy_can_be_called_in_any_state(self, states):
        """Property: destroy() can be safely called regardless of current state."""
        indicator, _, _ = create_indicator_with_mocks()

        # Cycle through states
        for state in states:
            indicator.set_state(state)

        # Destroy should not raise
        indicator.destroy()

    def test_destroy_clears_pending_animations(self):
        """Property: destroy() always cancels pending animations."""
        indicator, _, _ = create_indicator_with_mocks()

        # Add fake pending animations
        indicator._flash_after_ids = ["id1", "id2"]

        indicator.destroy()

        assert indicator._flash_after_ids == []

    def test_show_then_hide_is_symmetric(self):
        """Property: show() followed by hide() returns to hidden state."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        indicator.show()
        indicator.hide()

        # Last call should be withdraw (hide)
        mock_window.withdraw.assert_called()


# =============================================================================
# STATE TEXT PROPERTY TESTS
# =============================================================================

class TestStateTextProperties:
    """Property-based tests for state text content."""

    def test_active_states_have_non_empty_text(self):
        """Property: All active (non-idle) states have non-empty display text."""
        from handfree.ui.indicator import RecordingIndicator

        active_states = ["recording", "transcribing", "success", "error"]

        for state in active_states:
            text = RecordingIndicator.STATE_CONFIG[state][2]
            assert len(text) > 0, f"State {state} should have display text"

    def test_idle_state_has_empty_text(self):
        """Property: Idle state has empty display text."""
        from handfree.ui.indicator import RecordingIndicator

        text = RecordingIndicator.STATE_CONFIG["idle"][2]
        assert text == "", "Idle state should have empty text"

    def test_state_texts_are_short(self):
        """Property: All state texts should be short (for compact display)."""
        from handfree.ui.indicator import RecordingIndicator

        max_length = 5  # Maximum reasonable length for indicator text

        for state, config in RecordingIndicator.STATE_CONFIG.items():
            text = config[2]
            assert len(text) <= max_length, \
                f"State {state} text '{text}' exceeds max length {max_length}"


# =============================================================================
# INTEGRATION PROPERTY TESTS
# =============================================================================

class TestIntegrationProperties:
    """Integration tests combining multiple aspects of indicator behavior."""

    @given(state_sequence=st.lists(valid_states, min_size=2, max_size=10))
    @settings(max_examples=15)
    def test_rapid_state_changes_are_safe(self, state_sequence):
        """Property: Rapid state changes do not cause errors."""
        indicator, _, _ = create_indicator_with_mocks()

        for state in state_sequence:
            indicator.set_state(state)

        # Should end in the final state without error
        assert indicator._current_state == state_sequence[-1]

    @given(
        position=valid_positions,
        state=valid_states
    )
    @settings(max_examples=30)
    def test_position_and_state_are_independent(self, position, state):
        """Property: Position and state can be set independently."""
        indicator, _, _ = create_indicator_with_mocks(position=position)

        indicator.set_state(state)

        # Both should retain their values
        assert indicator._position == position
        assert indicator._current_state == state

    def test_state_cycle_recording_to_success(self):
        """Property: Complete recording cycle ends in correct state."""
        indicator, _, _ = create_indicator_with_mocks()

        # Simulate recording cycle
        indicator.set_state("recording")
        assert indicator._current_state == "recording"

        indicator.set_state("transcribing")
        assert indicator._current_state == "transcribing"

        indicator.set_state("success")
        assert indicator._current_state == "success"

    def test_state_cycle_recording_to_error(self):
        """Property: Recording cycle with error ends in error state."""
        indicator, _, _ = create_indicator_with_mocks()

        # Simulate recording cycle with error
        indicator.set_state("recording")
        indicator.set_state("transcribing")
        indicator.set_state("error")

        assert indicator._current_state == "error"
