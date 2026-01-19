"""
History Store Module

Provides JSONL-based persistent storage for transcription history.
Simple append-only file storage for single-user use.
"""

import json
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from context_aware_whisper.exceptions import StorageError


@dataclass
class TranscriptionRecord:
    """A single transcription history entry."""
    id: int
    text: str
    timestamp: datetime
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class HistoryStore:
    """
    JSONL-based storage for transcription history.

    Simple append-only file storage. Each line is a JSON object.
    """

    DEFAULT_PATH = Path.home() / ".context-aware-whisper" / "history.jsonl"
    MAX_ENTRIES = 1000

    def __init__(self, path: Optional[Path] = None):
        """
        Initialize history store.

        Args:
            path: Path to JSONL file. Defaults to ~/.context-aware-whisper/history.jsonl
        """
        self.path = path or self.DEFAULT_PATH
        self._lock = threading.Lock()
        self._next_id = 1
        self._init_storage()

    def _init_storage(self) -> None:
        """Initialize storage file and load next ID."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            if self.path.exists():
                # Find the highest ID to continue from
                entries = self._read_all()
                if entries:
                    self._next_id = max(e["id"] for e in entries) + 1
            else:
                self.path.touch()
        except OSError as e:
            raise StorageError(f"Failed to initialize storage: {e}") from e

    def _read_all(self) -> List[dict]:
        """Read all entries from file."""
        entries = []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except (OSError, json.JSONDecodeError) as e:
            raise StorageError(f"Failed to read history: {e}") from e
        return entries

    def add(
        self,
        text: str,
        duration: Optional[float] = None,
        language: Optional[str] = None
    ) -> int:
        """
        Add a transcription to history.

        Args:
            text: The transcribed text
            duration: Recording duration in seconds
            language: Language code (e.g., "en", "es")

        Returns:
            The ID of the inserted record
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        with self._lock:
            entry = {
                "id": self._next_id,
                "text": text.strip(),
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "language": language
            }

            try:
                with open(self.path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')

                record_id = self._next_id
                self._next_id += 1

                # Cleanup if needed
                self._cleanup_if_needed()

                return record_id
            except OSError as e:
                raise StorageError(f"Failed to save transcription: {e}") from e

    def _cleanup_if_needed(self) -> None:
        """Remove oldest entries if over MAX_ENTRIES."""
        try:
            entries = self._read_all()
            if len(entries) > self.MAX_ENTRIES:
                # Keep only the newest entries
                entries = entries[-self.MAX_ENTRIES:]
                with open(self.path, 'w', encoding='utf-8') as f:
                    for entry in entries:
                        f.write(json.dumps(entry) + '\n')
        except (OSError, json.JSONDecodeError):
            pass  # Non-critical, skip cleanup

    def get_recent(self, limit: int = 50) -> List[TranscriptionRecord]:
        """
        Get most recent transcriptions.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of TranscriptionRecord objects, newest first
        """
        with self._lock:
            entries = self._read_all()
            # Newest first
            entries = entries[-limit:][::-1]
            return [self._to_record(e) for e in entries]

    def search(self, query: str, limit: int = 50) -> List[TranscriptionRecord]:
        """
        Search transcriptions by text content.

        Args:
            query: Search query (case-insensitive substring match)
            limit: Maximum number of results

        Returns:
            List of matching TranscriptionRecord objects, newest first
        """
        if not query or not query.strip():
            return []

        query = query.strip().lower()

        with self._lock:
            entries = self._read_all()
            matches = [e for e in entries if query in e["text"].lower()]
            # Newest first, limited
            matches = matches[-limit:][::-1]
            return [self._to_record(e) for e in matches]

    def get_by_id(self, record_id: int) -> Optional[TranscriptionRecord]:
        """Get a specific transcription by ID."""
        with self._lock:
            entries = self._read_all()
            for e in entries:
                if e["id"] == record_id:
                    return self._to_record(e)
            return None

    def delete(self, record_id: int) -> bool:
        """Delete a transcription by ID."""
        with self._lock:
            entries = self._read_all()
            original_len = len(entries)
            entries = [e for e in entries if e["id"] != record_id]

            if len(entries) == original_len:
                return False

            try:
                with open(self.path, 'w', encoding='utf-8') as f:
                    for entry in entries:
                        f.write(json.dumps(entry) + '\n')
                return True
            except OSError:
                return False

    def count(self) -> int:
        """Get total number of transcriptions stored."""
        with self._lock:
            return len(self._read_all())

    def clear(self) -> int:
        """Clear all transcriptions. Returns count deleted."""
        with self._lock:
            count = len(self._read_all())
            try:
                with open(self.path, 'w', encoding='utf-8') as f:
                    pass  # Truncate file
                return count
            except OSError:
                return 0

    def _to_record(self, entry: dict) -> TranscriptionRecord:
        """Convert dict entry to TranscriptionRecord."""
        return TranscriptionRecord(
            id=entry["id"],
            text=entry["text"],
            timestamp=datetime.fromisoformat(entry["timestamp"]),
            duration_seconds=entry.get("duration_seconds"),
            language=entry.get("language")
        )
