"""
Custom Exceptions for CAW application.

This module defines the exception hierarchy used throughout the application.
"""


class CAWError(Exception):
    """Base exception for all CAW errors."""
    pass


class ConfigurationError(CAWError):
    """Error in application configuration."""
    pass


class MuteDetectionError(CAWError):
    """Error detecting input mute state."""
    pass


class AudioRecordingError(CAWError):
    """Error recording audio from microphone."""
    pass


class TranscriptionError(CAWError):
    """Error transcribing audio via API."""
    pass


class LocalTranscriptionError(CAWError):
    """Error transcribing audio locally via whisper.cpp."""
    pass


class OutputError(CAWError):
    """Error outputting text to clipboard or active application."""
    pass


class PermissionError(CAWError):
    """Error related to missing system permissions."""
    pass


class StorageError(CAWError):
    """Error related to data storage operations."""
    pass


class PlatformNotSupportedError(CAWError):
    """Error when running on an unsupported platform."""
    pass


class UIInitializationError(CAWError):
    """Error when UI fails to initialize."""
    pass


class HotkeyDetectorError(CAWError):
    """Error when hotkey detector fails to initialize or start."""
    pass


class OutputHandlerError(CAWError):
    """Error when output handler fails to initialize."""
    pass


class TextCleanupError(CAWError):
    """Error cleaning transcribed text."""
    pass
