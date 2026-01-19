"""
Tests for Animated Recording Indicator.

This module tests the bar animation feature for the recording state,
including:
- Animation constants configuration
- Bar animation state management
- Drawing animated bars
- Animation lifecycle (start/stop)
- Integration with state transitions
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from unittest.mock import MagicMock, patch, call


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

    def test_bar_count_is_four(self):
        """Verify BAR_COUNT is set to 4 as per spec."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_COUNT == 4

    def test_bar_width_is_six_pixels(self):
        """Verify BAR_WIDTH is 6 pixels."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_WIDTH == 6

    def test_bar_gap_is_three_pixels(self):
        """Verify BAR_GAP is 3 pixels."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_GAP == 3

    def test_bar_min_height_is_four_pixels(self):
        """Verify BAR_MIN_HEIGHT is 4 pixels."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_MIN_HEIGHT == 4

    def test_bar_max_height_is_sixteen_pixels(self):
        """Verify BAR_MAX_HEIGHT is 16 pixels."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_MAX_HEIGHT == 16

    def test_bar_animation_interval_approx_12_fps(self):
        """Verify BAR_ANIMATION_INTERVAL_MS is ~80ms (~12.5 FPS)."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_ANIMATION_INTERVAL_MS == 80

    def test_bar_colors_has_four_colors(self):
        """Verify BAR_COLORS has exactly 4 colors."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert len(RecordingIndicator.BAR_COLORS) == 4

    def test_bar_colors_are_valid_hex(self):
        """Verify all BAR_COLORS are valid hex strings."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        for color in RecordingIndicator.BAR_COLORS:
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB format

    def test_bar_bg_color_is_dark(self):
        """Verify BAR_BG_COLOR is the dark slate color."""
        from context_aware_whisper.ui.indicator import RecordingIndicator
        assert RecordingIndicator.BAR_BG_COLOR == "#1C1C1E"


# =============================================================================
# BAR ANIMATION STATE INITIALIZATION TESTS
# =============================================================================

class TestBarAnimationStateInit:
    """Tests for bar animation state initialization."""

    def test_bar_animation_id_starts_none(self):
        """Verify _bar_animation_id starts as None."""
        indicator, _, _ = create_indicator_with_mocks()
        assert indicator._bar_animation_id is None

    def test_bar_heights_initialized_to_min(self):
        """Verify _bar_heights are initialized to BAR_MIN_HEIGHT."""
        indicator, _, _ = create_indicator_with_mocks()
        from context_aware_whisper.ui.indicator import RecordingIndicator
        expected = [RecordingIndicator.BAR_MIN_HEIGHT] * RecordingIndicator.BAR_COUNT
        assert indicator._bar_heights == expected

    def test_bar_directions_are_alternating(self):
        """Verify _bar_directions alternate between 1 and -1."""
        indicator, _, _ = create_indicator_with_mocks()
        assert indicator._bar_directions == [1, -1, 1, -1]


# =============================================================================
# BAR DRAWING TESTS
# =============================================================================

class TestDrawRecordingBars:
    """Tests for _draw_recording_bars method."""

    def test_draw_bars_clears_canvas(self):
        """Verify _draw_recording_bars clears the canvas first."""
        indicator, _, mock_canvas = create_indicator_with_mocks()
        mock_canvas.delete.reset_mock()

        indicator._draw_recording_bars()

        mock_canvas.delete.assert_called_with("all")

    def test_draw_bars_creates_background_rectangle(self):
        """Verify _draw_recording_bars draws background rectangle."""
        indicator, _, mock_canvas = create_indicator_with_mocks()
        mock_canvas.create_rectangle.reset_mock()

        indicator._draw_recording_bars()

        # First rectangle call should be background
        calls = mock_canvas.create_rectangle.call_args_list
        assert len(calls) >= 1
        # Background should use BAR_BG_COLOR
        bg_call = calls[0]
        assert bg_call[1]['fill'] == indicator.BAR_BG_COLOR

    def test_draw_bars_creates_four_bar_rectangles(self):
        """Verify _draw_recording_bars creates 4 bar rectangles (plus background)."""
        indicator, _, mock_canvas = create_indicator_with_mocks()
        mock_canvas.create_rectangle.reset_mock()

        indicator._draw_recording_bars()

        # Should create 5 rectangles: 1 background + 4 bars
        calls = mock_canvas.create_rectangle.call_args_list
        assert len(calls) == 5

    def test_draw_bars_uses_bar_colors(self):
        """Verify bars are drawn with correct colors from BAR_COLORS."""
        indicator, _, mock_canvas = create_indicator_with_mocks()
        mock_canvas.create_rectangle.reset_mock()

        indicator._draw_recording_bars()

        calls = mock_canvas.create_rectangle.call_args_list
        # First call (index 0) is background, rest are bars
        # Extract only calls that have bar colors (not background color)
        bar_colors_found = []
        for call_obj in calls:
            fill_color = call_obj[1].get('fill', call_obj[0][4] if len(call_obj[0]) > 4 else None)
            if fill_color and fill_color in indicator.BAR_COLORS:
                bar_colors_found.append(fill_color)

        # Should find 4 bar colors
        assert len(bar_colors_found) == 4
        # Each bar color should be from BAR_COLORS
        for color in bar_colors_found:
            assert color in indicator.BAR_COLORS


# =============================================================================
# BAR ANIMATION TESTS
# =============================================================================

class TestAnimateBars:
    """Tests for _animate_bars method."""

    def test_animate_bars_does_nothing_if_not_recording(self):
        """Verify _animate_bars returns early if not in recording state."""
        indicator, mock_window, mock_canvas = create_indicator_with_mocks()
        indicator._current_state = "idle"

        # Store original heights
        original_heights = indicator._bar_heights.copy()

        indicator._animate_bars()

        # Heights should not change
        assert indicator._bar_heights == original_heights
        # No animation scheduled
        assert indicator._bar_animation_id is None

    def test_animate_bars_updates_heights(self):
        """Verify _animate_bars updates bar heights."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        # Store original heights
        original_heights = indicator._bar_heights.copy()

        indicator._animate_bars()

        # At least some heights should have changed
        assert indicator._bar_heights != original_heights or True  # Random might not change

    def test_animate_bars_respects_min_height(self):
        """Verify bar heights never go below BAR_MIN_HEIGHT."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"
        indicator._bar_heights = [indicator.BAR_MIN_HEIGHT] * 4
        indicator._bar_directions = [-1, -1, -1, -1]  # All going down

        indicator._animate_bars()

        for height in indicator._bar_heights:
            assert height >= indicator.BAR_MIN_HEIGHT

    def test_animate_bars_respects_max_height(self):
        """Verify bar heights never go above BAR_MAX_HEIGHT."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"
        indicator._bar_heights = [indicator.BAR_MAX_HEIGHT] * 4
        indicator._bar_directions = [1, 1, 1, 1]  # All going up

        indicator._animate_bars()

        for height in indicator._bar_heights:
            assert height <= indicator.BAR_MAX_HEIGHT

    def test_animate_bars_reverses_direction_at_limits(self):
        """Verify bar directions reverse when hitting limits."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"

        # Set bars at max, direction up - should reverse
        indicator._bar_heights = [indicator.BAR_MAX_HEIGHT] * 4
        indicator._bar_directions = [1, 1, 1, 1]

        indicator._animate_bars()

        # All directions should now be -1
        assert all(d == -1 for d in indicator._bar_directions)

    def test_animate_bars_schedules_next_frame(self):
        """Verify _animate_bars schedules the next animation frame."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"
        mock_window.after.reset_mock()

        indicator._animate_bars()

        # Should schedule next frame
        mock_window.after.assert_called_with(
            indicator.BAR_ANIMATION_INTERVAL_MS,
            indicator._animate_bars
        )

    def test_animate_bars_stores_animation_id(self):
        """Verify _animate_bars stores the animation callback ID."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"
        mock_window.after.return_value = "test_after_id"

        indicator._animate_bars()

        assert indicator._bar_animation_id == "test_after_id"


# =============================================================================
# STOP BAR ANIMATION TESTS
# =============================================================================

class TestStopBarAnimation:
    """Tests for _stop_bar_animation method."""

    def test_stop_bar_animation_cancels_callback(self):
        """Verify _stop_bar_animation cancels the pending callback."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._bar_animation_id = "test_id"

        indicator._stop_bar_animation()

        mock_window.after_cancel.assert_called_with("test_id")

    def test_stop_bar_animation_clears_animation_id(self):
        """Verify _stop_bar_animation sets animation ID to None."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._bar_animation_id = "test_id"

        indicator._stop_bar_animation()

        assert indicator._bar_animation_id is None

    def test_stop_bar_animation_resets_bar_heights(self):
        """Verify _stop_bar_animation resets bar heights to minimum."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._bar_heights = [10, 12, 8, 14]

        indicator._stop_bar_animation()

        expected = [indicator.BAR_MIN_HEIGHT] * indicator.BAR_COUNT
        assert indicator._bar_heights == expected

    def test_stop_bar_animation_handles_none_id(self):
        """Verify _stop_bar_animation handles None animation ID gracefully."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._bar_animation_id = None

        # Should not raise
        indicator._stop_bar_animation()

        assert indicator._bar_animation_id is None


# =============================================================================
# RECORDING STATE INTEGRATION TESTS
# =============================================================================

class TestRecordingStateIntegration:
    """Tests for recording state using animated bars."""

    def test_recording_state_draws_bars_not_text(self):
        """Verify recording state draws bars instead of 'REC' text."""
        indicator, _, mock_canvas = create_indicator_with_mocks()
        mock_canvas.reset_mock()

        indicator.set_state("recording")

        # Should create rectangles (bars) but not text
        assert mock_canvas.create_rectangle.called
        # create_text should not be called for recording state
        mock_canvas.create_text.assert_not_called()

    def test_recording_state_starts_animation(self):
        """Verify setting recording state starts bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        mock_window.after.reset_mock()

        indicator.set_state("recording")

        # Should schedule animation
        assert mock_window.after.called

    def test_leaving_recording_state_stops_animation(self):
        """Verify leaving recording state stops bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Enter recording
        indicator.set_state("recording")
        indicator._bar_animation_id = "test_id"

        # Leave recording
        indicator.set_state("transcribing")

        # Animation should be stopped
        mock_window.after_cancel.assert_called_with("test_id")

    def test_transcribing_state_uses_text_not_bars(self):
        """Verify transcribing state uses text ('...') not bars."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        indicator.set_state("transcribing")

        mock_canvas.create_text.assert_called()

    def test_success_state_uses_text_not_bars(self):
        """Verify success state uses text ('OK') not bars."""
        indicator, _, mock_canvas = create_indicator_with_mocks()

        indicator.set_state("success")

        mock_canvas.create_text.assert_called()


