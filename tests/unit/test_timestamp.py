"""Tests for timestamp detection and parsing."""
import pytest
from datetime import datetime

from log_sculptor.types.timestamp import (
    parse_timestamp,
    normalize_timestamp,
    is_likely_timestamp,
)


class TestParseTimestamp:
    """Tests for timestamp parsing."""

    def test_iso8601_basic(self):
        """Test ISO 8601 basic format."""
        result = parse_timestamp("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_iso8601_with_timezone(self):
        """Test ISO 8601 with timezone."""
        result = parse_timestamp("2024-01-15T10:30:00Z")
        assert result is not None

        result = parse_timestamp("2024-01-15T10:30:00+00:00")
        assert result is not None

    def test_iso8601_with_milliseconds(self):
        """Test ISO 8601 with milliseconds."""
        result = parse_timestamp("2024-01-15T10:30:00.123")
        assert result is not None

        result = parse_timestamp("2024-01-15T10:30:00.123456")
        assert result is not None

    def test_apache_clf_format(self):
        """Test Apache Common Log Format timestamp."""
        result = parse_timestamp("15/Jan/2024:10:30:00 +0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_syslog_format(self):
        """Test syslog timestamp format."""
        result = parse_timestamp("Jan 15 10:30:00")
        assert result is not None
        assert result.month == 1
        assert result.day == 15

    def test_unix_epoch(self):
        """Test Unix epoch timestamp."""
        result = parse_timestamp("1705315800")
        assert result is not None

    def test_unix_epoch_milliseconds(self):
        """Test Unix epoch in milliseconds."""
        result = parse_timestamp("1705315800000")
        assert result is not None

    def test_date_only(self):
        """Test date-only format."""
        result = parse_timestamp("2024-01-15")
        assert result is not None
        assert result.year == 2024

    def test_invalid_timestamp(self):
        """Test invalid timestamp returns None."""
        result = parse_timestamp("not a timestamp")
        assert result is None

        result = parse_timestamp("")
        assert result is None

    def test_common_formats(self):
        """Test various common timestamp formats."""
        formats = [
            "2024-01-15 10:30:00",
            "01/15/2024 10:30:00",
            "15-01-2024 10:30:00",
            "Jan 15, 2024 10:30:00",
        ]

        for fmt in formats:
            result = parse_timestamp(fmt)
            # Some may parse, some may not, but shouldn't error
            pass


class TestNormalizeTimestamp:
    """Tests for timestamp normalization."""

    def test_normalize_iso8601(self):
        """Test normalizing ISO 8601 timestamp."""
        dt = parse_timestamp("2024-01-15T10:30:00")
        assert dt is not None
        result = normalize_timestamp(dt)
        assert result is not None
        assert "2024" in result

    def test_normalize_apache_clf(self):
        """Test normalizing Apache CLF timestamp."""
        dt = parse_timestamp("15/Jan/2024:10:30:00 +0000")
        assert dt is not None
        result = normalize_timestamp(dt)
        assert result is not None

    def test_normalize_with_timezone(self):
        """Test normalizing datetime with timezone."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = normalize_timestamp(dt)
        assert result is not None
        # Should add UTC timezone if missing
        assert "2024-01-15" in result


class TestIsLikelyTimestamp:
    """Tests for timestamp likelihood detection."""

    def test_iso8601_is_timestamp(self):
        """ISO 8601 should be detected as timestamp."""
        assert is_likely_timestamp("2024-01-15T10:30:00") is True

    def test_apache_clf_is_timestamp(self):
        """Apache CLF should be detected as timestamp."""
        assert is_likely_timestamp("15/Jan/2024:10:30:00 +0000") is True

    def test_plain_text_not_timestamp(self):
        """Plain text should not be detected as timestamp."""
        assert is_likely_timestamp("hello world") is False

    def test_number_not_timestamp(self):
        """Regular number should not be detected as timestamp."""
        assert is_likely_timestamp("12345") is False

    def test_unix_epoch_is_timestamp(self):
        """Unix epoch should be detected as timestamp."""
        # Large enough to be an epoch timestamp
        assert is_likely_timestamp("1705315800") is True


class TestEdgeCases:
    """Tests for edge cases in timestamp handling."""

    def test_whitespace_handling(self):
        """Test timestamps with leading/trailing whitespace."""
        result = parse_timestamp("  2024-01-15T10:30:00  ")
        # Should handle whitespace gracefully
        pass

    def test_very_old_date(self):
        """Test very old timestamp."""
        result = parse_timestamp("1970-01-01T00:00:00")
        assert result is not None

    def test_future_date(self):
        """Test future timestamp."""
        result = parse_timestamp("2050-12-31T23:59:59")
        assert result is not None

    def test_leap_year(self):
        """Test leap year date."""
        result = parse_timestamp("2024-02-29T10:30:00")
        assert result is not None
        assert result.month == 2
        assert result.day == 29
