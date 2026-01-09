"""Tests for field type detection."""
from log_sculptor.types.detector import (
    detect_type,
    detect_types_for_fields,
    FieldType,
    TypedValue,
    _is_valid_ipv4,
)


class TestTypedValue:
    """Tests for TypedValue dataclass."""

    def test_to_dict(self):
        """Test TypedValue to_dict method."""
        tv = TypedValue("192.168.1.1", FieldType.IP, "192.168.1.1")
        result = tv.to_dict()

        assert result["raw"] == "192.168.1.1"
        assert result["type"] == "ip"
        assert result["normalized"] == "192.168.1.1"


class TestIPDetection:
    """Tests for IP address detection."""

    def test_valid_ipv4(self):
        """Test valid IPv4 detection."""
        result = detect_type("192.168.1.1")
        assert result.type == FieldType.IP
        assert result.normalized == "192.168.1.1"

    def test_valid_ipv4_edge(self):
        """Test edge case IPv4."""
        result = detect_type("0.0.0.0")
        assert result.type == FieldType.IP

        result = detect_type("255.255.255.255")
        assert result.type == FieldType.IP

    def test_invalid_ipv4_octet(self):
        """Test invalid IPv4 with octet > 255."""
        assert not _is_valid_ipv4("192.168.1.256")
        result = detect_type("192.168.1.256")
        assert result.type != FieldType.IP

    def test_ipv6_basic(self):
        """Test IPv6 detection."""
        result = detect_type("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert result.type == FieldType.IP
        assert result.normalized == result.raw.lower()

    def test_ipv6_compressed(self):
        """Test compressed IPv6."""
        result = detect_type("2001:db8::")
        assert result.type == FieldType.IP

    def test_ipv6_loopback(self):
        """Test IPv6 loopback."""
        result = detect_type("::")
        assert result.type == FieldType.IP


class TestURLDetection:
    """Tests for URL detection."""

    def test_http_url(self):
        """Test HTTP URL detection."""
        result = detect_type("http://example.com/path")
        assert result.type == FieldType.URL

    def test_https_url(self):
        """Test HTTPS URL detection."""
        result = detect_type("https://example.com/path?query=1")
        assert result.type == FieldType.URL

    def test_not_url(self):
        """Test non-URL is not detected as URL."""
        result = detect_type("example.com")
        assert result.type != FieldType.URL


class TestUUIDDetection:
    """Tests for UUID detection."""

    def test_valid_uuid(self):
        """Test valid UUID detection."""
        result = detect_type("550e8400-e29b-41d4-a716-446655440000")
        assert result.type == FieldType.UUID
        assert result.normalized == result.raw.lower()

    def test_uuid_uppercase(self):
        """Test uppercase UUID detection."""
        result = detect_type("550E8400-E29B-41D4-A716-446655440000")
        assert result.type == FieldType.UUID
        assert result.normalized == "550e8400-e29b-41d4-a716-446655440000"

    def test_invalid_uuid(self):
        """Test invalid UUID not detected."""
        result = detect_type("550e8400-e29b-41d4-a716")
        assert result.type != FieldType.UUID


class TestHexDetection:
    """Tests for hex value detection."""

    def test_hex_with_prefix(self):
        """Test hex with 0x prefix."""
        result = detect_type("0x1a2b3c4d5e6f7890")
        assert result.type == FieldType.HEX
        assert result.normalized == "1a2b3c4d5e6f7890"

    def test_hex_without_prefix(self):
        """Test hex without prefix."""
        result = detect_type("1a2b3c4d5e6f7890")
        assert result.type == FieldType.HEX

    def test_short_hex_is_int(self):
        """Test short hex detected as int (if all digits)."""
        result = detect_type("12345678")
        # Pure digits should be INT, not HEX
        assert result.type == FieldType.INT


class TestBoolDetection:
    """Tests for boolean detection."""

    def test_true_values(self):
        """Test true boolean values."""
        for val in ["true", "True", "TRUE", "yes", "Yes", "1", "on", "On"]:
            result = detect_type(val)
            assert result.type == FieldType.BOOL
            assert result.normalized is True

    def test_false_values(self):
        """Test false boolean values."""
        for val in ["false", "False", "FALSE", "no", "No", "0", "off", "Off"]:
            result = detect_type(val)
            assert result.type == FieldType.BOOL
            assert result.normalized is False


class TestNumericDetection:
    """Tests for numeric detection."""

    def test_integer(self):
        """Test integer detection."""
        result = detect_type("12345")
        assert result.type == FieldType.INT
        assert result.normalized == 12345

    def test_negative_integer(self):
        """Test negative integer detection."""
        result = detect_type("-12345")
        assert result.type == FieldType.INT
        assert result.normalized == -12345

    def test_float(self):
        """Test float detection."""
        result = detect_type("123.45")
        assert result.type == FieldType.FLOAT
        assert result.normalized == 123.45

    def test_negative_float(self):
        """Test negative float detection."""
        result = detect_type("-123.45")
        assert result.type == FieldType.FLOAT
        assert result.normalized == -123.45

    def test_very_large_integer(self):
        """Test very large integer is detected."""
        large_int = "999999999999999999999999999999999999"
        result = detect_type(large_int)
        assert result.type == FieldType.INT
        # Python handles arbitrary precision integers
        assert result.normalized == int(large_int)

    def test_zero(self):
        """Test zero detection."""
        # Note: "0" is also a boolean value
        result = detect_type("0")
        # Should be detected as bool (0 = False)
        assert result.type == FieldType.BOOL

    def test_regular_zero(self):
        """Test regular integer zero."""
        result = detect_type("00")  # Not in bool values
        assert result.type == FieldType.INT
        assert result.normalized == 0


class TestTimestampDetection:
    """Tests for timestamp detection in detector."""

    def test_iso8601(self):
        """Test ISO 8601 timestamp detection."""
        result = detect_type("2024-01-15T10:30:00")
        assert result.type == FieldType.TIMESTAMP

    def test_unix_epoch(self):
        """Test Unix epoch detection."""
        result = detect_type("1705315800")
        assert result.type == FieldType.TIMESTAMP


class TestStringFallback:
    """Tests for string fallback."""

    def test_plain_string(self):
        """Test plain string detection."""
        result = detect_type("hello world")
        assert result.type == FieldType.STRING
        assert result.normalized == "hello world"

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        result = detect_type("  hello  ")
        assert result.normalized == "hello"


class TestDetectTypesForFields:
    """Tests for batch field detection."""

    def test_multiple_fields(self):
        """Test detecting types for multiple fields."""
        fields = {
            "ip": "192.168.1.1",
            "count": "42",
            "flag": "true",
            "message": "hello",
        }

        result = detect_types_for_fields(fields)

        assert result["ip"].type == FieldType.IP
        assert result["count"].type == FieldType.INT
        assert result["flag"].type == FieldType.BOOL
        assert result["message"].type == FieldType.STRING