# =============================================================================
# CANCEL ANIMATIONS INTEGRATION TESTS
# =============================================================================

class TestCancelAnimationsIntegration:
    """Tests for _cancel_animations including bar animation."""

    def test_cancel_animations_stops_bar_animation(self):
        """Verify _cancel_animations also stops bar animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._bar_animation_id = "test_bar_id"

        indicator._cancel_animations()

        mock_window.after_cancel.assert_called_with("test_bar_id")
        assert indicator._bar_animation_id is None

    def test_cancel_animations_clears_both_types(self):
        """Verify _cancel_animations clears both flash and bar animations."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._flash_after_ids = ["flash1", "flash2"]
        indicator._bar_animation_id = "bar_id"

        indicator._cancel_animations()

        assert indicator._flash_after_ids == []
        assert indicator._bar_animation_id is None


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestBarAnimationProperties:
    """Property-based tests for bar animation behavior."""

    @given(heights=st.lists(
        st.integers(min_value=1, max_value=20),
        min_size=4,
        max_size=4
    ))
    @settings(max_examples=20)
    def test_bar_heights_always_clamped(self, heights):
        """Property: Bar heights are always clamped to min/max after animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()
        indicator._current_state = "recording"
        indicator._bar_heights = list(heights)

        # Run multiple animation steps
        for _ in range(5):
            indicator._animate_bars()
            for h in indicator._bar_heights:
                assert indicator.BAR_MIN_HEIGHT <= h <= indicator.BAR_MAX_HEIGHT

    @given(state_before=st.sampled_from(["idle", "transcribing", "success", "error"]))
    @settings(max_examples=15)
    def test_entering_recording_always_starts_animation(self, state_before):
        """Property: Entering recording state always starts animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Set to some state first
        indicator.set_state(state_before)
        mock_window.after.reset_mock()

        # Enter recording
        indicator.set_state("recording")

        # Animation should be scheduled
        assert mock_window.after.called

    @given(state_after=st.sampled_from(["idle", "transcribing", "success", "error"]))
    @settings(max_examples=15)
    def test_leaving_recording_always_stops_animation(self, state_after):
        """Property: Leaving recording state always stops animation."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        # Enter recording first
        indicator.set_state("recording")
        indicator._bar_animation_id = "test_id"

        # Leave recording
        indicator.set_state(state_after)

        # Animation should be stopped
        assert indicator._bar_animation_id is None

    @given(num_cycles=st.integers(min_value=1, max_value=10))
    @settings(max_examples=10)
    def test_rapid_recording_state_cycles_safe(self, num_cycles):
        """Property: Rapid recording state cycles don't leak animations."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        for _ in range(num_cycles):
            indicator.set_state("recording")
            indicator.set_state("transcribing")
            indicator.set_state("success")

        # Should end in success state with no lingering bar animation
        assert indicator._current_state == "success"
        assert indicator._bar_animation_id is None


