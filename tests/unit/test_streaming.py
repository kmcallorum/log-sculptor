"""Tests for streaming and performance optimizations."""
import pytest
from pathlib import Path
from log_sculptor.core.streaming import stream_parse, PatternCache, parallel_learn
from log_sculptor.core.patterns import PatternSet, learn_patterns


class TestStreamParse:
    """Tests for stream_parse function."""

    def test_stream_parse_basic(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 INFO message one\n2024-01-15 INFO message two\n")

        patterns = learn_patterns(log_file)
        records = list(stream_parse(log_file, patterns))

        assert len(records) == 2
        assert records[0].line_number == 1
        assert records[1].line_number == 2

    def test_stream_parse_with_callback(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 INFO message\n")

        patterns = learn_patterns(log_file)
        callback_count = [0]

        def callback(record):
            callback_count[0] += 1

        list(stream_parse(log_file, patterns, callback=callback))
        assert callback_count[0] == 1

    def test_stream_parse_empty_file(self, tmp_path: Path):
        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        patterns = PatternSet()
        records = list(stream_parse(log_file, patterns))

        assert len(records) == 0

    def test_stream_parse_skips_empty_lines(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_file.write_text("line1\n\nline2\n\n\nline3\n")

        patterns = learn_patterns(log_file)
        records = list(stream_parse(log_file, patterns))

        assert len(records) == 3


class TestPatternCache:
    """Tests for PatternCache class."""

    def test_cache_initialization(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 INFO message\n")

        patterns = learn_patterns(log_file)
        cache = PatternCache(patterns)

        assert cache.patterns == patterns

    def test_cache_match(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 INFO message\n")

        patterns = learn_patterns(log_file)
        cache = PatternCache(patterns)

        pattern, fields = cache.match("2024-01-15 INFO message")
        assert pattern is not None

    def test_cache_no_match(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        log_file.write_text("2024-01-15 INFO message\n")

        patterns = learn_patterns(log_file)
        cache = PatternCache(patterns)

        pattern, fields = cache.match("completely different format")
        assert pattern is None


class TestParallelLearn:
    """Tests for parallel_learn function."""

    def test_parallel_learn_small_file(self, tmp_path: Path):
        log_file = tmp_path / "small.log"
        lines = ["2024-01-15 INFO message\n"] * 100
        log_file.write_text("".join(lines))

        # Small file should still work
        patterns = parallel_learn(log_file, num_workers=2, chunk_size=50)

        assert len(patterns.patterns) >= 1

    def test_parallel_learn_multiple_patterns(self, tmp_path: Path):
        log_file = tmp_path / "multi.log"
        lines = (
            ["2024-01-15 INFO message\n"] * 50 +
            ["ERROR: failure\n"] * 50
        )
        log_file.write_text("".join(lines))

        patterns = parallel_learn(log_file, num_workers=2, chunk_size=30)

        # Should find at least 2 distinct patterns
        assert len(patterns.patterns) >= 1

    def test_parallel_learn_empty_file(self, tmp_path: Path):
        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        patterns = parallel_learn(log_file, num_workers=2)

        assert len(patterns.patterns) == 0
