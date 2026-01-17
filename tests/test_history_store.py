"""
Tests for HistoryStore - Transcription History Storage

Tests the JSONL-based storage for transcription history.
"""

import pytest
import json
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

from handfree.storage.history_store import HistoryStore, TranscriptionRecord
from handfree.exceptions import StorageError


@pytest.fixture
def temp_file():
    """Create a temporary JSONL file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    yield path
    try:
        path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def history_store(temp_file):
    """Create a HistoryStore instance with a temporary file."""
    return HistoryStore(path=temp_file)


class TestHistoryStoreInit:
    """Tests for HistoryStore initialization."""

    def test_creates_file(self, temp_file):
        """Test that file is created."""
        temp_file.unlink()  # Remove it first
        store = HistoryStore(path=temp_file)
        assert temp_file.exists()

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directory is created if it doesn't exist."""
        path = tmp_path / "subdir" / "test.jsonl"
        store = HistoryStore(path=path)
        assert path.exists()

    def test_has_max_entries_constant(self):
        """Test that MAX_ENTRIES constant is defined."""
        assert hasattr(HistoryStore, "MAX_ENTRIES")
        assert HistoryStore.MAX_ENTRIES == 1000

    def test_has_default_path(self):
        """Test that DEFAULT_PATH is defined."""
        assert hasattr(HistoryStore, "DEFAULT_PATH")
        assert HistoryStore.DEFAULT_PATH == Path.home() / ".handfree" / "history.jsonl"

    def test_loads_existing_entries(self, temp_file):
        """Test that existing entries are loaded on init."""
        # Write some entries first
        with open(temp_file, 'w') as f:
            f.write('{"id": 1, "text": "First", "timestamp": "2024-01-01T00:00:00"}\n')
            f.write('{"id": 5, "text": "Fifth", "timestamp": "2024-01-01T00:00:00"}\n')

        store = HistoryStore(path=temp_file)
        # Next ID should be 6
        new_id = store.add("New entry")
        assert new_id == 6


