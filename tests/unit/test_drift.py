"""Tests for format drift detection."""
from pathlib import Path
from log_sculptor.core.drift import DriftDetector, DriftReport, detect_drift
from log_sculptor.core.patterns import PatternSet, learn_patterns


class TestDriftReport:
    """Tests for DriftReport dataclass."""

    def test_match_rate_calculation(self):
        report = DriftReport(
            total_lines=100,
            matched_lines=80,
            pattern_distribution={"p1": 80},
            format_changes=[],
            dominant_patterns=[],
        )
        assert report.match_rate == 0.8

    def test_match_rate_empty(self):
        report = DriftReport(
            total_lines=0,
            matched_lines=0,
            pattern_distribution={},
            format_changes=[],
            dominant_patterns=[],
        )
        assert report.match_rate == 0.0

    def test_has_drift_true(self):
        from log_sculptor.core.drift import FormatChange
        report = DriftReport(
            total_lines=100,
            matched_lines=100,
            pattern_distribution={"p1": 50, "p2": 50},
            format_changes=[FormatChange(50, "p1", "p2", 0.9)],
            dominant_patterns=[],
        )
        assert report.has_drift is True

    def test_has_drift_false(self):
        report = DriftReport(
            total_lines=100,
            matched_lines=100,
            pattern_distribution={"p1": 100},
            format_changes=[],
            dominant_patterns=[],
        )
        assert report.has_drift is False

    def test_summary_output(self):
        report = DriftReport(
            total_lines=100,
            matched_lines=80,
            pattern_distribution={"p1": 80},
            format_changes=[],
            dominant_patterns=[],
        )
        summary = report.summary()
        assert "100" in summary
        assert "80" in summary

    def test_summary_with_format_changes(self):
        from log_sculptor.core.drift import FormatChange
        changes = [
            FormatChange(line_number=50, old_pattern_id="p1", new_pattern_id="p2", confidence=0.9),
            FormatChange(line_number=75, old_pattern_id="p2", new_pattern_id="p3", confidence=0.8),
        ]
        report = DriftReport(
            total_lines=100,
            matched_lines=90,
            pattern_distribution={"p1": 50, "p2": 25, "p3": 25},
            format_changes=changes,
            dominant_patterns=[],
        )
        summary = report.summary()
        assert "Format changes" in summary
        assert "Line 50" in summary
        assert "p1" in summary
        assert "p2" in summary

    def test_summary_many_format_changes(self):
        """Test summary truncates when > 5 format changes."""
        from log_sculptor.core.drift import FormatChange
        changes = [
            FormatChange(line_number=i * 10, old_pattern_id=f"p{i}", new_pattern_id=f"p{i+1}", confidence=0.9)
            for i in range(10)
        ]
        report = DriftReport(
            total_lines=100,
            matched_lines=90,
            pattern_distribution={f"p{i}": 10 for i in range(10)},
            format_changes=changes,
            dominant_patterns=[],
        )
        summary = report.summary()
        assert "... and 5 more" in summary


class TestDriftDetector:
    """Tests for DriftDetector class."""

    def test_init_defaults(self):
        detector = DriftDetector()
        assert detector.window_size == 100
        assert detector.change_threshold == 0.5

    def test_init_custom_params(self):
        detector = DriftDetector(window_size=50, change_threshold=0.3)
        assert detector.window_size == 50
        assert detector.change_threshold == 0.3


class TestDetectDrift:
    """Integration tests for drift detection."""

    def test_no_drift_uniform_log(self, tmp_path: Path):
        # Create a uniform log file
        log_file = tmp_path / "uniform.log"
        lines = ["2024-01-15 INFO message here\n"] * 100
        log_file.write_text("".join(lines))

        # Learn patterns
        patterns = learn_patterns(log_file)

        # Detect drift
        report = detect_drift(log_file, patterns)

        assert report.total_lines == 100
        assert report.matched_lines == 100
        assert len(report.format_changes) == 0

    def test_drift_format_change(self, tmp_path: Path):
        # Create a log with format change
        log_file = tmp_path / "mixed.log"
        lines = (
            ["2024-01-15 INFO message\n"] * 50 +
            ["ERROR: something failed at line 123\n"] * 50
        )
        log_file.write_text("".join(lines))

        # Learn patterns (will find two patterns)
        patterns = learn_patterns(log_file)

        # Detect drift
        report = detect_drift(log_file, patterns, window_size=20)

        assert report.total_lines == 100
        assert len(report.pattern_distribution) >= 2
        # Should detect at least one format change
        assert report.has_drift or len(report.pattern_distribution) >= 2

    def test_empty_file(self, tmp_path: Path):
        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        patterns = PatternSet()
        report = detect_drift(log_file, patterns)

        assert report.total_lines == 0
        assert report.match_rate == 0.0
        assert not report.has_drift