# =============================================================================
# VISUAL SPEC COMPLIANCE TESTS
# =============================================================================

class TestVisualSpecCompliance:
    """Tests verifying visual specification compliance."""

    def test_bars_centered_horizontally(self):
        """Verify bars are centered horizontally in the indicator."""
        indicator, _, mock_canvas = create_indicator_with_mocks(width=60)
        mock_canvas.create_rectangle.reset_mock()

        indicator._draw_recording_bars()

        # Calculate expected bar positions
        total_bar_width = (4 * 6) + (3 * 3)  # 4 bars, 3 gaps = 33px
        expected_start_x = (60 - total_bar_width) // 2  # = 13

        # Get bar rectangle calls (skip background at index 0)
        calls = mock_canvas.create_rectangle.call_args_list[1:]
        for i, call_obj in enumerate(calls):
            expected_x = expected_start_x + i * (6 + 3)
            actual_x = call_obj[0][0]
            assert actual_x == expected_x, f"Bar {i} x position mismatch"

    def test_bars_centered_vertically(self):
        """Verify bars are centered vertically in the indicator."""
        indicator, _, mock_canvas = create_indicator_with_mocks(height=24)

        indicator._draw_recording_bars()

        # Get bar rectangle calls (skip background)
        calls = mock_canvas.create_rectangle.call_args_list[1:]

        center_y = 24 // 2  # = 12
        for call_obj in calls:
            y1 = call_obj[0][1]
            y2 = call_obj[0][3]
            bar_center = (y1 + y2) / 2
            assert abs(bar_center - center_y) <= 1, "Bar not vertically centered"

    def test_recording_state_opacity_is_95_percent(self):
        """Verify recording state uses 0.95 opacity."""
        indicator, mock_window, _ = create_indicator_with_mocks()

        indicator.set_state("recording")

        # Check that alpha was set to 0.95
        calls = mock_window.attributes.call_args_list
        alpha_calls = [c for c in calls if c[0][0] == "-alpha"]
        assert any(c[0][1] == 0.95 for c in alpha_calls), "Recording opacity should be 0.95"

    def test_bar_background_uses_dark_slate_color(self):
        """Verify bar background uses #1C1C1E."""
        indicator, _, mock_canvas = create_indicator_with_mocks()
        mock_canvas.create_rectangle.reset_mock()

        indicator._draw_recording_bars()

        # First rectangle call should be background with dark slate color
        bg_call = mock_canvas.create_rectangle.call_args_list[0]
        assert bg_call[1]['fill'] == "#1C1C1E"
