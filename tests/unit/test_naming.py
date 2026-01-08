"""Tests for smart field naming."""
from log_sculptor.core.naming import infer_field_name, generate_field_names
from log_sculptor.core.tokenizer import Token, TokenType, tokenize


class TestInferFieldName:
    """Tests for infer_field_name function."""

    def test_infer_from_prev_indicator(self):
        token = Token(type=TokenType.NUMBER, value="200", start=0, end=3)
        prev = Token(type=TokenType.WORD, value="status", start=0, end=6)
        name = infer_field_name(token, 0, prev, None, [], set())
        assert name == "status"

    def test_infer_http_method(self):
        token = Token(type=TokenType.WORD, value="GET", start=0, end=3)
        name = infer_field_name(token, 0, None, None, [], set())
        assert name == "method"

    def test_infer_status_code(self):
        token = Token(type=TokenType.NUMBER, value="404", start=0, end=3)
        name = infer_field_name(token, 0, None, None, [], set())
        assert name == "status"

    def test_infer_path(self):
        token = Token(type=TokenType.WORD, value="/api/users", start=0, end=10)
        name = infer_field_name(token, 0, None, None, [], set())
        assert name == "path"

    def test_infer_log_level(self):
        token = Token(type=TokenType.WORD, value="ERROR", start=0, end=5)
        name = infer_field_name(token, 0, None, None, [], set())
        assert name == "level"

    def test_infer_uuid(self):
        token = Token(type=TokenType.WORD, value="550e8400-e29b-41d4-a716-446655440000", start=0, end=36)
        name = infer_field_name(token, 0, None, None, [], set())
        assert name == "uuid"

    def test_fallback_to_type_name(self):
        token = Token(type=TokenType.QUOTED, value='"some message"', start=0, end=14)
        name = infer_field_name(token, 0, None, None, [], set())
        assert name == "message"

    def test_unique_names(self):
        # Use a number that won't match status code pattern (must be 4+ digits)
        token = Token(type=TokenType.NUMBER, value="12345", start=0, end=5)
        existing = {"value"}
        name = infer_field_name(token, 0, None, None, [], existing)
        assert name == "value_1"


class TestGenerateFieldNames:
    """Tests for generate_field_names function."""

    def test_simple_log_line(self):
        tokens = tokenize("INFO Starting server")
        names = generate_field_names(tokens)
        assert "level" in names  # INFO should be detected as level

    def test_http_log_line(self):
        tokens = tokenize("GET /api/users 200")
        names = generate_field_names(tokens)
        assert "method" in names
        assert "path" in names
        assert "status" in names

    def test_key_value_pairs(self):
        # Tokenizer splits key=value into separate tokens
        # This test verifies naming works with the actual tokenization
        tokens = tokenize("user=admin status=active")
        names = generate_field_names(tokens)
        # Should have names for all non-whitespace tokens
        assert len(names) > 0
        # Should include "user" since it's a field indicator
        assert "user" in names

    def test_all_unique_names(self):
        tokens = tokenize("100 200 300 400")
        names = generate_field_names(tokens)
        # All should be unique
        assert len(names) == len(set(names))

    def test_timestamp_naming(self):
        tokens = tokenize("2024-01-15T10:30:00 INFO message")
        names = generate_field_names(tokens)
        assert "timestamp" in names
