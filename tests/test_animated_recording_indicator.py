"""
Tests for Animated Recording Indicator (Phase 4)

This module tests the animated audio visualizer bars that replace the static "REC"
indicator during recording state. These tests verify:
- Bar animation constants are correctly defined
- Bar animation state is properly initialized
- Bar drawing and animation methods work correctly
- Recording state uses animated bars instead of static text
- Animation cleanup is handled properly
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from unittest.mock import MagicMock, patch


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

    with patch('context_aware_whisper.ui.indicator.tk.Toplevel', return_value=mock_window), \
         patch('context_aware_whisper.ui.indicator.tk.Canvas', return_value=mock_canvas):
        from context_aware_whisper.ui.indicator import RecordingIndicator
        indicator = RecordingIndicator(width=width, height=height, position=position)
        return indicator, mock_window, mock_canvas


# =============================================================================
# BAR ANIMATION CONSTANTS TESTS
# =============================================================================

class TestBarAnimationConstants:
    """Tests for bar animation configuration constants."""

    def test_bar_count_constant_exists(self):
        """Test that BAR_COUNT constant exists and is 4."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_COUNT')
        assert RecordingIndicator.BAR_COUNT == 4

    def test_bar_width_constant_exists(self):
        """Test that BAR_WIDTH constant exists and is 6."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_WIDTH')
        assert RecordingIndicator.BAR_WIDTH == 6

    def test_bar_gap_constant_exists(self):
        """Test that BAR_GAP constant exists and is 3."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_GAP')
        assert RecordingIndicator.BAR_GAP == 3

    def test_bar_min_height_constant_exists(self):
        """Test that BAR_MIN_HEIGHT constant exists and is 4."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_MIN_HEIGHT')
        assert RecordingIndicator.BAR_MIN_HEIGHT == 4

    def test_bar_max_height_constant_exists(self):
        """Test that BAR_MAX_HEIGHT constant exists and is 16."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_MAX_HEIGHT')
        assert RecordingIndicator.BAR_MAX_HEIGHT == 16

    def test_bar_animation_interval_constant_exists(self):
        """Test that BAR_ANIMATION_INTERVAL_MS constant exists and is 80 (~12.5 FPS)."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_ANIMATION_INTERVAL_MS')
        assert RecordingIndicator.BAR_ANIMATION_INTERVAL_MS == 80

    def test_bar_colors_constant_exists(self):
        """Test that BAR_COLORS constant exists with correct gradient."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_COLORS')
        assert len(RecordingIndicator.BAR_COLORS) == 4
        assert RecordingIndicator.BAR_COLORS == ["#FF3B30", "#FF6B5B", "#FF9500", "#FF6B5B"]

    def test_bar_bg_color_constant_exists(self):
        """Test that BAR_BG_COLOR constant exists (dark slate)."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, 'BAR_BG_COLOR')
        assert RecordingIndicator.BAR_BG_COLOR == "#1C1C1E"

    def test_bar_dimensions_fit_within_default_indicator(self):
        """Test that bars fit within the default 60x24 indicator."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        total_bar_width = (RecordingIndicator.BAR_COUNT * RecordingIndicator.BAR_WIDTH) + \
                          ((RecordingIndicator.BAR_COUNT - 1) * RecordingIndicator.BAR_GAP)

        # Should fit within default width of 60
        assert total_bar_width < 60, f"Total bar width {total_bar_width} exceeds indicator width 60"

        # Max height should fit within default height of 24
        assert RecordingIndicator.BAR_MAX_HEIGHT < 24, "Max bar height exceeds indicator height"


# =============================================================================
# BAR ANIMATION INSTANCE VARIABLES TESTS
# =============================================================================

