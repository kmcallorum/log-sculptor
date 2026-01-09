"""Tests for smart field naming."""
from log_sculptor.core.naming import (
    infer_field_name,
    generate_field_names,
    refine_pattern_names,
    FIELD_INDICATORS,
    VALUE_PATTERNS,
)
from log_sculptor.core.tokenizer import tokenize, Token, TokenType


class TestInferFieldName:
    """Tests for field name inference."""

    def test_from_prev_indicator(self):
        """Test inference from previous indicator word."""
        tokens = tokenize("user admin")
        non_ws = [t for t in tokens if t.type != TokenType.WHITESPACE]

        name = infer_field_name(
            non_ws[1],  # 'admin'
            index=1,
            prev_token=non_ws[0],  # 'user'
            next_token=None,
            all_tokens=tokens,
            existing_names=set(),
        )
        assert name == "user"

    def test_http_method_pattern(self):
        """Test inference from HTTP method pattern."""
        tokens = tokenize("GET /api/users")
        non_ws = [t for t in tokens if t.type != TokenType.WHITESPACE]

        name = infer_field_name(
            non_ws[0],  # 'GET'
            index=0,
            prev_token=None,
            next_token=non_ws[1],
            all_tokens=tokens,
            existing_names=set(),
        )
        assert name == "method"

    def test_status_code_pattern(self):
        """Test inference from HTTP status code pattern."""
        tokens = tokenize("200")
        non_ws = [t for t in tokens if t.type != TokenType.WHITESPACE]

        name = infer_field_name(
            non_ws[0],
            index=0,
            prev_token=None,
            next_token=None,
            all_tokens=tokens,
            existing_names=set(),
        )
        assert name == "status"

    def test_path_pattern(self):
        """Test inference from URL path pattern."""
        tokens = tokenize("/api/users")
        non_ws = [t for t in tokens if t.type != TokenType.WHITESPACE]

        name = infer_field_name(
            non_ws[0],
            index=0,
            prev_token=None,
            next_token=None,
            all_tokens=tokens,
            existing_names=set(),
        )
        assert name == "path"

    def test_log_level_pattern(self):
        """Test inference from log level pattern."""
        for level in ["INFO", "WARN", "ERROR", "DEBUG"]:
            tokens = tokenize(level)
            non_ws = [t for t in tokens if t.type != TokenType.WHITESPACE]

            name = infer_field_name(
                non_ws[0],
                index=0,
                prev_token=None,
                next_token=None,
                all_tokens=tokens,
                existing_names=set(),
            )
            assert name == "level"

    def test_uuid_pattern(self):
        """Test inference from UUID pattern."""
        # Create a token that contains a UUID value (simulating a parsed quoted or word token)
        uuid_value = "550e8400-e29b-41d4-a716-446655440000"
        token = Token(TokenType.WORD, uuid_value, 0, len(uuid_value))

        name = infer_field_name(
            token,
            index=0,
            prev_token=None,
            next_token=None,
            all_tokens=[token],
            existing_names=set(),
        )
        assert name == "uuid"

    def test_uniqueness(self):
        """Test that names are made unique."""
        tokens = tokenize("INFO message INFO")
        non_ws = [t for t in tokens if t.type != TokenType.WHITESPACE]

        existing = {"level"}
        name = infer_field_name(
            non_ws[0],
            index=0,
            prev_token=None,
            next_token=non_ws[1],
            all_tokens=tokens,
            existing_names=existing,
        )
        assert name == "level_1"

    def test_type_based_fallback(self):
        """Test fallback to token type based name."""
        token = Token(TokenType.NUMBER, "12345", 0, 5)

        name = infer_field_name(
            token,
            index=0,
            prev_token=None,
            next_token=None,
            all_tokens=[token],
            existing_names=set(),
        )
        assert name == "value"


class TestGenerateFieldNames:
    """Tests for batch field name generation."""

    def test_simple_line(self):
        """Test name generation for simple line."""
        tokens = tokenize("INFO server started")
        names = generate_field_names(tokens)

        assert len(names) == 3
        assert "level" in names

    def test_apache_log(self):
        """Test name generation for Apache-style log."""
        tokens = tokenize('192.168.1.1 - - GET /api HTTP/1.1 200')
        names = generate_field_names(tokens)

        assert "ip" in names
        assert "method" in names
        assert "status" in names


class TestRefinePatternNames:
    """Tests for pattern name refinement."""

    def test_refine_with_examples(self):
        """Test refining names with example lines."""
        from log_sculptor.core.models import PatternElement
        from log_sculptor.core.tokenizer import TokenType

        elements = [
            PatternElement(type="field", token_type=TokenType.WORD, field_name="field_0"),
            PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
            PatternElement(type="field", token_type=TokenType.WORD, field_name="field_1"),
        ]

        refine_pattern_names(elements, ["INFO message"])

        field_elements = [e for e in elements if e.type == "field"]
        assert any(e.field_name == "level" for e in field_elements)

    def test_refine_no_examples(self):
        """Test refining with no examples does nothing."""
        from log_sculptor.core.models import PatternElement
        from log_sculptor.core.tokenizer import TokenType

        elements = [
            PatternElement(type="field", token_type=TokenType.WORD, field_name="field_0"),
        ]

        refine_pattern_names(elements, None)
        assert elements[0].field_name == "field_0"

        refine_pattern_names(elements, [])
        assert elements[0].field_name == "field_0"


class TestFieldIndicators:
    """Tests for field indicator constants."""

    def test_indicators_exist(self):
        """Test common indicators exist."""
        assert "user" in FIELD_INDICATORS
        assert "ip" in FIELD_INDICATORS
        assert "method" in FIELD_INDICATORS
        assert "status" in FIELD_INDICATORS
        assert "timestamp" in FIELD_INDICATORS

    def test_value_patterns_exist(self):
        """Test value patterns are defined."""
        assert len(VALUE_PATTERNS) > 0
