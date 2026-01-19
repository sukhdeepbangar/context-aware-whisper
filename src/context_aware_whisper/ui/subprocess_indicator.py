#!/usr/bin/env python3
"""
Subprocess Indicator - Focus-Preserving Recording Overlay

This script MUST be run as a separate subprocess. It sets
NSApplicationActivationPolicyProhibited BEFORE creating any windows,
which ensures it can NEVER steal focus from other applications.

Usage:
    python subprocess_indicator.py

Communication via stdin:
    recording\n      - Show recording state (red pulsing dots)
    transcribing\n   - Show transcribing state (orange animated dots)
    success\n        - Flash success (green checkmark), then hide
    error\n          - Flash error (red X), then hide
    idle\n           - Hide indicator
    exit\n           - Terminate subprocess

Outputs "ready\n" to stdout when initialized and ready for commands.
"""

import sys
import select
import threading
import time
from typing import Optional

# =============================================================================
# CRITICAL: Set activation policy BEFORE any other AppKit/Cocoa imports
# This MUST happen at module level, before any window/app is created
# =============================================================================
if sys.platform == "darwin":
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyProhibited
        # Get or create shared application instance
        app = NSApplication.sharedApplication()
        # Set policy immediately - this prevents the app from EVER stealing focus
        app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    except ImportError:
        print("ERROR: PyObjC not available", file=sys.stderr)
        sys.exit(1)
else:
    print("ERROR: This script only works on macOS", file=sys.stderr)
    sys.exit(1)

# Now safe to import remaining AppKit components
from AppKit import (
    NSPanel,
    NSView,
    NSColor,
    NSMakeRect,
    NSBezierPath,
    NSFloatingWindowLevel,
    NSBackingStoreBuffered,
    NSScreen,
    NSRunLoop,
    NSDate,
    NSTimer,
    NSFont,
)
import objc

# Style masks
NSBorderlessWindowMask = 0
NSNonactivatingPanelMask = 1 << 7  # 128 - prevents panel from activating app

# Visual design constants
INDICATOR_WIDTH = 80
INDICATOR_HEIGHT = 30
CORNER_RADIUS = 6
TOP_MARGIN = 40
BACKGROUND_COLOR = (0.11, 0.11, 0.12, 0.9)  # #1C1C1E at 90% alpha

# Colors
COLOR_RED = (1.0, 0.231, 0.188)      # #FF3B30
COLOR_ORANGE = (1.0, 0.584, 0.0)     # #FF9500
COLOR_GREEN = (0.204, 0.78, 0.349)   # #34C759
COLOR_WHITE = (1.0, 1.0, 1.0)


