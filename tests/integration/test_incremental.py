"""Tests for incremental pattern learning."""
import pytest
from pathlib import Path
from log_sculptor.core.patterns import Pattern, PatternElement, PatternSet, learn_patterns
from log_sculptor.core.tokenizer import TokenType


def make_pattern(elements_spec: list[tuple], pattern_id: str = "test", frequency: int = 1) -> Pattern:
    """Helper to create patterns from element specs."""
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


class TestPatternSetUpdate:
    """Tests for PatternSet.update() method."""

    def test_update_adds_new_patterns(self):
        ps1 = PatternSet()
        ps1.add(make_pattern([("field", "WORD", "msg")], "p1", 5))

        ps2 = PatternSet()
        ps2.add(make_pattern([("field", "NUMBER", "num")], "p2", 3))

        ps1.update(ps2, merge=False)
        assert len(ps1.patterns) == 2

    def test_update_merges_same_id(self):
        ps1 = PatternSet()
        p1 = make_pattern([("field", "WORD", "msg")], "p1", 5)
        p1.confidence = 0.8
        ps1.add(p1)

        ps2 = PatternSet()
        p2 = make_pattern([("field", "WORD", "msg")], "p1", 3)
        p2.confidence = 0.6
        ps2.add(p2)

        ps1.update(ps2, merge=False)
        assert len(ps1.patterns) == 1
        assert ps1.patterns[0].frequency == 8
        # Weighted confidence: (0.8 * 5 + 0.6 * 3) / 8 = 0.725
        assert ps1.patterns[0].confidence == pytest.approx(0.725)

    def test_update_with_merge_combines_similar(self):
        ps1 = PatternSet()
        ps1.add(make_pattern([("literal", "WORD", "INFO"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p1", 5))

        ps2 = PatternSet()
        ps2.add(make_pattern([("literal", "WORD", "WARN"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p2", 3))

        ps1.update(ps2, merge=True, threshold=0.8)
        # Should merge into a single pattern
        assert len(ps1.patterns) == 1
        assert ps1.patterns[0].frequency == 8

    def test_update_sorts_by_frequency(self):
        ps1 = PatternSet()
        ps1.add(make_pattern([("field", "WORD", "a")], "low", 2))
        ps1.add(make_pattern([("field", "NUMBER", "b")], "high", 10))

        ps2 = PatternSet()
        ps2.add(make_pattern([("field", "WORD", "a")], "low", 5))  # Now total 7

        ps1.update(ps2, merge=False)
        # Should be sorted by frequency
        assert ps1.patterns[0].frequency >= ps1.patterns[1].frequency


class TestPatternSetMergeSimilar:
    """Tests for PatternSet.merge_similar() method."""

    def test_merge_similar_in_place(self):
        ps = PatternSet()
        ps.add(make_pattern([("literal", "WORD", "INFO"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p1", 5))
        ps.add(make_pattern([("literal", "WORD", "WARN"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p2", 3))
        ps.add(make_pattern([("literal", "WORD", "ERROR"), ("literal", "WHITESPACE", " "), ("field", "WORD", "m")], "p3", 2))

        ps.merge_similar(threshold=0.8)
        assert len(ps.patterns) == 1
        assert ps.patterns[0].frequency == 10

    def test_merge_similar_preserves_different_structures(self):
        ps = PatternSet()
        ps.add(make_pattern([("field", "WORD", "w")], "p1", 5))
        ps.add(make_pattern([("field", "NUMBER", "n")], "p2", 3))

        ps.merge_similar(threshold=0.8)
        # Different structures should not merge
        assert len(ps.patterns) == 2


class TestIncrementalLearningIntegration:
    """Integration tests for incremental learning workflow."""

    def test_learn_then_update(self, tmp_path: Path):
        # Create first log file
        log1 = tmp_path / "log1.log"
        log1.write_text("2024-01-15 INFO message one\n2024-01-15 INFO message two\n")

        # Learn initial patterns
        ps1 = learn_patterns(log1)
        initial_freq = ps1.patterns[0].frequency if ps1.patterns else 0

        # Create second log file
        log2 = tmp_path / "log2.log"
        log2.write_text("2024-01-15 INFO message three\n")

        # Learn new patterns
        ps2 = learn_patterns(log2)

        # Update original with new
        ps1.update(ps2, merge=True)

        # Frequency should have increased
        assert ps1.patterns[0].frequency >= initial_freq

    def test_save_load_update_cycle(self, tmp_path: Path):
        # Create initial pattern set
        ps = PatternSet()
        ps.add(make_pattern([("field", "WORD", "msg")], "p1", 5))

        # Save
        patterns_file = tmp_path / "patterns.json"
        ps.save(patterns_file)

        # Load
        loaded = PatternSet.load(patterns_file)
        assert len(loaded.patterns) == 1
        assert loaded.patterns[0].frequency == 5

        # Update with new patterns
        ps2 = PatternSet()
        ps2.add(make_pattern([("field", "WORD", "msg")], "p1", 3))
        loaded.update(ps2, merge=False)

        # Save again
        loaded.save(patterns_file)

        # Verify final state
        final = PatternSet.load(patterns_file)
        assert len(final.patterns) == 1
        assert final.patterns[0].frequency == 8
