"""Tests for multi-line log handling."""
from log_sculptor.parsers.multiline import (
    ContinuationDetector,
    MultilineJoiner,
    join_multiline,
)


class TestContinuationDetector:
    """Tests for ContinuationDetector."""

    def test_indented_line_is_continuation(self):
        detector = ContinuationDetector()
        assert detector.is_continuation("    at com.example.Service.process()")
        assert detector.is_continuation("\tat java.lang.Thread.run()")

    def test_non_indented_line_not_continuation(self):
        detector = ContinuationDetector()
        assert not detector.is_continuation("2024-01-15 ERROR Something failed")

    def test_backslash_continuation(self):
        detector = ContinuationDetector(check_indentation=False, check_timestamp=False)
        assert detector.is_continuation("continuation", "first line \\")
        assert not detector.is_continuation("next line", "first line")

    def test_bracket_tracking(self):
        detector = ContinuationDetector(check_indentation=False, check_timestamp=False)
        detector.update_state("start {")
        assert detector.is_continuation("inner line")
        detector.update_state("inner line")
        detector.update_state("}")
        assert not detector.is_continuation("next line")

    def test_no_timestamp_continuation(self):
        detector = ContinuationDetector(check_indentation=False)
        assert detector.is_continuation("Caused by: java.io.IOException", "previous line")
        # Without prev_line, should not be continuation
        assert not detector.is_continuation("Caused by: java.io.IOException", None)

    def test_timestamp_prefix_detection(self):
        detector = ContinuationDetector()
        # Lines starting with timestamps are not continuations
        assert not detector.is_continuation("2024-01-15 INFO message")
        assert not detector.is_continuation("Jan 15 10:23:45 INFO message")

    def test_reset_clears_state(self):
        detector = ContinuationDetector()
        detector.update_state("start {")
        detector.reset()
        # After reset, bracket depth should be 0
        assert detector._bracket_depth == 0


class TestMultilineJoiner:
    """Tests for MultilineJoiner."""

    def test_join_stack_trace(self):
        lines = [
            "2024-01-15 ERROR Failed",
            "java.lang.NullPointerException",
            "    at Service.process()",
            "    at Controller.handle()",
            "2024-01-15 INFO Next entry",
        ]
        joiner = MultilineJoiner()
        result = list(joiner.join_lines(iter(lines)))
        assert len(result) == 2
        assert "at Service.process()" in result[0]
        assert result[1] == "2024-01-15 INFO Next entry"

    def test_join_with_custom_separator(self):
        lines = [
            "2024-01-15 ERROR Failed",
            "    continuation",
            "2024-01-15 INFO Next",
        ]
        joiner = MultilineJoiner(separator=" | ")
        result = list(joiner.join_lines(iter(lines)))
        assert len(result) == 2
        assert " | " in result[0]

    def test_max_lines_limit(self):
        lines = ["first"] + [f"    line{i}" for i in range(150)] + ["next"]
        joiner = MultilineJoiner(max_lines=10)
        result = list(joiner.join_lines(iter(lines)))
        # First entry should be capped at max_lines
        first_parts = result[0].split("\n")
        assert len(first_parts) <= 10

    def test_empty_input(self):
        joiner = MultilineJoiner()
        result = list(joiner.join_lines(iter([])))
        assert result == []


class TestJoinMultiline:
    """Tests for join_multiline convenience function."""

    def test_basic_joining(self):
        lines = [
            "2024-01-15 INFO Start",
            "    continuation",
            "2024-01-15 INFO End",
        ]
        result = list(join_multiline(iter(lines)))
        assert len(result) == 2

    def test_with_custom_options(self):
        lines = [
            "first line \\",
            "continuation",
            "next line",
        ]
        result = list(join_multiline(
            iter(lines),
            check_indentation=False,
            check_timestamp=False,
        ))
        assert len(result) == 2
        assert "first line" in result[0]
        assert "continuation" in result[0]


class TestBracketCounting:
    """Tests for bracket tracking in ContinuationDetector."""

    def test_count_brackets_basic(self):
        detector = ContinuationDetector()
        assert detector._count_brackets("{") == 1
        assert detector._count_brackets("}") == -1
        assert detector._count_brackets("{}") == 0

    def test_count_brackets_nested(self):
        detector = ContinuationDetector()
        assert detector._count_brackets("{[()]}") == 0
        assert detector._count_brackets("{[(") == 3

    def test_count_brackets_ignores_strings(self):
        detector = ContinuationDetector()
        # Brackets inside strings should be ignored
        assert detector._count_brackets('"{}"') == 0
        assert detector._count_brackets("'[]'") == 0

    def test_count_brackets_mixed(self):
        detector = ContinuationDetector()
        assert detector._count_brackets('{"key": "value"}') == 0
        assert detector._count_brackets('{"key": "{nested}"') == 1
