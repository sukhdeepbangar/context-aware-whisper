"""
Platform Abstraction Layer

This module provides platform detection and factory functions for creating
platform-specific components (hotkey detection, text output, etc.).

Supported platforms:
- macOS: Fn/Globe key detection via CGEvent tap, AppleScript output
- Windows: Ctrl+Shift+Space via pynput
- Linux: Ctrl+Shift+Space via pynput
"""

import logging
import sys
from typing import Callable

from handfree.platform.base import HotkeyDetectorBase, OutputHandlerBase
from handfree.exceptions import PlatformNotSupportedError


logger = logging.getLogger(__name__)


# Platform-specific error messages for better troubleshooting
PLATFORM_ERROR_MESSAGES = {
    "macos": {
        "hotkey": (
            "macOS hotkey detection requires Accessibility permission.\n"
            "Grant permission in: System Settings > Privacy & Security > Accessibility\n"
            "Then restart HandFree."
        ),
        "output": (
            "macOS text output requires Accessibility permission.\n"
            "Grant permission in: System Settings > Privacy & Security > Accessibility\n"
            "Then restart HandFree."
        ),
        "dependency": (
            "macOS requires pyobjc frameworks. Install with:\n"
            "  pip install 'handfree[macos]'"
        ),
    },
    "windows": {
        "hotkey": (
            "Windows hotkey detection requires pynput.\n"
            "Some antivirus software may block keyboard monitoring.\n"
            "Try running as Administrator if issues persist."
        ),
        "output": (
            "Windows text output requires pynput.\n"
            "Install with: pip install pynput"
        ),
        "dependency": (
            "Windows requires pynput. Install with:\n"
            "  pip install pynput"
        ),
    },
    "linux": {
        "hotkey": (
            "Linux hotkey detection requires X11 or proper Wayland permissions.\n"
            "On X11: Ensure DISPLAY environment variable is set.\n"
            "On Wayland: Some features may require additional configuration.\n"
            "You may need to run with sudo or add your user to the 'input' group."
        ),
        "output": (
            "Linux text output requires xdotool or pynput.\n"
            "Install with: sudo apt install xdotool (Debian/Ubuntu)\n"
            "             or: pip install pynput"
        ),
        "dependency": (
            "Linux requires pynput. Install with:\n"
            "  pip install pynput\n"
            "For xdotool fallback: sudo apt install xdotool"
        ),
    },
    "unknown": {
        "hotkey": "Your platform is not supported for hotkey detection.",
        "output": "Your platform is not supported for text output.",
        "dependency": "Your platform is not supported.",
    },
}


def get_platform() -> str:
    """
    Detect the current platform.

    Returns:
        'macos', 'windows', 'linux', or 'unknown'
    """
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    elif sys.platform.startswith("linux"):
        return "linux"
    else:
        return "unknown"


def get_platform_error_message(platform: str, error_type: str) -> str:
    """
    Get a helpful error message for platform-specific issues.

    Args:
        platform: The platform name (macos, windows, linux, unknown)
        error_type: The type of error (hotkey, output, dependency)

    Returns:
        A helpful error message string
    """
    messages = PLATFORM_ERROR_MESSAGES.get(platform, PLATFORM_ERROR_MESSAGES["unknown"])
    return messages.get(error_type, f"Unknown error type: {error_type}")


