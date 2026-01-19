"""
HandFree Storage Module

Provides persistent storage for transcription history.
"""

from context_aware_whisper.storage.history_store import HistoryStore, TranscriptionRecord

__all__ = ["HistoryStore", "TranscriptionRecord"]