class IndicatorContentView(NSView):
    """
    Custom NSView that draws the indicator content based on state.

    States:
    - recording: 3 red dots pulsing
    - transcribing: 3 orange dots animating
    - success: green checkmark
    - error: red X
    - idle: nothing (hidden)
    """

    def initWithFrame_(self, frame):
        self = objc.super(IndicatorContentView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._state = "idle"
        self._animation_phase = 0  # For pulsing/animation
        return self

    def isFlipped(self):
        """Use top-left coordinate system."""
        return True

    def drawRect_(self, rect):
        """Draw the indicator content."""
        bounds = self.bounds()

        # Draw rounded rectangle background
        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, CORNER_RADIUS, CORNER_RADIUS
        )
        bg_color = NSColor.colorWithRed_green_blue_alpha_(*BACKGROUND_COLOR)
        bg_color.setFill()
        bg_path.fill()

        if self._state == "idle":
            return

        # Center of the view
        cx = bounds.size.width / 2
        cy = bounds.size.height / 2

        if self._state == "recording":
            self._draw_recording_dots(cx, cy)
        elif self._state == "transcribing":
            self._draw_transcribing_dots(cx, cy)
        elif self._state == "success":
            self._draw_checkmark(cx, cy)
        elif self._state == "error":
            self._draw_error_x(cx, cy)

    def _draw_recording_dots(self, cx, cy):
        """Draw 3 red pulsing dots."""
        color = NSColor.colorWithRed_green_blue_alpha_(*COLOR_RED, 1.0)

        # Pulse sizes based on animation phase
        base_size = 6
        pulse_sizes = [
            base_size + 2 * (1 - abs((self._animation_phase - 0) % 3 - 1.5) / 1.5),
            base_size + 2 * (1 - abs((self._animation_phase - 1) % 3 - 1.5) / 1.5),
            base_size + 2 * (1 - abs((self._animation_phase - 2) % 3 - 1.5) / 1.5),
        ]

        spacing = 16
        positions = [cx - spacing, cx, cx + spacing]

        for i, (x, size) in enumerate(zip(positions, pulse_sizes)):
            color.setFill()
            oval = NSMakeRect(x - size/2, cy - size/2, size, size)
            path = NSBezierPath.bezierPathWithOvalInRect_(oval)
            path.fill()

    def _draw_transcribing_dots(self, cx, cy):
        """Draw 3 orange dots with wave animation."""
        color = NSColor.colorWithRed_green_blue_alpha_(*COLOR_ORANGE, 1.0)

        spacing = 16
        positions = [cx - spacing, cx, cx + spacing]
        base_size = 6

        for i, x in enumerate(positions):
            # Wave animation offset
            offset = 4 * ((self._animation_phase + i) % 3 - 1)
            y = cy + offset

            color.setFill()
            oval = NSMakeRect(x - base_size/2, y - base_size/2, base_size, base_size)
            path = NSBezierPath.bezierPathWithOvalInRect_(oval)
            path.fill()

    def _draw_checkmark(self, cx, cy):
        """Draw a green checkmark."""
        color = NSColor.colorWithRed_green_blue_alpha_(*COLOR_GREEN, 1.0)
        color.setStroke()

        path = NSBezierPath.bezierPath()
        path.setLineWidth_(3.0)
        path.setLineCapStyle_(1)  # Round cap
        path.setLineJoinStyle_(1)  # Round join

        # Checkmark path
        path.moveToPoint_((cx - 8, cy))
        path.lineToPoint_((cx - 2, cy + 6))
        path.lineToPoint_((cx + 10, cy - 6))
        path.stroke()

    def _draw_error_x(self, cx, cy):
        """Draw a red X."""
        color = NSColor.colorWithRed_green_blue_alpha_(*COLOR_RED, 1.0)
        color.setStroke()

        path = NSBezierPath.bezierPath()
        path.setLineWidth_(3.0)
        path.setLineCapStyle_(1)  # Round cap

        size = 8
        path.moveToPoint_((cx - size, cy - size))
        path.lineToPoint_((cx + size, cy + size))
        path.moveToPoint_((cx + size, cy - size))
        path.lineToPoint_((cx - size, cy + size))
        path.stroke()

    def setState_(self, state):
        """Set the indicator state."""
        self._state = state
        self._animation_phase = 0
        self.setNeedsDisplay_(True)

    def setAnimationPhase_(self, phase):
        """Set animation phase for animated states."""
        self._animation_phase = phase
        self.setNeedsDisplay_(True)

    def getState(self):
        """Get current state."""
        return self._state


