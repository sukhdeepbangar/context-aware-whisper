"""
Platform Abstraction Layer

This module provides platform detection and factory functions for creating
platform-specific components (hotkey detection, text output, etc.).

Supported platforms:
- macOS: Fn/Globe key detection via CGEvent tap, AppleScript output
- Windows: Ctrl+Shift+Space via pynput (planned)
- Linux: Ctrl+Shift+Space via pynput (planned)
"""

import sys
from typing import Callable

from handfree.platform.base import HotkeyDetectorBase, OutputHandlerBase
from handfree.exceptions import PlatformNotSupportedError


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
    """
    platform = get_platform()

    if platform == "macos":
        from handfree.platform.macos.hotkey_detector import MacOSHotkeyDetector
        return MacOSHotkeyDetector(on_start, on_stop)
    elif platform == "windows":
        from handfree.platform.windows.hotkey_detector import WindowsHotkeyDetector
        return WindowsHotkeyDetector(on_start, on_stop)
    elif platform == "linux":
        from handfree.platform.linux.hotkey_detector import LinuxHotkeyDetector
        return LinuxHotkeyDetector(on_start, on_stop)
    else:
        raise PlatformNotSupportedError(
            f"Platform '{platform}' is not supported. "
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
    """
    platform = get_platform()

    if platform == "macos":
        from handfree.platform.macos.output_handler import MacOSOutputHandler
        return MacOSOutputHandler(type_delay)
    elif platform == "windows":
        from handfree.platform.windows.output_handler import WindowsOutputHandler
        return WindowsOutputHandler(type_delay)
    elif platform == "linux":
        from handfree.platform.linux.output_handler import LinuxOutputHandler
        return LinuxOutputHandler(type_delay)
    else:
        raise PlatformNotSupportedError(
            f"Platform '{platform}' is not supported. "
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
    "create_hotkey_detector",
    "create_output_handler",
    "is_mute_detector_available",
    "get_default_hotkey_description",
    "HotkeyDetectorBase",
    "OutputHandlerBase",
]
