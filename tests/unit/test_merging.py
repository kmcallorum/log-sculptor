"""Tests for pattern merging."""
import pytest
from log_sculptor.core.patterns import Pattern, PatternElement, PatternSet
from log_sculptor.core.tokenizer import TokenType
from log_sculptor.core.merging import (
    can_merge,
    merge_two,
    merge_patterns,
    merge_pattern_set,
)


def make_pattern(elements_spec: list[tuple], pattern_id: str = "test", frequency: int = 1) -> Pattern:
    """Helper to create patterns from element specs.

    Each element spec is (type, token_type, value_or_name).
    """
    elements = []
    for spec in elements_spec:
        elem_type, token_type, value_or_name = spec
        if elem_type == "literal":
            elements.append(PatternElement(
                type="literal",
                value=value_or_name,
                token_type=TokenType(token_type) if token_type else None,
            ))
        else:
            elements.append(PatternElement(
                type="field",
                token_type=TokenType(token_type) if token_type else None,
                field_name=value_or_name,
            ))
    return Pattern(id=pattern_id, elements=elements, frequency=frequency, confidence=1.0)


class TestCanMerge:
    """Tests for can_merge function."""

    def test_identical_patterns_can_merge(self):
        p1 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("literal", "WORD", "INFO"),
        ], "p1")
        p2 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("literal", "WORD", "INFO"),
        ], "p2")
        assert can_merge(p1, p2)

    def test_same_types_different_literals_can_merge(self):
        p1 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("literal", "WORD", "INFO"),
        ], "p1")
        p2 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("literal", "WORD", "ERROR"),
        ], "p2")
        # Same structure (TIMESTAMP, WORD), should be mergeable
        assert can_merge(p1, p2)

    def test_different_lengths_cannot_merge(self):
        p1 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("literal", "WORD", "INFO"),
        ], "p1")
        p2 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("literal", "WORD", "INFO"),
            ("literal", "WHITESPACE", " "),
            ("field", "NUMBER", "count"),
        ], "p2")
        assert not can_merge(p1, p2)

    def test_different_token_types_cannot_merge(self):
        p1 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("field", "NUMBER", "value"),
        ], "p1")
        p2 = make_pattern([
            ("field", "TIMESTAMP", "ts"),
            ("literal", "WHITESPACE", " "),
            ("field", "WORD", "name"),
        ], "p2")
        assert not can_merge(p1, p2)


class TestMergeTwo:
    """Tests for merge_two function."""

    def test_merge_same_literals(self):
        p1 = make_pattern([
            ("literal", "WORD", "INFO"),
            ("literal", "WHITESPACE", " "),
            ("field", "WORD", "msg"),
        ], "p1", frequency=5)
        p2 = make_pattern([
            ("literal", "WORD", "INFO"),
            ("literal", "WHITESPACE", " "),
            ("field", "WORD", "msg"),
        ], "p2", frequency=3)

        merged = merge_two(p1, p2)
        assert merged.frequency == 8
        # First element should remain a literal
        assert merged.elements[0].type == "literal"
        assert merged.elements[0].value == "INFO"

    def test_merge_different_literals_become_fields(self):
        p1 = make_pattern([
            ("literal", "WORD", "INFO"),
            ("literal", "WHITESPACE", " "),
            ("field", "WORD", "msg"),
        ], "p1", frequency=5)
        p2 = make_pattern([
            ("literal", "WORD", "ERROR"),
            ("literal", "WHITESPACE", " "),
            ("field", "WORD", "msg"),
        ], "p2", frequency=3)

        merged = merge_two(p1, p2)
        # Different literals should become a field
        assert merged.elements[0].type == "field"
        assert merged.elements[0].token_type == TokenType.WORD

    def test_merge_preserves_weighted_confidence(self):
        p1 = make_pattern([("field", "WORD", "msg")], "p1", frequency=10)
        p1.confidence = 0.9
        p2 = make_pattern([("field", "WORD", "msg")], "p2", frequency=10)
        p2.confidence = 0.7

        merged = merge_two(p1, p2)
        # Weighted average: (0.9 * 10 + 0.7 * 10) / 20 = 0.8
        assert merged.confidence == pytest.approx(0.8)


class TestMergePatterns:
    """Tests for merge_patterns function."""

    def test_merge_similar_patterns(self):
        patterns = [
            make_pattern([("literal", "WORD", "INFO"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p1", 5),
            make_pattern([("literal", "WORD", "WARN"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p2", 3),
            make_pattern([("literal", "WORD", "ERROR"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p3", 2),
        ]

        result = merge_patterns(patterns)
        # All three should merge into one since they have same token type signature
        assert len(result) == 1
        assert result[0].frequency == 10

    def test_no_merge_different_structures(self):
        patterns = [
            make_pattern([("literal", "WORD", "INFO"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p1"),
            make_pattern([("field", "TIMESTAMP", "ts"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p2"),
        ]

        result = merge_patterns(patterns)
        # Different structures should not merge
        assert len(result) == 2

    def test_single_pattern_unchanged(self):
        patterns = [make_pattern([("field", "WORD", "msg")], "p1", 5)]
        result = merge_patterns(patterns)
        assert len(result) == 1
        assert result[0].frequency == 5

    def test_empty_list(self):
        result = merge_patterns([])
        assert result == []


class TestMergePatternSet:
    """Tests for merge_pattern_set function."""

    def test_merge_pattern_set(self):
        ps = PatternSet()
        ps.add(make_pattern([("literal", "WORD", "INFO"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p1", 5))
        ps.add(make_pattern([("literal", "WORD", "WARN"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p2", 3))

        merged_ps = merge_pattern_set(ps)
        assert len(merged_ps.patterns) == 1
        assert merged_ps.patterns[0].frequency == 8

    def test_merged_set_sorted_by_frequency(self):
        ps = PatternSet()
        ps.add(make_pattern([("field", "NUMBER", "n")], "p1", 2))
        ps.add(make_pattern([("field", "WORD", "w")], "p2", 10))

        merged_ps = merge_pattern_set(ps)
        # Should be sorted by frequency descending
        assert merged_ps.patterns[0].frequency >= merged_ps.patterns[-1].frequency