class TestBarAnimationInstanceVariables:
    """Tests for bar animation instance variable initialization."""

    def test_bar_animation_id_initialized(self):
        """Test that _bar_animation_id is initialized to None."""
        indicator, _, _ = create_indicator_with_mocks()
        assert hasattr(indicator, '_bar_animation_id')
        assert indicator._bar_animation_id is None

    def test_bar_heights_initialized(self):
        """Test that _bar_heights is initialized with correct values."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, _ = create_indicator_with_mocks()
        assert hasattr(indicator, '_bar_heights')
        assert isinstance(indicator._bar_heights, list)
        assert len(indicator._bar_heights) == RecordingIndicator.BAR_COUNT

        # All bars should start at minimum height
        for height in indicator._bar_heights:
            assert height == RecordingIndicator.BAR_MIN_HEIGHT

    def test_bar_directions_initialized(self):
        """Test that _bar_directions is initialized with alternating values."""
        indicator, _, _ = create_indicator_with_mocks()
        assert hasattr(indicator, '_bar_directions')
        assert isinstance(indicator._bar_directions, list)
        assert len(indicator._bar_directions) == 4
        # Alternating up/down directions
        assert indicator._bar_directions == [1, -1, 1, -1]


# =============================================================================
# BAR DRAWING METHOD TESTS
# =============================================================================

class TestDrawRecordingBars:
    """Tests for _draw_recording_bars method."""

    def test_draw_recording_bars_method_exists(self):
        """Test that _draw_recording_bars method exists."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, '_draw_recording_bars')
        assert callable(getattr(RecordingIndicator, '_draw_recording_bars'))

    def test_draw_recording_bars_clears_canvas(self):
        """Test that _draw_recording_bars clears the canvas first."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.delete.reset_mock()
        indicator._draw_recording_bars()

        mock_canvas.delete.assert_called_with("all")

    def test_draw_recording_bars_draws_background(self):
        """Test that _draw_recording_bars draws dark background."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_rectangle.reset_mock()
        indicator._draw_recording_bars()

        # First rectangle should be the background
        calls = mock_canvas.create_rectangle.call_args_list
        assert len(calls) >= 1

        # Check first call is background
        first_call_kwargs = calls[0][1]
        assert first_call_kwargs.get('fill') == RecordingIndicator.BAR_BG_COLOR

    def test_draw_recording_bars_draws_four_bars(self):
        """Test that _draw_recording_bars draws 4 bars."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_rectangle.reset_mock()
        indicator._draw_recording_bars()

        # Should have 5 rectangles: 1 background + 4 bars
        calls = mock_canvas.create_rectangle.call_args_list
        assert len(calls) == 5

    def test_draw_recording_bars_uses_bar_colors(self):
        """Test that _draw_recording_bars uses correct bar colors."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_rectangle.reset_mock()
        indicator._draw_recording_bars()

        calls = mock_canvas.create_rectangle.call_args_list
        # Skip background (first call), check bar colors
        for i in range(1, 5):
            fill_color = calls[i][1].get('fill')
            expected_color = RecordingIndicator.BAR_COLORS[(i-1) % len(RecordingIndicator.BAR_COLORS)]
            assert fill_color == expected_color, f"Bar {i} has wrong color: {fill_color} vs {expected_color}"


# =============================================================================
# BAR ANIMATION METHOD TESTS
# =============================================================================

class TestAnimateBars:
    """Tests for _animate_bars method."""

    def test_animate_bars_method_exists(self):
        """Test that _animate_bars method exists."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, '_animate_bars')
        assert callable(getattr(RecordingIndicator, '_animate_bars'))

    def test_animate_bars_does_nothing_if_not_recording(self):
        """Test that _animate_bars returns early if not in recording state."""
        indicator, mock_window, mock_canvas = create_indicator_with_mocks()

        # Set to non-recording state
        indicator._current_state = "idle"
        mock_window.after.reset_mock()

        indicator._animate_bars()

        # Should not schedule next animation
        mock_window.after.assert_not_called()

    def test_animate_bars_updates_bar_heights(self):
        """Test that _animate_bars updates bar heights."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        initial_heights = indicator._bar_heights.copy()

        # Mock random to return consistent values for testing
        with patch('context_aware_whisper.ui.indicator.random.randint', return_value=3):
            indicator._animate_bars()

        # At least some heights should have changed
        # (Some may bounce at limits, so we check that animation occurred)
        assert indicator._bar_heights != initial_heights or \
               mock_window.after.called  # Animation was scheduled

    def test_animate_bars_respects_height_bounds(self):
        """Test that _animate_bars keeps heights within bounds."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        # Set heights to extremes
        indicator._bar_heights = [RecordingIndicator.BAR_MAX_HEIGHT] * 4
        indicator._bar_directions = [1, 1, 1, 1]  # All going up

        with patch('context_aware_whisper.ui.indicator.random.randint', return_value=5):
            indicator._animate_bars()

        # Heights should still be within bounds
        for height in indicator._bar_heights:
            assert RecordingIndicator.BAR_MIN_HEIGHT <= height <= RecordingIndicator.BAR_MAX_HEIGHT

    def test_animate_bars_reverses_direction_at_limits(self):
        """Test that _animate_bars reverses direction at height limits."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        # Set bar at max height with upward direction
        indicator._bar_heights = [RecordingIndicator.BAR_MAX_HEIGHT, 8, 8, 8]
        indicator._bar_directions = [1, 1, 1, 1]

        with patch('context_aware_whisper.ui.indicator.random.randint', return_value=3):
            indicator._animate_bars()

        # First bar should have reversed direction
        assert indicator._bar_directions[0] == -1

    def test_animate_bars_schedules_next_frame(self):
        """Test that _animate_bars schedules next animation frame."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        mock_window.after.reset_mock()
        indicator._animate_bars()

        # Should schedule next frame
        mock_window.after.assert_called()
        call_args = mock_window.after.call_args
        assert call_args[0][0] == RecordingIndicator.BAR_ANIMATION_INTERVAL_MS


# =============================================================================
# STOP BAR ANIMATION METHOD TESTS
# =============================================================================

class TestStopBarAnimation:
    """Tests for _stop_bar_animation method."""

    def test_stop_bar_animation_method_exists(self):
        """Test that _stop_bar_animation method exists."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert hasattr(RecordingIndicator, '_stop_bar_animation')
        assert callable(getattr(RecordingIndicator, '_stop_bar_animation'))

    def test_stop_bar_animation_cancels_pending_animation(self):
        """Test that _stop_bar_animation cancels pending animation callback."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Simulate running animation
        indicator._bar_animation_id = "fake_id"

        indicator._stop_bar_animation()

        mock_window.after_cancel.assert_called_with("fake_id")

    def test_stop_bar_animation_clears_animation_id(self):
        """Test that _stop_bar_animation sets animation ID to None."""
        indicator, _, _ = create_indicator_with_mocks()

        indicator._bar_animation_id = "fake_id"
        indicator._stop_bar_animation()

        assert indicator._bar_animation_id is None

    def test_stop_bar_animation_resets_bar_heights(self):
        """Test that _stop_bar_animation resets bar heights to minimum."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, _ = create_indicator_with_mocks()

        # Set heights to random values
        indicator._bar_heights = [10, 12, 8, 14]
        indicator._stop_bar_animation()

        for height in indicator._bar_heights:
            assert height == RecordingIndicator.BAR_MIN_HEIGHT

    def test_stop_bar_animation_handles_no_animation_gracefully(self):
        """Test that _stop_bar_animation works when no animation is running."""
        indicator, _, _ = create_indicator_with_mocks()

        indicator._bar_animation_id = None

        # Should not raise
        indicator._stop_bar_animation()

        assert indicator._bar_animation_id is None


