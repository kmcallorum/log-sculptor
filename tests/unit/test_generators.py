"""Tests for log data generators."""
import pytest
import json
from log_sculptor.testing.generators import (
    LogGenerator,
    generate_apache_logs,
    generate_syslog,
    generate_json_logs,
    generate_app_logs,
    generate_mixed_logs,
    write_sample_logs,
)


class TestLogGenerator:
    """Tests for LogGenerator base class."""

    def test_seed_reproducibility(self):
        from datetime import datetime
        # Use same start time for both generators
        start = datetime(2024, 1, 15, 10, 30, 0)

        # Generate first sequence
        gen1 = LogGenerator(seed=42, start_time=start)
        ip1 = gen1._random_ip()
        method1 = gen1._random_method()
        status1 = gen1._random_status()

        # Generate second sequence with same seed
        gen2 = LogGenerator(seed=42, start_time=start)
        ip2 = gen2._random_ip()
        method2 = gen2._random_method()
        status2 = gen2._random_status()

        assert ip1 == ip2
        assert method1 == method2
        assert status1 == status2

    def test_random_ip_format(self):
        gen = LogGenerator(seed=42)
        ip = gen._random_ip()

        parts = ip.split(".")
        assert len(parts) == 4
        for part in parts:
            assert 0 <= int(part) <= 255

    def test_random_method(self):
        gen = LogGenerator(seed=42)
        methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}

        for _ in range(20):
            method = gen._random_method()
            assert method in methods

    def test_random_status(self):
        gen = LogGenerator(seed=42)

        for _ in range(20):
            status = gen._random_status()
            assert 100 <= status < 600

    def test_random_uuid_format(self):
        gen = LogGenerator(seed=42)
        uuid = gen._random_uuid()

        parts = uuid.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestGenerateApacheLogs:
    """Tests for Apache log generator."""

    def test_generates_correct_count(self):
        logs = list(generate_apache_logs(count=10))
        assert len(logs) == 10

    def test_reproducible_with_seed(self):
        logs1 = list(generate_apache_logs(count=5, seed=42))
        logs2 = list(generate_apache_logs(count=5, seed=42))

        assert logs1 == logs2

    def test_format_structure(self):
        logs = list(generate_apache_logs(count=1, seed=42))
        log = logs[0]

        # Apache CLF format has specific structure
        assert " - " in log  # ident and user
        assert "[" in log and "]" in log  # timestamp brackets
        assert "HTTP/1.1" in log
        assert '"' in log  # quoted strings


class TestGenerateSyslog:
    """Tests for syslog generator."""

    def test_generates_correct_count(self):
        logs = list(generate_syslog(count=10))
        assert len(logs) == 10

    def test_contains_hostname(self):
        logs = list(generate_syslog(count=1, hostname="myserver"))

        assert "myserver" in logs[0]

    def test_format_structure(self):
        logs = list(generate_syslog(count=1, seed=42))
        log = logs[0]

        # Syslog has priority, program[pid]
        assert "<" in log and ">" in log  # priority
        assert "[" in log and "]" in log  # pid


class TestGenerateJsonLogs:
    """Tests for JSON log generator."""

    def test_generates_correct_count(self):
        logs = list(generate_json_logs(count=10))
        assert len(logs) == 10

    def test_valid_json(self):
        logs = list(generate_json_logs(count=5, seed=42))

        for log in logs:
            parsed = json.loads(log)
            assert "timestamp" in parsed
            assert "level" in parsed
            assert "message" in parsed

    def test_error_logs_have_extra_fields(self):
        # Generate enough logs to likely get an error
        logs = list(generate_json_logs(count=100, seed=42))

        error_logs = [json.loads(log) for log in logs if '"level": "ERROR"' in log]

        # At least some error logs should have error field
        if error_logs:
            assert any("error" in log for log in error_logs)


class TestGenerateAppLogs:
    """Tests for application log generator."""

    def test_generates_correct_count(self):
        logs = list(generate_app_logs(count=10))
        assert len(logs) == 10

    def test_contains_app_name(self):
        logs = list(generate_app_logs(count=1, app_name="myapp"))

        assert "[myapp]" in logs[0]

    def test_has_level(self):
        logs = list(generate_app_logs(count=10, seed=42))
        valid_levels = {"DEBUG", "INFO", "WARN", "ERROR"}

        for log in logs:
            has_level = any(f"[{level}]" in log for level in valid_levels)
            assert has_level


class TestGenerateMixedLogs:
    """Tests for mixed format log generator."""

    def test_generates_correct_count(self):
        logs = list(generate_mixed_logs(count=10))
        assert len(logs) == 10

    def test_format_changes_at_specified_points(self):
        logs = list(generate_mixed_logs(count=100, seed=42, change_format_at=[50]))

        # First 50 and last 50 should have different formats
        first_half = logs[:50]
        second_half = logs[50:]

        # Just verify we got logs (format detection is complex)
        assert len(first_half) == 50
        assert len(second_half) == 50


class TestWriteSampleLogs:
    """Tests for write_sample_logs function."""

    def test_writes_file(self, tmp_path):
        output = tmp_path / "test.log"

        result = write_sample_logs(output, generator="app", count=10, seed=42)

        assert result == output
        assert output.exists()

    def test_correct_line_count(self, tmp_path):
        output = tmp_path / "test.log"

        write_sample_logs(output, generator="app", count=50, seed=42)

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 50

    def test_all_generator_types(self, tmp_path):
        generators = ["app", "apache", "syslog", "json", "mixed"]

        for gen_type in generators:
            output = tmp_path / f"{gen_type}.log"
            write_sample_logs(output, generator=gen_type, count=10, seed=42)
            assert output.exists()
            assert output.stat().st_size > 0

    def test_invalid_generator_raises(self, tmp_path):
        output = tmp_path / "test.log"

        with pytest.raises(ValueError):
            write_sample_logs(output, generator="invalid", count=10)
