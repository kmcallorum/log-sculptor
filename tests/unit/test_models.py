"""Tests for core data models."""
import pytest
from log_sculptor.core.models import Pattern, PatternElement
from log_sculptor.core.tokenizer import TokenType, tokenize


class TestPatternElement:
    """Tests for PatternElement."""

    def test_literal_element(self):
        """Test literal element creation."""
        elem = PatternElement(
            type="literal",
            token_type=TokenType.WORD,
            value="INFO",
        )
        assert elem.type == "literal"
        assert elem.value == "INFO"
        assert elem.field_name is None

    def test_field_element(self):
        """Test field element creation."""
        elem = PatternElement(
            type="field",
            token_type=TokenType.NUMBER,
            field_name="count",
        )
        assert elem.type == "field"
        assert elem.field_name == "count"

    def test_to_dict(self):
        """Test element serialization."""
        elem = PatternElement(
            type="field",
            token_type=TokenType.IP,
            field_name="client_ip",
        )
        d = elem.to_dict()

        assert d["type"] == "field"
        assert d["token_type"] == "IP"
        assert d["field_name"] == "client_ip"

    def test_from_dict(self):
        """Test element deserialization."""
        data = {
            "type": "literal",
            "token_type": "WORD",
            "value": "ERROR",
        }
        elem = PatternElement.from_dict(data)

        assert elem.type == "literal"
        assert elem.token_type == TokenType.WORD
        assert elem.value == "ERROR"


class TestPattern:
    """Tests for Pattern."""

    @pytest.fixture
    def sample_pattern(self):
        """Create a sample pattern."""
        return Pattern(
            id="test-pattern",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="level"),
                PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="message"),
            ],
            frequency=100,
            confidence=0.95,
            example="INFO hello world",
        )

    def test_pattern_creation(self, sample_pattern):
        """Test pattern creation."""
        assert sample_pattern.id == "test-pattern"
        assert len(sample_pattern.elements) == 3
        assert sample_pattern.frequency == 100
        assert sample_pattern.confidence == 0.95

    def test_pattern_match_success(self, sample_pattern):
        """Test pattern matching success."""
        # Pattern has 2 non-ws elements (field WORD, field WORD)
        # So input must have exactly 2 non-ws tokens
        tokens = tokenize("ERROR happened")
        fields = sample_pattern.match(tokens)

        assert fields is not None
        assert "level" in fields
        assert fields["level"] == "ERROR"
        assert "message" in fields
        assert fields["message"] == "happened"

    def test_pattern_match_failure(self, sample_pattern):
        """Test pattern matching failure."""
        # Too many tokens - pattern expects 2 non-ws, this has 3
        tokens = tokenize("not enough tokens")
        fields = sample_pattern.match(tokens)
        assert fields is None

    def test_pattern_to_dict(self, sample_pattern):
        """Test pattern serialization."""
        d = sample_pattern.to_dict()

        assert d["id"] == "test-pattern"
        assert d["frequency"] == 100
        assert d["confidence"] == 0.95
        assert len(d["elements"]) == 3

    def test_pattern_from_dict(self, sample_pattern):
        """Test pattern deserialization."""
        d = sample_pattern.to_dict()
        restored = Pattern.from_dict(d)

        assert restored.id == sample_pattern.id
        assert restored.frequency == sample_pattern.frequency
        assert len(restored.elements) == len(sample_pattern.elements)

    def test_pattern_match_with_literal(self):
        """Test pattern matching with literal elements."""
        pattern = Pattern(
            id="test",
            elements=[
                PatternElement(type="literal", token_type=TokenType.WORD, value="ERROR"),
                PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="message"),
            ],
            frequency=1,
            confidence=1.0,
            example="ERROR test",
        )

        # Should match
        tokens = tokenize("ERROR test")
        fields = pattern.match(tokens)
        assert fields is not None
        assert fields["message"] == "test"

        # Should not match (wrong literal)
        tokens = tokenize("INFO test")
        fields = pattern.match(tokens)
        assert fields is None
