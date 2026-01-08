"""Multi-line log entry detection and handling."""

from typing import Iterator
import regex

from log_sculptor.types.timestamp import is_likely_timestamp


class ContinuationDetector:
    """Detect if a line continues a previous log entry."""

    def __init__(
        self,
        check_indentation: bool = True,
        check_timestamp: bool = True,
        check_brackets: bool = True,
        check_backslash: bool = True,
    ):
        """
        Initialize detector with enabled strategies.

        Args:
            check_indentation: Treat indented lines as continuations.
            check_timestamp: Lines without timestamps continue previous.
            check_brackets: Track unclosed brackets across lines.
            check_backslash: Backslash at EOL means continuation.
        """
        self.check_indentation = check_indentation
        self.check_timestamp = check_timestamp
        self.check_brackets = check_brackets
        self.check_backslash = check_backslash

        # Bracket tracking state
        self._bracket_depth = 0

    def reset(self) -> None:
        """Reset internal state."""
        self._bracket_depth = 0

    def _count_brackets(self, line: str) -> int:
        """Count net bracket depth change in a line."""
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(line):
            # Track string boundaries
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and (i == 0 or line[i-1] != '\\'):
                    in_string = False
                    string_char = None
                continue

            if in_string:
                continue

            if char in '({[':
                depth += 1
            elif char in ')}]':
                depth -= 1

        return depth

    def _has_timestamp_prefix(self, line: str) -> bool:
        """Check if line starts with something that looks like a timestamp."""
        # Quick check: must start with digit or letter (for month names)
        if not line or not (line[0].isdigit() or line[0].isalpha()):
            return False

        # Extract first "word" (up to first space or common delimiter)
        match = regex.match(r'^[\w\-/:.\[\]]+', line)
        if not match:
            return False

        candidate = match.group(0)
        # Remove brackets if present
        candidate = candidate.strip('[]')

        return is_likely_timestamp(candidate)

    def is_continuation(self, line: str, prev_line: str | None = None) -> bool:
        """
        Check if line continues a previous log entry.

        Args:
            line: Current line to check.
            prev_line: Previous line (used for backslash check).

        Returns:
            True if this line continues the previous entry.
        """
        if not line:
            return False

        # 1. Indentation check (most reliable for stack traces)
        if self.check_indentation:
            if line[0] in ' \t':
                return True

        # 2. Previous line ends with backslash
        if self.check_backslash and prev_line:
            if prev_line.rstrip().endswith('\\'):
                return True

        # 3. Unclosed brackets from previous lines
        if self.check_brackets and self._bracket_depth > 0:
            return True

        # 4. No timestamp at start of line
        if self.check_timestamp:
            if not self._has_timestamp_prefix(line):
                # Only treat as continuation if prev_line exists
                if prev_line is not None:
                    return True

        return False

    def update_state(self, line: str) -> None:
        """Update internal state after processing a line."""
        if self.check_brackets:
            self._bracket_depth += self._count_brackets(line)
            # Clamp to 0 (don't go negative)
            self._bracket_depth = max(0, self._bracket_depth)


class MultilineJoiner:
    """Join multi-line log entries into single records."""

    def __init__(
        self,
        detector: ContinuationDetector | None = None,
        separator: str = "\n",
        max_lines: int = 100,
    ):
        """
        Initialize joiner.

        Args:
            detector: Continuation detector (creates default if None).
            separator: String to join lines with.
            max_lines: Maximum lines to join (safety limit).
        """
        self.detector = detector or ContinuationDetector()
        self.separator = separator
        self.max_lines = max_lines

    def join_lines(self, lines: Iterator[str]) -> Iterator[str]:
        """
        Join multi-line entries into single records.

        Args:
            lines: Iterator of log lines.

        Yields:
            Complete log entries (may contain original newlines as separator).
        """
        self.detector.reset()
        buffer: list[str] = []
        prev_line: str | None = None

        for line in lines:
            line = line.rstrip('\n\r')

            if not buffer:
                # Start new entry
                buffer.append(line)
                self.detector.update_state(line)
                prev_line = line
                continue

            # Check if this line continues the previous entry
            if self.detector.is_continuation(line, prev_line):
                if len(buffer) < self.max_lines:
                    buffer.append(line)
                    self.detector.update_state(line)
                    prev_line = line
                # else: drop line (too many continuations)
            else:
                # Emit completed entry
                yield self.separator.join(buffer)

                # Start new entry
                self.detector.reset()
                buffer = [line]
                self.detector.update_state(line)
                prev_line = line

        # Emit final entry
        if buffer:
            yield self.separator.join(buffer)


def join_multiline(
    lines: Iterator[str],
    separator: str = "\n",
    **detector_kwargs,
) -> Iterator[str]:
    """
    Convenience function to join multi-line log entries.

    Args:
        lines: Iterator of log lines.
        separator: String to join lines with.
        **detector_kwargs: Arguments for ContinuationDetector.

    Yields:
        Complete log entries.
    """
    detector = ContinuationDetector(**detector_kwargs)
    joiner = MultilineJoiner(detector=detector, separator=separator)
    yield from joiner.join_lines(lines)