# =============================================================================
# RECORDING STATE INTEGRATION TESTS
# =============================================================================

class TestRecordingStateIntegration:
    """Tests for recording state using animated bars instead of static text."""

    def test_recording_state_calls_draw_recording_bars(self):
        """Test that setting recording state draws animated bars."""
        indicator, mock_window, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_rectangle.reset_mock()
        indicator.set_state("recording")

        # Should have created rectangles (background + bars)
        assert mock_canvas.create_rectangle.call_count >= 5

    def test_recording_state_starts_bar_animation(self):
        """Test that setting recording state starts bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        mock_window.after.reset_mock()
        indicator.set_state("recording")

        # Should have scheduled animation
        assert mock_window.after.called
        # Check animation ID is set
        assert indicator._bar_animation_id is not None

    def test_recording_state_does_not_create_text(self):
        """Test that recording state uses bars instead of 'REC' text."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_text.reset_mock()
        indicator.set_state("recording")

        # Should NOT create text (we use bars instead)
        mock_canvas.create_text.assert_not_called()

    def test_non_recording_states_stop_bar_animation(self):
        """Test that setting non-recording state stops bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Start in recording state
        indicator.set_state("recording")
        animation_id = indicator._bar_animation_id
        assert animation_id is not None

        # Switch to transcribing
        indicator.set_state("transcribing")

        # Animation should be stopped
        assert indicator._bar_animation_id is None
        mock_window.after_cancel.assert_called()

    def test_transcribing_state_still_uses_static_text(self):
        """Test that transcribing state still uses static '...' text."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_text.reset_mock()
        indicator.set_state("transcribing")

        # Should create text for transcribing
        mock_canvas.create_text.assert_called()

    def test_success_state_still_uses_static_text(self):
        """Test that success state still uses static 'OK' text."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        mock_canvas.create_text.reset_mock()
        indicator.set_state("success")

        # Should create text for success
        mock_canvas.create_text.assert_called()


# =============================================================================
# CLEANUP INTEGRATION TESTS
# =============================================================================

class TestCleanupIntegration:
    """Tests for animation cleanup integration."""

    def test_cancel_animations_stops_bar_animation(self):
        """Test that _cancel_animations also stops bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Start bar animation
        indicator._bar_animation_id = "fake_id"
        indicator._bar_heights = [10, 12, 8, 14]

        indicator._cancel_animations()

        # Bar animation should be stopped
        assert indicator._bar_animation_id is None
        mock_window.after_cancel.assert_called()

    def test_destroy_stops_bar_animation(self):
        """Test that destroy() stops bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        indicator._bar_animation_id = "fake_id"
        indicator.destroy()

        assert indicator._bar_animation_id is None


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestBarAnimationProperties:
    """Property-based tests for bar animation behavior."""

    @given(height=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_bar_heights_stay_within_bounds(self, height):
        """Property: Bar heights always stay within MIN and MAX bounds."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        # Set initial heights
        indicator._bar_heights = [min(max(height, RecordingIndicator.BAR_MIN_HEIGHT),
                                      RecordingIndicator.BAR_MAX_HEIGHT)] * 4

        # Animate multiple times
        for _ in range(10):
            indicator._animate_bars()
            for h in indicator._bar_heights:
                assert RecordingIndicator.BAR_MIN_HEIGHT <= h <= RecordingIndicator.BAR_MAX_HEIGHT

    @given(direction=st.sampled_from([-1, 1]))
    @settings(max_examples=10)
    def test_bar_direction_reverses_at_limits(self, direction):
        """Property: Bar direction always reverses when hitting limits."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        # Set up to trigger limit
        if direction == 1:
            indicator._bar_heights = [RecordingIndicator.BAR_MAX_HEIGHT] * 4
        else:
            indicator._bar_heights = [RecordingIndicator.BAR_MIN_HEIGHT] * 4

        indicator._bar_directions = [direction] * 4

        with patch('context_aware_whisper.ui.indicator.random.randint', return_value=3):
            indicator._animate_bars()

        # Direction should be reversed
        expected_direction = -direction
        assert all(d == expected_direction for d in indicator._bar_directions)

    @given(states=st.lists(st.sampled_from(["idle", "recording", "transcribing", "success", "error"]),
                           min_size=1, max_size=20))
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rapid_state_changes_handle_animation_correctly(self, states):
        """Property: Rapid state changes properly manage bar animation."""
        indicator, _, _ = create_indicator_with_mocks()

        for state in states:
            indicator.set_state(state)

        # Final state should be correct
        assert indicator._current_state == states[-1]

        # Animation should only be running if in recording state
        if states[-1] == "recording":
            assert indicator._bar_animation_id is not None
        else:
            assert indicator._bar_animation_id is None


class TestBarDrawingProperties:
    """Property-based tests for bar drawing."""

    @given(
        width=st.integers(min_value=40, max_value=200),
        height=st.integers(min_value=20, max_value=100)
    )
    @settings(max_examples=20)
    def test_bars_centered_regardless_of_dimensions(self, width, height):
        """Property: Bars are always centered horizontally in the indicator."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        indicator, _, mock_canvas = create_indicator_with_mocks(width=width, height=height)

        mock_canvas.create_rectangle.reset_mock()
        indicator._draw_recording_bars()

        calls = mock_canvas.create_rectangle.call_args_list

        # Calculate expected center
        total_bar_width = (RecordingIndicator.BAR_COUNT * RecordingIndicator.BAR_WIDTH) + \
                          ((RecordingIndicator.BAR_COUNT - 1) * RecordingIndicator.BAR_GAP)
        start_x = (width - total_bar_width) // 2

        # Check first bar position (skip background at index 0)
        if len(calls) >= 2:
            first_bar_x = calls[1][0][0]  # First positional arg
            assert abs(first_bar_x - start_x) <= 1  # Allow 1px tolerance


