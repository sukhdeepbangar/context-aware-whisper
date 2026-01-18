"""
Native macOS Recording Indicator using NSPanel.

Uses NSPanel with NSNonactivatingPanelMask to show an overlay that
NEVER steals focus from the active application.

References:
- https://developer.apple.com/documentation/appkit/nspanel
- https://developer.apple.com/documentation/appkit/nswindow/stylemask-swift.struct/nonactivatingpanel
"""

import sys
from typing import Optional, Callable

# Only available on macOS
if sys.platform != "darwin":
    raise ImportError("native_indicator is only available on macOS")

try:
    from AppKit import (
        NSPanel,
        NSView,
        NSColor,
        NSFont,
        NSMakeRect,
        NSBezierPath,
        NSFloatingWindowLevel,
        NSBackingStoreBuffered,
        NSScreen,
    )
    import objc
except ImportError as e:
    raise ImportError(f"PyObjC is required for native_indicator: {e}")


# Style masks
NSBorderlessWindowMask = 0
NSNonactivatingPanelMask = 1 << 7  # 128 - prevents panel from activating app


class IndicatorView(NSView):
    """Custom NSView that draws the recording indicator."""

    def initWithFrame_(self, frame):
        self = objc.super(IndicatorView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._state = "idle"
        self._bar_heights = [8, 12, 6, 10]  # Static varied heights
        self._bar_colors = [
            NSColor.colorWithRed_green_blue_alpha_(1.0, 0.23, 0.19, 1.0),  # #FF3B30
            NSColor.colorWithRed_green_blue_alpha_(1.0, 0.42, 0.36, 1.0),  # #FF6B5B
            NSColor.colorWithRed_green_blue_alpha_(1.0, 0.58, 0.0, 1.0),   # #FF9500
            NSColor.colorWithRed_green_blue_alpha_(1.0, 0.42, 0.36, 1.0),  # #FF6B5B
        ]
        self._bg_color = NSColor.colorWithRed_green_blue_alpha_(0.11, 0.11, 0.12, 0.95)

        return self

    def drawRect_(self, rect):
        """Draw the indicator based on current state."""
        # Draw background
        self._bg_color.setFill()
        NSBezierPath.fillRect_(self.bounds())

        if self._state == "recording":
            self._draw_bars()
        elif self._state == "transcribing":
            self._draw_text("...", NSColor.colorWithRed_green_blue_alpha_(1.0, 0.58, 0.0, 1.0))
        elif self._state == "success":
            self._draw_text("OK", NSColor.colorWithRed_green_blue_alpha_(0.2, 0.78, 0.35, 1.0))
        elif self._state == "error":
            self._draw_text("ERR", NSColor.colorWithRed_green_blue_alpha_(1.0, 0.23, 0.19, 1.0))

    def _draw_bars(self):
        """Draw audio visualizer bars (static for now to avoid timer issues)."""
        bounds = self.bounds()
        bar_width = 6
        bar_gap = 3
        bar_count = 4
        total_width = bar_count * bar_width + (bar_count - 1) * bar_gap
        start_x = (bounds.size.width - total_width) / 2
        center_y = bounds.size.height / 2

        for i, height in enumerate(self._bar_heights):
            x = start_x + i * (bar_width + bar_gap)
            y = center_y - height / 2
            rect = NSMakeRect(x, y, bar_width, height)
            self._bar_colors[i].setFill()
            NSBezierPath.fillRect_(rect)

    def _draw_text(self, text, color):
        """Draw centered text."""
        bounds = self.bounds()
        font = NSFont.boldSystemFontOfSize_(10)
        from AppKit import NSAttributedString, NSFontAttributeName, NSForegroundColorAttributeName
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: color,
        }
        attr_str = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        size = attr_str.size()
        x = (bounds.size.width - size.width) / 2
        y = (bounds.size.height - size.height) / 2
        attr_str.drawAtPoint_((x, y))

    def setState_(self, state):
        """Set the indicator state."""
        self._state = state
        self.setNeedsDisplay_(True)


class NativeRecordingIndicator:
    """
    Native macOS recording indicator using NSPanel.

    This indicator NEVER steals focus from the active application because
    it uses NSNonactivatingPanelMask.
    """

    def __init__(self, width: int = 60, height: int = 24, position: str = "top-center"):
        """
        Initialize native recording indicator.

        Args:
            width: Width in pixels
            height: Height in pixels
            position: Position on screen (top-center, top-right, etc.)
        """
        self.width = width
        self.height = height
        self._position = position
        self._current_state = "idle"
        self._panel: Optional[NSPanel] = None
        self._view: Optional[IndicatorView] = None

        self._create_panel()

    def _create_panel(self):
        """Create the NSPanel with non-activating style."""
        # Calculate position
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        x = (screen_frame.size.width - self.width) / 2
        y = screen_frame.size.height - self.height - 10  # 10px from top

        frame = NSMakeRect(x, y, self.width, self.height)

        # Create panel with borderless + non-activating style
        style_mask = NSBorderlessWindowMask | NSNonactivatingPanelMask

        self._panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            NSBackingStoreBuffered,
            False
        )

        # Configure panel behavior
        self._panel.setLevel_(NSFloatingWindowLevel)  # Float above other windows
        self._panel.setOpaque_(False)
        self._panel.setBackgroundColor_(NSColor.clearColor())
        self._panel.setHasShadow_(False)
        self._panel.setIgnoresMouseEvents_(True)  # Click-through
        self._panel.setCollectionBehavior_(
            (1 << 0) |  # canJoinAllSpaces
            (1 << 4) |  # stationary
            (1 << 6)    # ignoresCycle
        )

        # CRITICAL: These prevent the panel from ever becoming key/main
        # But NSNonactivatingPanelMask already handles this at the window level

        # Create and set content view
        self._view = IndicatorView.alloc().initWithFrame_(NSMakeRect(0, 0, self.width, self.height))
        self._panel.setContentView_(self._view)

    def set_state(self, state: str) -> None:
        """
        Set the indicator state.

        Args:
            state: One of "idle", "recording", "transcribing", "success", "error"
        """
        self._current_state = state

        if state == "idle":
            self.hide()
        else:
            self._view.setState_(state)
            self.show()

    def show(self) -> None:
        """Show the indicator without stealing focus."""
        self._panel.orderFrontRegardless()

    def hide(self) -> None:
        """Hide the indicator."""
        self._panel.orderOut_(None)

    def destroy(self) -> None:
        """Clean up resources."""
        if self._panel:
            self._panel.close()


def create_native_indicator(width: int = 60, height: int = 24, position: str = "top-center"):
    """
    Factory function to create a native indicator.

    Returns None if not on macOS or if creation fails.
    """
    if sys.platform != "darwin":
        return None
    try:
        return NativeRecordingIndicator(width, height, position)
    except Exception:
        return None
