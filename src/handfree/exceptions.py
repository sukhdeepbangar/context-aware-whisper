"""
Custom Exceptions for HandFree application.

This module defines the exception hierarchy used throughout the application.
"""


class HandFreeError(Exception):
    """Base exception for all HandFree errors."""
    pass


class ConfigurationError(HandFreeError):
    """Error in application configuration."""
    pass


class MuteDetectionError(HandFreeError):
    """Error detecting input mute state."""
    pass


class AudioRecordingError(HandFreeError):
    """Error recording audio from microphone."""
    pass


class TranscriptionError(HandFreeError):
    """Error transcribing audio via API."""
    pass


class LocalTranscriptionError(HandFreeError):
    """Error transcribing audio locally via whisper.cpp."""
    pass


class OutputError(HandFreeError):
    """Error outputting text to clipboard or active application."""
    pass


class PermissionError(HandFreeError):
    """Error related to missing system permissions."""
    pass


class StorageError(HandFreeError):
    """Error related to data storage operations."""
    pass


class PlatformNotSupportedError(HandFreeError):
    """Error when running on an unsupported platform."""
    pass


class UIInitializationError(HandFreeError):
    """Error when UI fails to initialize."""
    pass


class HotkeyDetectorError(HandFreeError):
    """Error when hotkey detector fails to initialize or start."""
    pass


class OutputHandlerError(HandFreeError):
    """Error when output handler fails to initialize."""
    pass


class TextCleanupError(HandFreeError):
    """Error cleaning transcribed text."""
    pass
