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
    """Custom NSView that draws the recording indicator as a simple colored dot."""

    def initWithFrame_(self, frame):
        self = objc.super(IndicatorView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._state = "idle"
        return self

    def drawRect_(self, rect):
        """Draw a simple colored circle based on state."""
        bounds = self.bounds()

        # Colors for different states (amber/blue theme)
        if self._state == "recording":
            # Amber color for recording
            color = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.75, 0.0, 1.0)
        elif self._state == "transcribing":
            # Blue color for transcribing
            color = NSColor.colorWithRed_green_blue_alpha_(0.0, 0.48, 1.0, 1.0)
        elif self._state == "success":
            color = NSColor.greenColor()
        elif self._state == "error":
            color = NSColor.orangeColor()
        else:
            return  # Don't draw anything for idle

        # Draw filled circle
        size = min(bounds.size.width, bounds.size.height) - 4
        x = (bounds.size.width - size) / 2
        y = (bounds.size.height - size) / 2
        oval_rect = NSMakeRect(x, y, size, size)

        color.setFill()
        path = NSBezierPath.bezierPathWithOvalInRect_(oval_rect)
        path.fill()

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