def create_hotkey_detector(
    on_start: Callable[[], None],
    on_stop: Callable[[], None]
) -> HotkeyDetectorBase:
    """
    Create a platform-appropriate hotkey detector.

    Args:
        on_start: Called when hotkey is pressed (start recording)
        on_stop: Called when hotkey is released (stop recording)

    Returns:
        Platform-specific HotkeyDetector instance

    Raises:
        PlatformNotSupportedError: If current platform is not supported
        ImportError: If required dependencies are not installed
    """
    platform = get_platform()
    logger.debug(f"Creating hotkey detector for platform: {platform}")

    if platform == "macos":
        try:
            from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector
            detector = MacOSHotkeyDetector(on_start, on_stop)
            logger.debug("Created MacOSHotkeyDetector")
            return detector
        except ImportError as e:
            logger.error(f"Failed to import macOS hotkey detector: {e}")
            raise PlatformNotSupportedError(
                f"macOS hotkey detection unavailable: {e}\n\n"
                f"{get_platform_error_message('macos', 'dependency')}"
            ) from e
    elif platform == "windows":
        try:
            from handfree.platform.windows.hotkey_detector import WindowsHotkeyDetector
            detector = WindowsHotkeyDetector(on_start, on_stop)
            logger.debug("Created WindowsHotkeyDetector")
            return detector
        except ImportError as e:
            logger.error(f"Failed to import Windows hotkey detector: {e}")
            raise PlatformNotSupportedError(
                f"Windows hotkey detection unavailable: {e}\n\n"
                f"{get_platform_error_message('windows', 'dependency')}"
            ) from e
    elif platform == "linux":
        try:
            from handfree.platform.linux.hotkey_detector import LinuxHotkeyDetector
            detector = LinuxHotkeyDetector(on_start, on_stop)
            logger.debug("Created LinuxHotkeyDetector")
            return detector
        except ImportError as e:
            logger.error(f"Failed to import Linux hotkey detector: {e}")
            raise PlatformNotSupportedError(
                f"Linux hotkey detection unavailable: {e}\n\n"
                f"{get_platform_error_message('linux', 'dependency')}"
            ) from e
    else:
        logger.error(f"Unsupported platform: {platform}")
        raise PlatformNotSupportedError(
            f"Platform '{platform}' is not supported.\n"
            "Supported platforms: macOS, Windows, Linux"
        )


def create_output_handler(type_delay: float = 0.0) -> OutputHandlerBase:
    """
    Create a platform-appropriate output handler.

    Args:
        type_delay: Delay between keystrokes in seconds (0 = fastest)

    Returns:
        Platform-specific OutputHandler instance

    Raises:
        PlatformNotSupportedError: If current platform is not supported
        ImportError: If required dependencies are not installed
    """
    platform = get_platform()
    logger.debug(f"Creating output handler for platform: {platform}")

    if platform == "macos":
        try:
            from handfree.platform.macos.output_handler import MacOSOutputHandler
            handler = MacOSOutputHandler(type_delay)
            logger.debug("Created MacOSOutputHandler")
            return handler
        except ImportError as e:
            logger.error(f"Failed to import macOS output handler: {e}")
            raise PlatformNotSupportedError(
                f"macOS output handler unavailable: {e}\n\n"
                f"{get_platform_error_message('macos', 'dependency')}"
            ) from e
    elif platform == "windows":
        try:
            from handfree.platform.windows.output_handler import WindowsOutputHandler
            handler = WindowsOutputHandler(type_delay)
            logger.debug("Created WindowsOutputHandler")
            return handler
        except ImportError as e:
            logger.error(f"Failed to import Windows output handler: {e}")
            raise PlatformNotSupportedError(
                f"Windows output handler unavailable: {e}\n\n"
                f"{get_platform_error_message('windows', 'dependency')}"
            ) from e
    elif platform == "linux":
        try:
            from handfree.platform.linux.output_handler import LinuxOutputHandler
            handler = LinuxOutputHandler(type_delay)
            logger.debug("Created LinuxOutputHandler")
            return handler
        except ImportError as e:
            logger.error(f"Failed to import Linux output handler: {e}")
            raise PlatformNotSupportedError(
                f"Linux output handler unavailable: {e}\n\n"
                f"{get_platform_error_message('linux', 'dependency')}"
            ) from e
    else:
        logger.error(f"Unsupported platform: {platform}")
        raise PlatformNotSupportedError(
            f"Platform '{platform}' is not supported.\n"
            "Supported platforms: macOS, Windows, Linux"
        )


def is_mute_detector_available() -> bool:
    """
    Check if AirPods mute detector is available on this platform.

    The mute detector uses macOS AVFAudio framework and is only
    available on macOS.

    Returns:
        True only on macOS
    """
    return get_platform() == "macos"


def get_default_hotkey_description() -> str:
    """
    Get the default hotkey description for the current platform.

    Returns:
        Human-readable hotkey description
    """
    platform = get_platform()

    if platform == "macos":
        return "Fn/Globe key"
    elif platform in ("windows", "linux"):
        return "Ctrl+Shift+Space"
    else:
        return "Unknown"


__all__ = [
    "get_platform",
    "get_platform_error_message",
    "create_hotkey_detector",
    "create_output_handler",
    "is_mute_detector_available",
    "get_default_hotkey_description",
    "HotkeyDetectorBase",
    "OutputHandlerBase",
    "PLATFORM_ERROR_MESSAGES",
]