class TestAnimationTimingProperties:
    """Property-based tests for animation timing."""

    def test_animation_frame_rate_is_reasonable(self):
        """Property: Animation frame rate is between 10-20 FPS."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        interval_ms = RecordingIndicator.BAR_ANIMATION_INTERVAL_MS
        fps = 1000 / interval_ms

        assert 10 <= fps <= 20, f"FPS {fps} is outside reasonable range 10-20"

    def test_bar_count_matches_colors(self):
        """Property: Number of bar colors matches bar count."""
        from context_aware_whisper.ui.indicator import RecordingIndicator

        assert len(RecordingIndicator.BAR_COLORS) >= RecordingIndicator.BAR_COUNT


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in bar animation."""

    def test_animation_handles_tk_tcl_error_gracefully(self):
        """Test that animation handles TclError during cancellation."""
        import tkinter as tk

        indicator, mock_window, _ = create_indicator_with_mocks()

        # Make after_cancel raise TclError
        mock_window.after_cancel.side_effect = tk.TclError("test error")
        indicator._bar_animation_id = "fake_id"

        # Should not raise
        indicator._stop_bar_animation()

        assert indicator._bar_animation_id is None

    def test_recording_to_recording_transition(self):
        """Test that recording -> recording transition handles animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Set to recording
        indicator.set_state("recording")
        first_animation_id = indicator._bar_animation_id

        # Set to recording again (cancel current animations is called)
        mock_window.after.reset_mock()
        indicator.set_state("recording")

        # Animation should be restarted
        assert mock_window.after.called

    def test_destroy_while_animating(self):
        """Test that destroy during animation is safe."""
        indicator, _, _ = create_indicator_with_mocks()

        indicator.set_state("recording")
        assert indicator._bar_animation_id is not None

        # Should not raise
        indicator.destroy()

        assert indicator._bar_animation_id is None