class SubprocessIndicator:
    """
    Subprocess indicator that can never steal focus.

    Uses NSPanel with NSNonactivatingPanelMask and runs in a process
    that has NSApplicationActivationPolicyProhibited set.
    """

    def __init__(self):
        self._panel: Optional[NSPanel] = None
        self._view: Optional[IndicatorContentView] = None
        self._animation_timer: Optional[NSTimer] = None
        self._hide_timer: Optional[NSTimer] = None
        self._current_state = "idle"

        self._create_panel()

    def _create_panel(self):
        """Create the indicator panel."""
        # Get screen dimensions
        screen = NSScreen.mainScreen()
        screen_frame = screen.visibleFrame()  # Account for menu bar

        # Position at center-top
        x = screen_frame.origin.x + (screen_frame.size.width - INDICATOR_WIDTH) / 2
        y = screen_frame.origin.y + screen_frame.size.height - INDICATOR_HEIGHT - TOP_MARGIN

        frame = NSMakeRect(x, y, INDICATOR_WIDTH, INDICATOR_HEIGHT)

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
        self._panel.setHasShadow_(True)
        self._panel.setIgnoresMouseEvents_(True)  # Click-through

        # Collection behavior: join all spaces, stationary, ignore cycle
        self._panel.setCollectionBehavior_(
            (1 << 0) |  # canJoinAllSpaces
            (1 << 4) |  # stationary
            (1 << 6)    # ignoresCycle
        )

        # Prevent panel from ever becoming key/main window
        # Note: The class methods would override this, but we're using NSPanel
        # which respects these settings when NSNonactivatingPanelMask is set

        # Create content view
        self._view = IndicatorContentView.alloc().initWithFrame_(
            NSMakeRect(0, 0, INDICATOR_WIDTH, INDICATOR_HEIGHT)
        )
        self._panel.setContentView_(self._view)

    def set_state(self, state: str):
        """Set the indicator state."""
        self._current_state = state

        # Cancel any existing timers
        self._cancel_timers()

        if state == "idle":
            self._hide()
        elif state in ("recording", "transcribing"):
            self._view.setState_(state)
            self._show()
            self._start_animation()
        elif state in ("success", "error"):
            self._view.setState_(state)
            self._show()
            # Auto-hide after 800ms
            self._schedule_hide(0.8)

    def _show(self):
        """Show the panel without stealing focus."""
        self._panel.orderFrontRegardless()

    def _hide(self):
        """Hide the panel."""
        self._panel.orderOut_(None)

    def _start_animation(self):
        """Start animation timer for recording/transcribing states."""
        def animate_tick():
            if self._current_state in ("recording", "transcribing"):
                phase = (self._view._animation_phase + 0.5) % 3
                self._view.setAnimationPhase_(phase)

        # Create a repeating timer
        self._animation_timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.15,  # 150ms interval
            True,
            lambda timer: animate_tick()
        )

    def _schedule_hide(self, delay: float):
        """Schedule hiding after a delay."""
        def hide_callback():
            self.set_state("idle")

        self._hide_timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            delay,
            False,
            lambda timer: hide_callback()
        )

    def _cancel_timers(self):
        """Cancel all pending timers."""
        if self._animation_timer:
            self._animation_timer.invalidate()
            self._animation_timer = None
        if self._hide_timer:
            self._hide_timer.invalidate()
            self._hide_timer = None

    def cleanup(self):
        """Clean up resources."""
        self._cancel_timers()
        if self._panel:
            self._panel.close()
            self._panel = None


def run_event_loop(indicator: SubprocessIndicator):
    """
    Run the main event loop, reading commands from stdin.

    Uses select() to check for stdin input without blocking,
    while also processing the NSRunLoop for UI updates.
    """
    # Signal that we're ready
    print("ready", flush=True)

    run_loop = NSRunLoop.currentRunLoop()
    running = True

    while running:
        # Process pending UI events (animations, timers)
        # Run for a short interval to allow stdin checking
        run_loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))

        # Check for stdin input (non-blocking)
        readable, _, _ = select.select([sys.stdin], [], [], 0)

        if readable:
            try:
                line = sys.stdin.readline()
                if not line:
                    # EOF - parent process closed stdin
                    running = False
                    continue

                command = line.strip().lower()

                if command == "exit":
                    running = False
                elif command in ("recording", "transcribing", "success", "error", "idle"):
                    indicator.set_state(command)
                elif command:
                    # Unknown command - ignore but log
                    print(f"Unknown command: {command}", file=sys.stderr)
            except Exception as e:
                print(f"Error reading command: {e}", file=sys.stderr)

    indicator.cleanup()


def main():
    """Main entry point."""
    try:
        indicator = SubprocessIndicator()
        run_event_loop(indicator)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
