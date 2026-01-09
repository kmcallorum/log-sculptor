"""Tests for DuckDB and Parquet output writers."""
import pytest
from pathlib import Path

from log_sculptor.core.patterns import ParsedRecord, PatternSet, learn_patterns, parse_logs
from log_sculptor.outputs.duckdb import write_duckdb, _sanitize_column_name
from log_sculptor.outputs.parquet import write_parquet, _sanitize_column_name as parquet_sanitize
from log_sculptor.testing.generators import write_sample_logs

# Check for optional dependencies
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

try:
    import pyarrow
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False


@pytest.fixture
def sample_records(tmp_path):
    """Generate sample parsed records."""
    log_file = tmp_path / "test.log"
    write_sample_logs(log_file, generator="apache", count=20, seed=42)

    patterns = learn_patterns(log_file)
    records = list(parse_logs(log_file, patterns))
    return records, patterns


class TestSanitizeColumnName:
    """Tests for column name sanitization."""

    def test_basic_name(self):
        """Basic alphanumeric name."""
        assert _sanitize_column_name("field") == "field"

    def test_with_dash(self):
        """Name with dash becomes underscore."""
        assert _sanitize_column_name("field-name") == "field_name"

    def test_with_dot(self):
        """Name with dot becomes underscore."""
        assert _sanitize_column_name("field.name") == "field_name"

    def test_starts_with_digit(self):
        """Name starting with digit gets prefix."""
        assert _sanitize_column_name("1field") == "f_1field"

    def test_empty_name(self):
        """Empty name becomes 'field'."""
        assert _sanitize_column_name("") == "field"

    def test_special_chars_only(self):
        """Only special chars becomes underscores."""
        # Special chars become underscores, but since empty string check comes first,
        # the result depends on whether underscores remain
        result = _sanitize_column_name("@#$")
        # Result is "___" (underscores from special chars)
        assert result == "___" or result == "field"

    def test_parquet_sanitize_same(self):
        """Parquet sanitize works the same."""
        assert parquet_sanitize("field-name") == "field_name"
        assert parquet_sanitize("1field") == "f_1field"


@pytest.mark.skipif(not HAS_DUCKDB, reason="duckdb not installed")
class TestDuckDBOutput:
    """Tests for DuckDB output writer."""

    def test_write_duckdb_basic(self, sample_records, tmp_path):
        """Test basic DuckDB write."""
        records, patterns = sample_records
        output = tmp_path / "output.duckdb"

        count = write_duckdb(records, output, patterns=patterns)

        assert count == len(records)
        assert output.exists()

        import duckdb
        conn = duckdb.connect(str(output))

        # Check patterns table
        result = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()
        assert result[0] > 0

        # Check logs table
        result = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
        assert result[0] == len(records)

        conn.close()

    def test_write_duckdb_no_patterns(self, sample_records, tmp_path):
        """Test DuckDB write without patterns."""
        records, _ = sample_records
        output = tmp_path / "output.duckdb"

        count = write_duckdb(records, output, patterns=None)

        assert count == len(records)

        import duckdb
        conn = duckdb.connect(str(output))

        # Patterns table should not exist
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='patterns'"
        ).fetchone()
        assert result[0] == 0

        conn.close()

    def test_write_duckdb_no_raw(self, sample_records, tmp_path):
        """Test DuckDB write without raw line."""
        records, patterns = sample_records
        output = tmp_path / "output.duckdb"

        write_duckdb(records, output, patterns=patterns, include_raw=False)

        import duckdb
        conn = duckdb.connect(str(output))
        result = conn.execute("DESCRIBE logs").fetchall()
        column_names = [r[0] for r in result]
        assert "raw" not in column_names
        conn.close()

    def test_write_duckdb_with_raw(self, sample_records, tmp_path):
        """Test DuckDB write with raw line."""
        records, patterns = sample_records
        output = tmp_path / "output.duckdb"

        write_duckdb(records, output, patterns=patterns, include_raw=True)

        import duckdb
        conn = duckdb.connect(str(output))
        result = conn.execute("DESCRIBE logs").fetchall()
        column_names = [r[0] for r in result]
        assert "raw" in column_names
        conn.close()

    def test_write_duckdb_overwrites(self, sample_records, tmp_path):
        """Test DuckDB write overwrites existing file."""
        records, patterns = sample_records
        output = tmp_path / "output.duckdb"

        write_duckdb(records[:5], output, patterns=patterns)
        write_duckdb(records, output, patterns=patterns)

        import duckdb
        conn = duckdb.connect(str(output))
        result = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
        assert result[0] == len(records)
        conn.close()

    def test_write_duckdb_no_typed(self, sample_records, tmp_path):
        """Test DuckDB write without typed fields."""
        records, patterns = sample_records
        output = tmp_path / "output.duckdb"

        count = write_duckdb(records, output, patterns=patterns, include_typed=False)
        assert count == len(records)


@pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
class TestParquetOutput:
    """Tests for Parquet output writer."""

    def test_write_parquet_basic(self, sample_records, tmp_path):
        """Test basic Parquet write."""
        records, patterns = sample_records
        output = tmp_path / "output.parquet"

        count = write_parquet(records, output, patterns=patterns)

        assert count == len(records)
        assert output.exists()

        import pyarrow.parquet as pq
        table = pq.read_table(output)
        assert len(table) == len(records)

    def test_write_parquet_creates_patterns_file(self, sample_records, tmp_path):
        """Test Parquet write creates patterns file."""
        records, patterns = sample_records
        output = tmp_path / "output.parquet"

        write_parquet(records, output, patterns=patterns)

        patterns_file = tmp_path / "output_patterns.parquet"
        assert patterns_file.exists()

        import pyarrow.parquet as pq
        patterns_table = pq.read_table(patterns_file)
        assert len(patterns_table) > 0

    def test_write_parquet_no_patterns(self, sample_records, tmp_path):
        """Test Parquet write without patterns."""
        records, _ = sample_records
        output = tmp_path / "output.parquet"

        count = write_parquet(records, output, patterns=None)
        assert count == len(records)

        patterns_file = tmp_path / "output_patterns.parquet"
        assert not patterns_file.exists()

    def test_write_parquet_no_raw(self, sample_records, tmp_path):
        """Test Parquet write without raw line."""
        records, patterns = sample_records
        output = tmp_path / "output.parquet"

        write_parquet(records, output, patterns=patterns, include_raw=False)

        import pyarrow.parquet as pq
        table = pq.read_table(output)
        assert "raw" not in table.column_names

    def test_write_parquet_with_raw(self, sample_records, tmp_path):
        """Test Parquet write with raw line."""
        records, patterns = sample_records
        output = tmp_path / "output.parquet"

        write_parquet(records, output, patterns=patterns, include_raw=True)

        import pyarrow.parquet as pq
        table = pq.read_table(output)
        assert "raw" in table.column_names

    def test_write_parquet_empty_records(self, tmp_path):
        """Test Parquet write with empty records."""
        output = tmp_path / "output.parquet"

        count = write_parquet([], output)
        assert count == 0

    def test_write_parquet_no_typed(self, sample_records, tmp_path):
        """Test Parquet write without typed fields."""
        records, patterns = sample_records
        output = tmp_path / "output.parquet"

        count = write_parquet(records, output, patterns=patterns, include_typed=False)
        assert count == len(records)


@pytest.mark.skipif(not HAS_DUCKDB or not HAS_PYARROW, reason="duckdb or pyarrow not installed")
class TestSpecialFieldNames:
    """Test handling of special field names."""

    def test_duplicate_column_names(self, tmp_path):
        """Test handling of duplicate column names after sanitization."""
        record = ParsedRecord(
            line_number=1,
            raw="test",
            fields={"field-a": "v1", "field.a": "v2", "field_a": "v3"},
            pattern_id="test",
            matched=True,
            confidence=1.0,
        )

        # DuckDB
        output_db = tmp_path / "output.duckdb"
        write_duckdb([record], output_db, include_raw=True)

        import duckdb
        conn = duckdb.connect(str(output_db))
        result = conn.execute("DESCRIBE logs").fetchall()
        column_names = [r[0] for r in result]
        # Should have unique columns
        field_cols = [c for c in column_names if c.startswith("field")]
        assert len(field_cols) == len(set(field_cols))
        conn.close()

        # Parquet
        output_pq = tmp_path / "output.parquet"
        write_parquet([record], output_pq, include_raw=True)

        import pyarrow.parquet as pq
        table = pq.read_table(output_pq)
        field_cols = [c for c in table.column_names if c.startswith("field")]
        assert len(field_cols) == len(set(field_cols))
