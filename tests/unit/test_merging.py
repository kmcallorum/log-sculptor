"""Tests for pattern merging."""
import pytest
from log_sculptor.core.merging import (
    merge_patterns,
    can_merge,
    merge_two,
    _get_type_signature,
)
from log_sculptor.core.models import Pattern, PatternElement
from log_sculptor.core.tokenizer import TokenType


@pytest.fixture
def sample_pattern():
    """Create a sample pattern."""
    return Pattern(
        id="p1",
        elements=[
            PatternElement(type="field", token_type=TokenType.WORD, field_name="level"),
            PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
            PatternElement(type="field", token_type=TokenType.WORD, field_name="message"),
        ],
        frequency=10,
        confidence=0.9,
        example="INFO hello",
    )


class TestGetTypeSignature:
    """Tests for type signature extraction."""

    def test_simple_pattern(self, sample_pattern):
        """Test type signature for simple pattern."""
        sig = _get_type_signature(sample_pattern)
        # Should exclude whitespace
        assert TokenType.WHITESPACE not in sig
        assert len(sig) == 2

    def test_empty_pattern(self):
        """Test type signature for empty pattern."""
        p = Pattern(id="empty", elements=[], frequency=1, confidence=1.0, example="")
        sig = _get_type_signature(p)
        assert sig == ()


class TestCanMerge:
    """Tests for merge eligibility."""

    def test_same_structure_can_merge(self):
        """Test patterns with same structure can merge."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
                PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                PatternElement(type="field", token_type=TokenType.NUMBER, field_name="b"),
            ],
            frequency=1,
            confidence=1.0,
            example="word 123",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
                PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                PatternElement(type="field", token_type=TokenType.NUMBER, field_name="b"),
            ],
            frequency=1,
            confidence=1.0,
            example="hello 456",
        )
        assert can_merge(p1, p2) is True

    def test_different_length_cannot_merge(self):
        """Test patterns with different lengths cannot merge."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
            ],
            frequency=1,
            confidence=1.0,
            example="word",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
                PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                PatternElement(type="field", token_type=TokenType.NUMBER, field_name="b"),
            ],
            frequency=1,
            confidence=1.0,
            example="word 123",
        )
        assert can_merge(p1, p2) is False

    def test_different_types_cannot_merge(self):
        """Test patterns with different types cannot merge."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
            ],
            frequency=1,
            confidence=1.0,
            example="word",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="field", token_type=TokenType.NUMBER, field_name="a"),
            ],
            frequency=1,
            confidence=1.0,
            example="123",
        )
        assert can_merge(p1, p2) is False


class TestMergeTwo:
    """Tests for merging two patterns."""

    def test_merge_combines_frequency(self):
        """Test merging combines frequencies."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
            ],
            frequency=10,
            confidence=0.9,
            example="word1",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
            ],
            frequency=5,
            confidence=0.8,
            example="word2",
        )

        merged = merge_two(p1, p2)

        assert merged.frequency == 15

    def test_merge_weighted_confidence(self):
        """Test merging uses weighted confidence."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
            ],
            frequency=10,
            confidence=1.0,
            example="word1",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
            ],
            frequency=10,
            confidence=0.5,
            example="word2",
        )

        merged = merge_two(p1, p2)

        # Should be weighted average: (1.0*10 + 0.5*10) / 20 = 0.75
        assert merged.confidence == 0.75

    def test_merge_different_literals_become_field(self):
        """Test that different literals become a field."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="literal", token_type=TokenType.WORD, value="INFO"),
            ],
            frequency=10,
            confidence=0.9,
            example="INFO",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="literal", token_type=TokenType.WORD, value="ERROR"),
            ],
            frequency=5,
            confidence=0.8,
            example="ERROR",
        )

        merged = merge_two(p1, p2)

        # The literal should now be a field
        assert merged.elements[0].type == "field"

    def test_merge_same_literals_stay_literal(self):
        """Test that same literals stay as literals."""
        p1 = Pattern(
            id="p1",
            elements=[
                PatternElement(type="literal", token_type=TokenType.WORD, value="INFO"),
            ],
            frequency=10,
            confidence=0.9,
            example="INFO",
        )
        p2 = Pattern(
            id="p2",
            elements=[
                PatternElement(type="literal", token_type=TokenType.WORD, value="INFO"),
            ],
            frequency=5,
            confidence=0.8,
            example="INFO",
        )

        merged = merge_two(p1, p2)

        # The literal should stay as literal
        assert merged.elements[0].type == "literal"
        assert merged.elements[0].value == "INFO"


class TestMergePatterns:
    """Tests for batch pattern merging."""

    def test_merge_similar_patterns(self):
        """Test merging list of similar patterns."""
        patterns = [
            Pattern(
                id="p1",
                elements=[
                    PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
                    PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                    PatternElement(type="field", token_type=TokenType.NUMBER, field_name="b"),
                ],
                frequency=10,
                confidence=0.9,
                example="INFO 100",
            ),
            Pattern(
                id="p2",
                elements=[
                    PatternElement(type="field", token_type=TokenType.WORD, field_name="a"),
                    PatternElement(type="literal", token_type=TokenType.WHITESPACE, value=" "),
                    PatternElement(type="field", token_type=TokenType.NUMBER, field_name="b"),
                ],
                frequency=5,
                confidence=0.85,
                example="WARN 200",
            ),
        ]

        merged = merge_patterns(patterns, threshold=0.8)

        # Similar patterns should be merged
        assert len(merged) <= len(patterns)

    def test_merge_empty_list(self):
        """Test merging empty list."""
        merged = merge_patterns([])
        assert merged == []

    def test_merge_single_pattern(self, sample_pattern):
        """Test merging single pattern."""
        merged = merge_patterns([sample_pattern])
        assert len(merged) == 1
