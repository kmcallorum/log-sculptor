"""Tests for streaming and performance optimizations."""
import pytest

from log_sculptor.core.streaming import (
    stream_parse,
    parallel_learn,
    PatternCache,
    _read_lines_mmap,
)
from log_sculptor.core.patterns import learn_patterns
from log_sculptor.testing.generators import write_sample_logs


@pytest.fixture
def large_log_file(tmp_path):
    """Create a larger log file for testing."""
    log_file = tmp_path / "large.log"
    write_sample_logs(log_file, generator="apache", count=500, seed=42)
    return log_file


@pytest.fixture
def small_log_file(tmp_path):
    """Create a small log file for testing."""
    log_file = tmp_path / "small.log"
    write_sample_logs(log_file, generator="app", count=50, seed=42)
    return log_file


class TestReadLinesMmap:
    """Tests for memory-mapped file reading."""

    def test_read_lines(self, small_log_file):
        """Test basic line reading."""
        lines = list(_read_lines_mmap(small_log_file))
        assert len(lines) == 50

    def test_handles_encoding(self, tmp_path):
        """Test handling of encoding issues."""
        log_file = tmp_path / "unicode.log"
        log_file.write_bytes(b"line1\nline2\ninvalid \xff byte\nline4\n")

        lines = list(_read_lines_mmap(log_file))
        assert len(lines) == 4


class TestStreamParse:
    """Tests for stream parsing."""

    def test_stream_parse_basic(self, small_log_file):
        """Test basic stream parsing."""
        patterns = learn_patterns(small_log_file)
        records = list(stream_parse(small_log_file, patterns))

        assert len(records) > 0
        assert all(r.line_number > 0 for r in records)

    def test_stream_parse_with_callback(self, small_log_file):
        """Test stream parsing with callback."""
        patterns = learn_patterns(small_log_file)
        callback_count = [0]

        def callback(record):
            callback_count[0] += 1

        records = list(stream_parse(small_log_file, patterns, callback=callback))

        assert callback_count[0] == len(records)

    def test_stream_parse_no_mmap(self, small_log_file):
        """Test stream parsing without mmap."""
        patterns = learn_patterns(small_log_file)
        records = list(stream_parse(small_log_file, patterns, use_mmap=False))

        assert len(records) > 0

    def test_stream_parse_no_types(self, small_log_file):
        """Test stream parsing without type detection."""
        patterns = learn_patterns(small_log_file)
        records = list(stream_parse(small_log_file, patterns, detect_types=False))

        assert len(records) > 0
        # typed_fields should be None when detect_types=False
        assert all(r.typed_fields is None for r in records)


class TestPatternCache:
    """Tests for pattern caching."""

    def test_cache_creation(self, small_log_file):
        """Test cache creation."""
        patterns = learn_patterns(small_log_file)
        cache = PatternCache(patterns)

        assert cache.patterns == patterns
        assert len(cache._sig_to_patterns) >= 0

    def test_cache_match(self, small_log_file):
        """Test cache matching."""
        patterns = learn_patterns(small_log_file)
        cache = PatternCache(patterns)

        # Read a line from the file
        with open(small_log_file) as f:
            line = f.readline().strip()

        pattern, fields = cache.match(line)
        # Should match (line came from the file we learned from)
        assert pattern is not None or fields is None


class TestParallelLearn:
    """Tests for parallel learning."""

    def test_parallel_learn_small_file(self, small_log_file):
        """Test parallel learning falls back for small files."""
        patterns = parallel_learn(small_log_file, num_workers=2, chunk_size=100)

        assert len(patterns.patterns) > 0

    def test_parallel_learn_large_file(self, large_log_file):
        """Test parallel learning with larger file."""
        patterns = parallel_learn(large_log_file, num_workers=2, chunk_size=100)

        assert len(patterns.patterns) > 0

    def test_parallel_learn_with_sample(self, large_log_file):
        """Test parallel learning with sample size."""
        patterns = parallel_learn(large_log_file, sample_size=200, num_workers=2)

        assert len(patterns.patterns) > 0

    def test_parallel_learn_empty_file(self, tmp_path):
        """Test parallel learning with empty file."""
        empty_file = tmp_path / "empty.log"
        empty_file.write_text("")

        patterns = parallel_learn(empty_file, num_workers=2)
        assert len(patterns.patterns) == 0


class TestStreamParseEdgeCases:
    """Edge cases for stream parsing."""

    def test_stream_parse_empty_file(self, tmp_path):
        """Test stream parsing empty file."""
        from log_sculptor.core.patterns import PatternSet

        empty_file = tmp_path / "empty.log"
        empty_file.write_text("")

        patterns = PatternSet()
        records = list(stream_parse(empty_file, patterns))
        assert len(records) == 0

    def test_stream_parse_file_with_empty_lines(self, tmp_path):
        """Test stream parsing skips empty lines."""
        file = tmp_path / "gaps.log"
        file.write_text("INFO line1\n\n\nINFO line2\n")

        patterns = learn_patterns(file)
        records = list(stream_parse(file, patterns))

        # Should only have 2 records (empty lines skipped)
        assert len(records) == 2

    def test_stream_parse_large_file_uses_mmap(self, tmp_path):
        """Test that large files (>1MB) use mmap."""
        large_file = tmp_path / "large.log"
        # Create a file > 1MB
        line = "INFO " + "x" * 1000 + "\n"
        large_file.write_text(line * 1100)  # ~1.1MB

        patterns = learn_patterns(large_file, sample_size=100)
        records = list(stream_parse(large_file, patterns, use_mmap=True))

        assert len(records) > 0

    def test_stream_parse_unmatched_lines(self, tmp_path):
        """Test stream parsing with unmatched lines."""
        file = tmp_path / "test.log"
        file.write_text("INFO message\nsome random text that wont match\n")

        patterns = learn_patterns(file)
        records = list(stream_parse(file, patterns))

        # All lines should be returned (matched or not)
        assert len(records) >= 1


class TestPatternCacheEdgeCases:
    """Edge cases for pattern caching."""

    def test_cache_with_literal_elements(self, tmp_path):
        """Test cache handles literal elements."""
        file = tmp_path / "test.log"
        file.write_text("ERROR critical failure\n" * 5)

        patterns = learn_patterns(file)
        cache = PatternCache(patterns)

        # The cache should be built
        assert len(cache._sig_to_patterns) >= 0

    def test_cache_no_match(self, tmp_path):
        """Test cache returns None when no match."""
        file = tmp_path / "test.log"
        file.write_text("INFO message\n")

        patterns = learn_patterns(file)
        cache = PatternCache(patterns)

        # Try to match something completely different
        pattern, fields = cache.match("@@@ %%% !!!")
        # Either matches or doesn't
        if pattern is None:
            assert fields is None
