"""Tests using pytest-agents markers and fixtures."""
import pytest
from pathlib import Path

from log_sculptor.core.patterns import PatternSet, learn_patterns, parse_logs
from log_sculptor.testing.generators import write_sample_logs
from log_sculptor.testing.mocks import MockFileReader, MockPatternMatcher
from log_sculptor.testing.fixtures import isolated_test


@pytest.mark.unit
class TestPatternLearningUnit:
    """Unit tests for pattern learning with pytest-agents markers."""

    def test_learn_from_generated_logs(self, tmp_path):
        """Learn patterns from generated Apache logs."""
        log_file = tmp_path / "apache.log"
        write_sample_logs(log_file, generator="apache", count=50, seed=42)

        patterns = learn_patterns(log_file)

        assert len(patterns.patterns) > 0
        assert all(p.frequency > 0 for p in patterns.patterns)

    def test_learn_from_json_logs(self, tmp_path):
        """Learn patterns from generated JSON logs."""
        log_file = tmp_path / "json.log"
        write_sample_logs(log_file, generator="json", count=50, seed=42)

        patterns = learn_patterns(log_file)

        assert len(patterns.patterns) > 0

    def test_learn_reproducible_with_seed(self, tmp_path):
        """Verify pattern learning is reproducible with same seed."""
        log1 = tmp_path / "log1.log"
        log2 = tmp_path / "log2.log"

        write_sample_logs(log1, generator="app", count=100, seed=123)
        write_sample_logs(log2, generator="app", count=100, seed=123)

        patterns1 = learn_patterns(log1)
        patterns2 = learn_patterns(log2)

        assert len(patterns1.patterns) == len(patterns2.patterns)


@pytest.mark.unit
class TestMockIntegration:
    """Unit tests demonstrating mock object usage."""

    def test_mock_file_reader(self):
        """Test MockFileReader tracks calls."""
        reader = MockFileReader()
        reader.add_file(Path("/test.log"), ["line1", "line2", "line3"])

        lines = reader.read_lines(Path("/test.log"))

        assert lines == ["line1", "line2", "line3"]
        assert reader.read_count == 1

    def test_mock_pattern_matcher(self):
        """Test MockPatternMatcher with custom responses."""
        from log_sculptor.testing.mocks import MockPattern

        matcher = MockPatternMatcher()
        matcher.add_response("INFO server started", MockPattern(id="info"), {"level": "INFO"})

        pattern, fields = matcher.match("INFO server started")

        assert pattern.id == "info"
        assert fields["level"] == "INFO"
        assert matcher.call_count == 1

    def test_isolated_test_context(self, tmp_path):
        """Test isolated_test context manager."""
        with isolated_test() as ctx:
            log_file = ctx.create_log_file("test.log", generator="app", count=20)

            assert log_file.exists()
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 20


@pytest.mark.unit
class TestParsingUnit:
    """Unit tests for log parsing."""

    def test_parse_generated_logs(self, tmp_path):
        """Parse generated logs with learned patterns."""
        log_file = tmp_path / "server.log"
        write_sample_logs(log_file, generator="apache", count=30, seed=42)

        patterns = learn_patterns(log_file)
        records = list(parse_logs(log_file, patterns))

        assert len(records) == 30
        matched = sum(1 for r in records if r.matched)
        assert matched > 0

    def test_parse_with_type_detection(self, tmp_path):
        """Verify type detection works on parsed logs."""
        log_file = tmp_path / "server.log"
        write_sample_logs(log_file, generator="apache", count=10, seed=42)

        patterns = learn_patterns(log_file)
        records = list(parse_logs(log_file, patterns, detect_types=True))

        for record in records:
            if record.matched and record.typed_fields:
                # Should have detected some types
                assert len(record.typed_fields) > 0


@pytest.mark.integration
class TestEndToEndIntegration:
    """Integration tests for full workflow."""

    def test_learn_parse_save_load(self, tmp_path):
        """Test complete workflow: generate -> learn -> save -> load -> parse."""
        log_file = tmp_path / "server.log"
        patterns_file = tmp_path / "patterns.json"

        # Generate logs
        write_sample_logs(log_file, generator="syslog", count=100, seed=42)

        # Learn patterns
        patterns = learn_patterns(log_file)
        assert len(patterns.patterns) > 0

        # Save patterns
        patterns.save(patterns_file)
        assert patterns_file.exists()

        # Load patterns
        loaded = PatternSet.load(patterns_file)
        assert len(loaded.patterns) == len(patterns.patterns)

        # Parse with loaded patterns
        records = list(parse_logs(log_file, loaded))
        assert len(records) == 100

    def test_incremental_learning(self, tmp_path):
        """Test incremental pattern learning."""
        log1 = tmp_path / "batch1.log"
        log2 = tmp_path / "batch2.log"

        write_sample_logs(log1, generator="app", count=50, seed=1)
        write_sample_logs(log2, generator="app", count=50, seed=2)

        # Learn from first batch
        patterns1 = learn_patterns(log1)
        initial_count = len(patterns1.patterns)

        # Update with second batch
        patterns2 = learn_patterns(log2)
        patterns1.update(patterns2, merge=True)

        # Should have merged patterns
        assert len(patterns1.patterns) >= 1
        assert initial_count >= 1  # Verify we had patterns initially


@pytest.mark.performance
class TestPerformance:
    """Performance benchmark tests."""

    def test_large_file_learning(self, tmp_path):
        """Benchmark pattern learning on larger file."""
        log_file = tmp_path / "large.log"
        write_sample_logs(log_file, generator="apache", count=1000, seed=42)

        patterns = learn_patterns(log_file)

        # Should complete without error and find patterns
        assert len(patterns.patterns) > 0

    def test_large_file_parsing(self, tmp_path):
        """Benchmark parsing on larger file."""
        log_file = tmp_path / "large.log"
        write_sample_logs(log_file, generator="apache", count=1000, seed=42)

        patterns = learn_patterns(log_file, sample_size=100)
        records = list(parse_logs(log_file, patterns))

        assert len(records) == 1000
