"""
Recording Indicator Component

Provides a minimal, always-on-top visual indicator showing the application state.
"""

import random
import sys
import tkinter as tk
from typing import Optional, List

# PyObjC imports for macOS focus prevention
if sys.platform == "darwin":
    try:
        from AppKit import NSFloatingWindowLevel, NSApp
        PYOBJC_AVAILABLE = True
    except ImportError:
        PYOBJC_AVAILABLE = False
else:
    PYOBJC_AVAILABLE = False


# Valid position values
VALID_POSITIONS = ["top-center", "top-right", "top-left", "bottom-center", "bottom-right", "bottom-left"]


def get_current_platform() -> str:
    """Detect the current platform."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    elif sys.platform.startswith("linux"):
        return "linux"
    return "unknown"


class RecordingIndicator:
    """
    A minimal, always-on-top indicator window showing recording state.

    States:
    - idle: Hidden or very dim (dark gray)
    - recording: Red with "REC" text
    - transcribing: Orange with "..." text
    - success: Green with "OK" text (flashes briefly with animation)
    - error: Red with "ERR" text (flashes briefly with animation)
    """

    # State configuration: (bg_color, text_color, display_text, opacity)
    STATE_CONFIG = {
        "idle": ("#333333", "#FFFFFF", "", 0.3),
        "recording": ("#FF3B30", "#FFFFFF", "REC", 0.95),
        "transcribing": ("#FF9500", "#FFFFFF", "...", 0.95),
        "success": ("#34C759", "#FFFFFF", "OK", 0.95),
        "error": ("#FF3B30", "#FFFFFF", "ERR", 0.95),
    }

    # Margin from screen edges in pixels
    EDGE_MARGIN = 10

    # Flash animation configuration
    FLASH_DURATION_MS = 1500  # Total duration before returning to idle
    FLASH_STEPS = 6  # Number of animation steps
    FLASH_INTERVAL_MS = 100  # Time between animation steps

    # Bar animation configuration
    BAR_COUNT = 4
    BAR_WIDTH = 6
    BAR_GAP = 3
    BAR_MIN_HEIGHT = 4
    BAR_MAX_HEIGHT = 16
    BAR_ANIMATION_INTERVAL_MS = 80  # ~12.5 FPS

    # Bar colors (red to orange gradient)
    BAR_COLORS = ["#FF3B30", "#FF6B5B", "#FF9500", "#FF6B5B"]
    BAR_BG_COLOR = "#1C1C1E"

    def __init__(
        self,
        width: int = 60,
        height: int = 24,
        root: Optional[tk.Tk] = None,
        position: str = "top-center"
    ):
        """
        Initialize recording indicator.

        Args:
            width: Width of indicator in pixels
            height: Height of indicator in pixels
            root: Optional tkinter root window (for testing)
            position: Position on screen. One of: top-center, top-right, top-left,
                     bottom-center, bottom-right, bottom-left. Default: top-center.
        """
        self.width = width
        self.height = height
        self._current_state = "idle"
        self._flash_after_ids: List[str] = []  # Track all animation scheduled callbacks
        self._position = position if position in VALID_POSITIONS else "top-center"
        self._platform = get_current_platform()
        self._transparency_supported = True

        # Bar animation state
        self._bar_animation_id: Optional[str] = None
        self._bar_heights: List[int] = [self.BAR_MIN_HEIGHT] * self.BAR_COUNT
        self._bar_directions: List[int] = [1, -1, 1, -1]  # Alternating up/down

        # Create window if root not provided (for testing purposes)
        if root is None:
            self.window = tk.Toplevel()
        else:
            self.window = tk.Toplevel(root)

        # Configure window
        self.window.withdraw()  # Start hidden
        self.window.overrideredirect(True)  # No window decorations
        self.window.attributes("-topmost", True)  # Always on top

        # Platform-specific focus prevention
        self._setup_focus_prevention()

        # Platform-specific transparency setup
        self._setup_transparency()

        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.window,
            width=width,
            height=height,
            highlightthickness=0,
            bg="white"
        )
        self.canvas.pack()

        # Draw initial state
        self._draw_state()

        # Position window on primary display
        self._position_window()

    def _setup_focus_prevention(self) -> None:
        """Configure platform-specific settings to prevent stealing focus."""
        try:
            if self._platform == "macos":
                self._setup_macos_focus_prevention()
            elif self._platform == "linux":
                # Linux: Set window type to prevent focus
                # This works with most window managers
                try:
                    self.window.attributes('-type', 'notification')
                except tk.TclError:
                    # Fallback: try splash type
                    try:
                        self.window.attributes('-type', 'splash')
                    except tk.TclError:
                        pass
            # Windows: overrideredirect(True) is usually sufficient
        except Exception:
            # If focus prevention fails, continue anyway
            pass

    def _setup_macos_focus_prevention(self) -> None:
        """Configure macOS-specific window properties to prevent focus stealing.

        Uses PyObjC to access the underlying NSWindow and configure it to not
        take keyboard focus when shown.
        """
        if not PYOBJC_AVAILABLE:
            return

        try:
            # Force window to be created and mapped first
            self.window.update_idletasks()

            # On macOS, we need to find the NSWindow for our tkinter window.
            # The window ID from tkinter is a CGWindowID, not a pointer.
            # We use NSApp to iterate through windows to find ours.
            try:
                from AppKit import NSApp

                # Get the tkinter window's screen position to identify it
                self.window.update()
                tk_x = self.window.winfo_x()
                tk_y = self.window.winfo_y()
                tk_width = self.window.winfo_width()
                tk_height = self.window.winfo_height()

                # Find the matching NSWindow
                nswindow = None
                for win in NSApp.windows():
                    frame = win.frame()
                    # Match by approximate position and size
                    # Note: Y coordinate is flipped in Cocoa (origin at bottom-left)
                    if (abs(frame.origin.x - tk_x) < 5 and
                        abs(frame.size.width - tk_width) < 5 and
                        abs(frame.size.height - tk_height) < 5):
                        nswindow = win
                        break

                if nswindow is None:
                    return

            except Exception:
                return

            # Prevent window from becoming key window (no keyboard focus)
            if hasattr(nswindow, 'setCanBecomeKey_'):
                nswindow.setCanBecomeKey_(False)

            # Prevent window from becoming main window
            if hasattr(nswindow, 'setCanBecomeMain_'):
                nswindow.setCanBecomeMain_(False)

            # Set window level to floating (above normal windows)
            if hasattr(nswindow, 'setLevel_'):
                nswindow.setLevel_(NSFloatingWindowLevel)

            # Prevent window from hiding on deactivate
            if hasattr(nswindow, 'setHidesOnDeactivate_'):
                nswindow.setHidesOnDeactivate_(False)

            # Set collection behavior to join all spaces and not be part of window cycling
            if hasattr(nswindow, 'setCollectionBehavior_'):
                # NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
                # NSWindowCollectionBehaviorStationary = 1 << 4
                # NSWindowCollectionBehaviorIgnoresCycle = 1 << 6
                behavior = (1 << 0) | (1 << 4) | (1 << 6)
                nswindow.setCollectionBehavior_(behavior)

        except Exception:
            # Silently fail - focus prevention is best-effort
            pass

    def _setup_transparency(self) -> None:
        """Configure platform-specific window transparency."""
        try:
            if self._platform == "macos":
                # macOS: Full alpha channel support
                self.window.attributes("-alpha", 0.3)
            elif self._platform == "windows":
                # Windows: Use alpha attribute (works on Windows 7+)
                try:
                    self.window.attributes("-alpha", 0.3)
                except tk.TclError:
                    # Fallback: transparent color key (older Windows)
                    self.window.attributes("-transparentcolor", "white")
            elif self._platform == "linux":
                # Linux: Alpha support varies by compositor
                # Works on most modern compositors (Picom, Mutter, KWin)
                try:
                    self.window.attributes("-alpha", 0.3)
                except tk.TclError:
                    # Transparency not available on this setup
                    self._transparency_supported = False
            else:
                self._transparency_supported = False
        except tk.TclError:
            self._transparency_supported = False

    def _get_primary_display_geometry(self) -> tuple:
        """
        Get the geometry of the primary display for multi-monitor support.

        Returns:
            Tuple of (x_offset, y_offset, width, height) for the primary display.
        """
        # Force window update to ensure geometry info is available
        self.window.update_idletasks()

        # Get virtual screen dimensions (all monitors combined)
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Try to get the root window position to determine primary display
        # On multi-monitor setups, winfo_screenwidth/height gives virtual size
        # We use winfo_vrootx/vrooty to get offset to the virtual root
        try:
            # Get virtual root offset (for multi-monitor)
            vroot_x = self.window.winfo_vrootx()
            vroot_y = self.window.winfo_vrooty()

            # If we can get real root geometry, use it
            # This handles cases where primary display isn't at (0,0)
            if vroot_x != 0 or vroot_y != 0:
                # We're in a virtual root situation
                return (vroot_x, vroot_y, screen_width, screen_height)
        except tk.TclError:
            pass

        # Default: assume primary display starts at (0, 0)
        # This is the most common case for single-monitor and
        # for primary monitor on left in multi-monitor setups
        return (0, 0, screen_width, screen_height)

    def _position_window(self) -> None:
        """
        Position window based on configured position.

        Handles multi-monitor setups by positioning on the primary display.
        """
        # Get primary display geometry
        display_x, display_y, screen_width, screen_height = self._get_primary_display_geometry()

        # Calculate x position based on horizontal alignment
        if "center" in self._position:
            x = display_x + (screen_width - self.width) // 2
        elif "right" in self._position:
            x = display_x + screen_width - self.width - self.EDGE_MARGIN
        else:  # left
            x = display_x + self.EDGE_MARGIN

        # Calculate y position based on vertical alignment
        if self._position.startswith("top"):
            y = display_y + self.EDGE_MARGIN
        else:  # bottom
            y = display_y + screen_height - self.height - self.EDGE_MARGIN

        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    @property
    def position(self) -> str:
        """Current position setting."""
        return self._position

    def set_position(self, position: str) -> None:
        """
        Change the indicator position.

        Args:
            position: One of: top-center, top-right, top-left, bottom-center,
                     bottom-right, bottom-left
        """
        if position not in VALID_POSITIONS:
            raise ValueError(f"Invalid position: {position}. Must be one of {VALID_POSITIONS}")
        self._position = position
        self._position_window()

    def _draw_state(self, opacity_override: Optional[float] = None) -> None:
        """
        Draw the current state on the canvas.

        Args:
            opacity_override: Optional opacity to use instead of state default
        """
        if self._current_state not in self.STATE_CONFIG:
            return

        # Special handling for recording state - use animated bars
        if self._current_state == "recording":
            self._draw_recording_bars()
            # Start animation if not already running
            if self._bar_animation_id is None:
                self._bar_animation_id = self.window.after(
                    self.BAR_ANIMATION_INTERVAL_MS,
                    self._animate_bars
                )
            # Set opacity
            if self._transparency_supported:
                try:
                    self.window.attributes("-alpha", 0.95)
                except tk.TclError:
                    pass
            return

        # Stop bar animation if running (for non-recording states)
        self._stop_bar_animation()

        bg_color, text_color, text, base_opacity = self.STATE_CONFIG[self._current_state]
        opacity = opacity_override if opacity_override is not None else base_opacity

        # Clear canvas
        self.canvas.delete("all")

        # Draw rounded rectangle background
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=bg_color,
            outline="",
            width=0
        )

        # Draw text if any
        if text:
            self.canvas.create_text(
                self.width // 2,
                self.height // 2,
                text=text,
                fill=text_color,
                font=("Arial", 10, "bold")
            )

        # Update opacity if transparency is supported
        if self._transparency_supported:
            try:
                self.window.attributes("-alpha", opacity)
            except tk.TclError:
                pass

    def _draw_recording_bars(self) -> None:
        """Draw animated audio visualizer bars for recording state."""
        self.canvas.delete("all")

        # Draw dark background
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=self.BAR_BG_COLOR,
            outline=""
        )

        # Calculate starting x position to center bars
        total_bar_width = (self.BAR_COUNT * self.BAR_WIDTH) + ((self.BAR_COUNT - 1) * self.BAR_GAP)
        start_x = (self.width - total_bar_width) // 2
        center_y = self.height // 2

        # Draw each bar
        for i, height in enumerate(self._bar_heights):
            x = start_x + i * (self.BAR_WIDTH + self.BAR_GAP)
            y1 = center_y - height // 2
            y2 = center_y + height // 2

            self.canvas.create_rectangle(
                x, y1, x + self.BAR_WIDTH, y2,
                fill=self.BAR_COLORS[i % len(self.BAR_COLORS)],
                outline=""
            )

    def _animate_bars(self) -> None:
        """Animate bar heights for recording visualization."""
        if self._current_state != "recording":
            return

        # Update each bar height with randomness
        for i in range(len(self._bar_heights)):
            delta = random.randint(2, 5) * self._bar_directions[i]
            self._bar_heights[i] += delta

            # Bounce at limits
            if self._bar_heights[i] >= self.BAR_MAX_HEIGHT:
                self._bar_heights[i] = self.BAR_MAX_HEIGHT
                self._bar_directions[i] = -1
            elif self._bar_heights[i] <= self.BAR_MIN_HEIGHT:
                self._bar_heights[i] = self.BAR_MIN_HEIGHT
                self._bar_directions[i] = 1

        # Redraw bars
        self._draw_recording_bars()

        # Schedule next frame
        self._bar_animation_id = self.window.after(
            self.BAR_ANIMATION_INTERVAL_MS,
            self._animate_bars
        )

    def _stop_bar_animation(self) -> None:
        """Stop the bar animation and reset state."""
        if self._bar_animation_id is not None:
            try:
                self.window.after_cancel(self._bar_animation_id)
            except tk.TclError:
                pass
            self._bar_animation_id = None

        # Reset bar heights
        self._bar_heights = [self.BAR_MIN_HEIGHT] * self.BAR_COUNT

    def _cancel_animations(self) -> None:
        """Cancel all pending animation callbacks."""
        # Cancel flash animations
        for after_id in self._flash_after_ids:
            try:
                self.window.after_cancel(after_id)
            except (tk.TclError, ValueError):
                pass
        self._flash_after_ids.clear()

        # Cancel bar animation
        self._stop_bar_animation()

    def _schedule_flash_animation(self) -> None:
        """
        Schedule a flash animation for success/error states.

        The animation pulses the opacity before fading to idle.
        """
        # Flash animation: pulse then fade
        # Step 0-2: Pulse bright (0.95)
        # Step 3-5: Fade out gradually
        fade_opacities = [0.95, 0.85, 0.95, 0.75, 0.55, 0.35]

        def animate_step(step: int) -> None:
            if step < len(fade_opacities):
                # Update opacity for fade effect
                if self._transparency_supported:
                    try:
                        self.window.attributes("-alpha", fade_opacities[step])
                    except tk.TclError:
                        pass
                # Schedule next step
                after_id = self.window.after(
                    self.FLASH_INTERVAL_MS,
                    lambda: animate_step(step + 1)
                )
                self._flash_after_ids.append(after_id)
            else:
                # Animation complete, return to idle
                self.set_state("idle")

        # Start animation after a brief pause showing the state
        after_id = self.window.after(
            self.FLASH_DURATION_MS - (len(fade_opacities) * self.FLASH_INTERVAL_MS),
            lambda: animate_step(0)
        )
        self._flash_after_ids.append(after_id)

    def set_state(self, state: str) -> None:
        """
        Set the indicator state.

        Args:
            state: One of "idle", "recording", "transcribing", "success", "error"
        """
        if state not in self.STATE_CONFIG:
            raise ValueError(f"Invalid state: {state}. Must be one of {list(self.STATE_CONFIG.keys())}")

        # Cancel any pending animations
        self._cancel_animations()

        self._current_state = state
        self._draw_state()

        # Show window if not idle, hide if idle
        if state == "idle":
            self.hide()
        else:
            self.show()

        # Flash animation for success/error states
        if state in ("success", "error"):
            self._schedule_flash_animation()

    def show(self) -> None:
        """Show the indicator window without stealing focus."""
        # Re-apply focus prevention before showing (settings may reset after withdraw)
        if self._platform == "macos":
            self._setup_macos_focus_prevention()

        self.window.deiconify()

        # Don't call lift() on macOS as it can steal focus from the active text field
        # The -topmost attribute ensures the window stays on top without needing lift()
        if self._platform != "macos":
            self.window.lift()

    def hide(self) -> None:
        """Hide the indicator window."""
        self.window.withdraw()

    @property
    def transparency_supported(self) -> bool:
        """Whether window transparency is supported on this platform."""
        return self._transparency_supported

    @property
    def platform(self) -> str:
        """The detected platform (macos, windows, linux, unknown)."""
        return self._platform

    def destroy(self) -> None:
        """Destroy the indicator window."""
        self._cancel_animations()
        try:
            self.window.destroy()
        except tk.TclError:
            pass