class TestHistoryStoreAdd:
    """Tests for HistoryStore.add() method."""

    def test_add_returns_id(self, history_store):
        """Test that add() returns record ID."""
        record_id = history_store.add("Hello world")
        assert isinstance(record_id, int)
        assert record_id > 0

    def test_add_with_all_fields(self, history_store):
        """Test add() with all optional fields."""
        record_id = history_store.add(
            text="Test transcription",
            duration=5.5,
            language="en"
        )
        assert record_id > 0

        record = history_store.get_by_id(record_id)
        assert record.text == "Test transcription"
        assert record.duration_seconds == 5.5
        assert record.language == "en"

    def test_add_strips_whitespace(self, history_store):
        """Test that add() strips whitespace from text."""
        record_id = history_store.add("  Hello world  ")
        record = history_store.get_by_id(record_id)
        assert record.text == "Hello world"

    def test_add_empty_text_raises_error(self, history_store):
        """Test that add() raises ValueError for empty text."""
        with pytest.raises(ValueError):
            history_store.add("")

    def test_add_whitespace_only_raises_error(self, history_store):
        """Test that add() raises ValueError for whitespace-only text."""
        with pytest.raises(ValueError):
            history_store.add("   ")

    def test_add_increments_ids(self, history_store):
        """Test that IDs are incremented."""
        id1 = history_store.add("First")
        id2 = history_store.add("Second")
        id3 = history_store.add("Third")

        assert id2 > id1
        assert id3 > id2

    def test_add_sets_timestamp(self, history_store):
        """Test that add() sets timestamp automatically."""
        before = datetime.now()
        record_id = history_store.add("Test")
        after = datetime.now()

        record = history_store.get_by_id(record_id)
        assert before <= record.timestamp <= after

    def test_add_writes_to_file(self, history_store, temp_file):
        """Test that add() writes to the JSONL file."""
        history_store.add("Test entry")

        with open(temp_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["text"] == "Test entry"


class TestHistoryStoreGetRecent:
    """Tests for HistoryStore.get_recent() method."""

    def test_get_recent_empty_file(self, history_store):
        """Test get_recent() on empty file."""
        records = history_store.get_recent()
        assert records == []

    def test_get_recent_returns_list(self, history_store):
        """Test that get_recent() returns a list."""
        history_store.add("Test")
        records = history_store.get_recent()
        assert isinstance(records, list)

    def test_get_recent_returns_transcription_records(self, history_store):
        """Test that get_recent() returns TranscriptionRecord objects."""
        history_store.add("Test")
        records = history_store.get_recent()
        assert len(records) == 1
        assert isinstance(records[0], TranscriptionRecord)

    def test_get_recent_newest_first(self, history_store):
        """Test that get_recent() returns newest first."""
        history_store.add("First")
        history_store.add("Second")
        history_store.add("Third")

        records = history_store.get_recent()
        assert len(records) == 3
        assert records[0].text == "Third"
        assert records[1].text == "Second"
        assert records[2].text == "First"

    def test_get_recent_respects_limit(self, history_store):
        """Test that get_recent() respects limit parameter."""
        for i in range(10):
            history_store.add(f"Entry {i}")

        records = history_store.get_recent(limit=5)
        assert len(records) == 5

    def test_get_recent_default_limit(self, history_store):
        """Test that default limit is 50."""
        for i in range(60):
            history_store.add(f"Entry {i}")

        records = history_store.get_recent()
        assert len(records) == 50


class TestHistoryStoreSearch:
    """Tests for HistoryStore.search() method."""

    def test_search_empty_query_returns_empty(self, history_store):
        """Test that search with empty query returns empty list."""
        history_store.add("Test entry")
        records = history_store.search("")
        assert records == []

    def test_search_whitespace_query_returns_empty(self, history_store):
        """Test that search with whitespace query returns empty list."""
        history_store.add("Test entry")
        records = history_store.search("   ")
        assert records == []

    def test_search_finds_matches(self, history_store):
        """Test that search finds matching entries."""
        history_store.add("Hello world")
        history_store.add("Goodbye world")
        history_store.add("Nothing here")

        records = history_store.search("world")
        assert len(records) == 2

    def test_search_case_insensitive(self, history_store):
        """Test that search is case-insensitive."""
        history_store.add("Hello WORLD")
        history_store.add("hello world")

        records = history_store.search("world")
        assert len(records) == 2

    def test_search_partial_match(self, history_store):
        """Test that search matches partial strings."""
        history_store.add("transcription test")

        records = history_store.search("script")
        assert len(records) == 1

    def test_search_respects_limit(self, history_store):
        """Test that search respects limit parameter."""
        for i in range(10):
            history_store.add(f"Test entry {i}")

        records = history_store.search("Test", limit=3)
        assert len(records) == 3

    def test_search_newest_first(self, history_store):
        """Test that search results are newest first."""
        history_store.add("Apple first")
        history_store.add("Apple second")
        history_store.add("Apple third")

        records = history_store.search("Apple")
        assert records[0].text == "Apple third"
        assert records[2].text == "Apple first"


class TestHistoryStoreGetById:
    """Tests for HistoryStore.get_by_id() method."""

    def test_get_by_id_existing(self, history_store):
        """Test get_by_id() for existing record."""
        record_id = history_store.add("Test entry")
        record = history_store.get_by_id(record_id)

        assert record is not None
        assert record.id == record_id
        assert record.text == "Test entry"

    def test_get_by_id_nonexistent(self, history_store):
        """Test get_by_id() for non-existent record."""
        record = history_store.get_by_id(99999)
        assert record is None

    def test_get_by_id_returns_transcription_record(self, history_store):
        """Test that get_by_id() returns TranscriptionRecord."""
        record_id = history_store.add("Test", duration=2.5, language="en")
        record = history_store.get_by_id(record_id)

        assert isinstance(record, TranscriptionRecord)
        assert record.duration_seconds == 2.5
        assert record.language == "en"


class TestHistoryStoreDelete:
    """Tests for HistoryStore.delete() method."""

    def test_delete_existing_record(self, history_store):
        """Test deleting existing record."""
        record_id = history_store.add("Test")
        result = history_store.delete(record_id)

        assert result is True
        assert history_store.get_by_id(record_id) is None

    def test_delete_nonexistent_record(self, history_store):
        """Test deleting non-existent record."""
        result = history_store.delete(99999)
        assert result is False

    def test_delete_decrements_count(self, history_store):
        """Test that delete decrements count."""
        history_store.add("First")
        record_id = history_store.add("Second")
        history_store.add("Third")

        assert history_store.count() == 3
        history_store.delete(record_id)
        assert history_store.count() == 2


class TestHistoryStoreCount:
    """Tests for HistoryStore.count() method."""

    def test_count_empty(self, history_store):
        """Test count on empty file."""
        assert history_store.count() == 0

    def test_count_after_adds(self, history_store):
        """Test count after adding entries."""
        history_store.add("One")
        history_store.add("Two")
        history_store.add("Three")

        assert history_store.count() == 3


class TestHistoryStoreClear:
    """Tests for HistoryStore.clear() method."""

    def test_clear_returns_count(self, history_store):
        """Test that clear returns number of deleted records."""
        history_store.add("One")
        history_store.add("Two")
        history_store.add("Three")

        deleted = history_store.clear()
        assert deleted == 3

    def test_clear_empties_file(self, history_store):
        """Test that clear empties the file."""
        history_store.add("One")
        history_store.add("Two")
        history_store.clear()

        assert history_store.count() == 0
        assert history_store.get_recent() == []


class TestHistoryStoreCleanup:
    """Tests for automatic cleanup when MAX_ENTRIES is exceeded."""

    def test_cleanup_removes_oldest(self, temp_file):
        """Test that oldest entries are removed when limit exceeded."""
        store = HistoryStore(path=temp_file)
        original_max = HistoryStore.MAX_ENTRIES
        HistoryStore.MAX_ENTRIES = 5

        try:
            for i in range(6):
                store.add(f"Entry {i}")

            assert store.count() == 5

            # Verify oldest (Entry 0) was removed
            records = store.get_recent()
            texts = [r.text for r in records]
            assert "Entry 0" not in texts
            assert "Entry 5" in texts
        finally:
            HistoryStore.MAX_ENTRIES = original_max


class TestHistoryStoreThreadSafety:
    """Tests for thread safety of HistoryStore."""

    def test_concurrent_adds(self, history_store):
        """Test that concurrent adds don't cause data corruption."""
        results = []
        errors = []

        def add_entries(prefix, count):
            try:
                for i in range(count):
                    history_store.add(f"{prefix} {i}")
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_entries, args=("Thread1", 10)),
            threading.Thread(target=add_entries, args=("Thread2", 10)),
            threading.Thread(target=add_entries, args=("Thread3", 10)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3
        assert history_store.count() == 30


class TestTranscriptionRecord:
    """Tests for TranscriptionRecord dataclass."""

    def test_record_has_required_fields(self):
        """Test that TranscriptionRecord has all required fields."""
        record = TranscriptionRecord(
            id=1,
            text="Test",
            timestamp=datetime.now()
        )
        assert hasattr(record, "id")
        assert hasattr(record, "text")
        assert hasattr(record, "timestamp")
        assert hasattr(record, "duration_seconds")
        assert hasattr(record, "language")

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        record = TranscriptionRecord(
            id=1,
            text="Test",
            timestamp=datetime.now()
        )
        assert record.duration_seconds is None
        assert record.language is None


class TestStorageError:
    """Tests for StorageError exception."""

    def test_storage_error_exists(self):
        """Test that StorageError is defined."""
        from handfree.exceptions import StorageError
        assert StorageError is not None

    def test_storage_error_is_handfree_error(self):
        """Test that StorageError inherits from HandFreeError."""
        from handfree.exceptions import StorageError, HandFreeError
        assert issubclass(StorageError, HandFreeError)
