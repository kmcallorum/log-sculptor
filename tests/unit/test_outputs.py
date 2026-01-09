"""Tests for output writers."""
import pytest
import sqlite3
from pathlib import Path

from log_sculptor.core.patterns import PatternSet, learn_patterns, parse_logs, ParsedRecord
from log_sculptor.outputs.sqlite import write_sqlite
from log_sculptor.outputs.jsonl import write_jsonl
from log_sculptor.testing.generators import write_sample_logs


@pytest.fixture
def sample_records(tmp_path):
    """Generate sample parsed records."""
    log_file = tmp_path / "test.log"
    write_sample_logs(log_file, generator="apache", count=20, seed=42)

    patterns = learn_patterns(log_file)
    records = list(parse_logs(log_file, patterns))
    return records, patterns


class TestSQLiteOutput:
    """Tests for SQLite output writer."""

    def test_write_sqlite_basic(self, sample_records, tmp_path):
        """Test basic SQLite write."""
        records, patterns = sample_records
        output = tmp_path / "output.db"

        count = write_sqlite(records, output, patterns=patterns)

        assert count == len(records)
        assert output.exists()

        # Verify database structure
        conn = sqlite3.connect(output)
        cursor = conn.cursor()

        # Check patterns table exists
        cursor.execute("SELECT COUNT(*) FROM patterns")
        pattern_count = cursor.fetchone()[0]
        assert pattern_count > 0

        # Check logs table exists
        cursor.execute("SELECT COUNT(*) FROM logs")
        log_count = cursor.fetchone()[0]
        assert log_count == len(records)

        conn.close()

    def test_write_sqlite_without_patterns(self, sample_records, tmp_path):
        """Test SQLite write without pattern metadata."""
        records, _ = sample_records
        output = tmp_path / "output.db"

        count = write_sqlite(records, output, patterns=None)

        assert count == len(records)

        conn = sqlite3.connect(output)
        cursor = conn.cursor()

        # Patterns table should not exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patterns'")
        assert cursor.fetchone() is None

        conn.close()

    def test_write_sqlite_include_raw(self, sample_records, tmp_path):
        """Test SQLite write with raw line included."""
        records, patterns = sample_records
        output = tmp_path / "output.db"

        write_sqlite(records, output, patterns=patterns, include_raw=True)

        conn = sqlite3.connect(output)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(logs)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "raw" in columns
        conn.close()

    def test_write_sqlite_no_raw(self, sample_records, tmp_path):
        """Test SQLite write without raw line."""
        records, patterns = sample_records
        output = tmp_path / "output.db"

        write_sqlite(records, output, patterns=patterns, include_raw=False)

        conn = sqlite3.connect(output)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(logs)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "raw" not in columns
        conn.close()

    def test_write_sqlite_overwrites_existing(self, sample_records, tmp_path):
        """Test that SQLite write overwrites existing file."""
        records, patterns = sample_records
        output = tmp_path / "output.db"

        # Write once
        write_sqlite(records[:5], output, patterns=patterns)

        # Write again with more records
        write_sqlite(records, output, patterns=patterns)

        conn = sqlite3.connect(output)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM logs")
        count = cursor.fetchone()[0]
        assert count == len(records)  # Should have all records, not just 5
        conn.close()


class TestJSONLOutput:
    """Tests for JSONL output writer."""

    def test_write_jsonl_basic(self, sample_records, tmp_path):
        """Test basic JSONL write."""
        records, _ = sample_records
        output = tmp_path / "output.jsonl"

        count = write_jsonl(records, output)

        assert count == len(records)
        assert output.exists()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == len(records)

    def test_write_jsonl_include_raw(self, sample_records, tmp_path):
        """Test JSONL write with raw line."""
        records, _ = sample_records
        output = tmp_path / "output.jsonl"

        write_jsonl(records, output, include_raw=True)

        import json
        lines = output.read_text().strip().split("\n")
        first_record = json.loads(lines[0])
        assert "_raw" in first_record

    def test_write_jsonl_exclude_unmatched(self, sample_records, tmp_path):
        """Test JSONL write excluding unmatched records."""
        records, _ = sample_records
        output = tmp_path / "output.jsonl"

        matched_count = sum(1 for r in records if r.matched)
        count = write_jsonl(records, output, include_unmatched=False)

        assert count == matched_count

    def test_write_jsonl_include_typed(self, sample_records, tmp_path):
        """Test JSONL write with typed fields."""
        records, _ = sample_records
        output = tmp_path / "output.jsonl"

        write_jsonl(records, output, include_typed=True)

        import json
        lines = output.read_text().strip().split("\n")
        for line in lines:
            record = json.loads(line)
            if record.get("matched"):
                # Typed fields might be present
                pass  # Just verify it doesn't error

    def test_write_jsonl_to_file_object(self, sample_records, tmp_path):
        """Test JSONL write to file object."""
        records, _ = sample_records
        output = tmp_path / "output.jsonl"

        with open(output, "w") as f:
            count = write_jsonl(records, f)

        assert count == len(records)
        assert output.exists()


class TestOutputFieldHandling:
    """Tests for field handling in outputs."""

    def test_special_characters_in_fields(self, tmp_path):
        """Test handling of special characters in field names."""
        # Create a simple record with special field name
        record = ParsedRecord(
            line_number=1,
            raw="test line",
            fields={"field-with-dash": "value", "field.with.dot": "value2"},
            pattern_id="test",
            matched=True,
            confidence=1.0,
        )

        output = tmp_path / "output.db"
        write_sqlite([record], output, include_raw=True)

        conn = sqlite3.connect(output)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs")
        row = cursor.fetchone()
        assert row is not None
        conn.close()


class TestJSONLEdgeCases:
    """Edge cases for JSONL output."""

    def test_write_jsonl_skip_unmatched(self, tmp_path):
        """Test that unmatched records are skipped when include_unmatched=False."""
        records = [
            ParsedRecord(line_number=1, raw="matched", fields={"f": "v"}, pattern_id="p1", matched=True, confidence=1.0),
            ParsedRecord(line_number=2, raw="unmatched", fields={}, pattern_id=None, matched=False, confidence=0.0),
            ParsedRecord(line_number=3, raw="matched2", fields={"f": "v"}, pattern_id="p1", matched=True, confidence=1.0),
        ]

        output = tmp_path / "output.jsonl"
        count = write_jsonl(records, output, include_unmatched=False)

        assert count == 2
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_write_jsonl_empty_records(self, tmp_path):
        """Test JSONL write with empty records list."""
        output = tmp_path / "output.jsonl"
        count = write_jsonl([], output)

        assert count == 0
        assert output.read_text() == ""


class TestSQLiteEdgeCases:
    """Edge cases for SQLite output."""

    def test_write_sqlite_empty_records(self, tmp_path):
        """Test SQLite write with empty records list."""
        output = tmp_path / "output.db"
        count = write_sqlite([], output)

        assert count == 0
        assert output.exists()

    def test_write_sqlite_no_typed(self, sample_records, tmp_path):
        """Test SQLite write without typed fields."""
        records, patterns = sample_records
        output = tmp_path / "output.db"

        count = write_sqlite(records, output, patterns=patterns, include_typed=False)
        assert count == len(records)
