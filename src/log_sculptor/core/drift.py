"""Format change (drift) detection for log files."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from collections import defaultdict

from log_sculptor.core.patterns import PatternSet, parse_logs, ParsedRecord


@dataclass
class FormatChange:
    """Represents a detected format change in the log file."""
    line_number: int
    old_pattern_id: str | None
    new_pattern_id: str | None
    confidence: float
    context_before: str | None = None
    context_after: str | None = None


@dataclass
class DriftReport:
    """Report of format changes detected in a log file."""
    total_lines: int
    matched_lines: int
    pattern_distribution: dict[str, int]
    format_changes: list[FormatChange]
    dominant_patterns: list[tuple[int, int, str]]  # (start_line, end_line, pattern_id)

    @property
    def match_rate(self) -> float:
        return self.matched_lines / self.total_lines if self.total_lines > 0 else 0.0

    @property
    def has_drift(self) -> bool:
        return len(self.format_changes) > 0

    def summary(self) -> str:
        lines = [
            f"Lines: {self.total_lines} ({self.match_rate:.1%} matched)",
            f"Patterns: {len(self.pattern_distribution)}",
            f"Format changes: {len(self.format_changes)}",
        ]
        if self.format_changes:
            lines.append("\nFormat changes detected at:")
            for change in self.format_changes[:5]:  # Show first 5
                lines.append(f"  Line {change.line_number}: {change.old_pattern_id} -> {change.new_pattern_id}")
            if len(self.format_changes) > 5:
                lines.append(f"  ... and {len(self.format_changes) - 5} more")
        return "\n".join(lines)


class DriftDetector:
    """Detect format changes in log files."""

    def __init__(
        self,
        window_size: int = 100,
        change_threshold: float = 0.5,
        min_confidence: float = 0.3,
    ):
        """
        Initialize drift detector.

        Args:
            window_size: Number of lines to consider for pattern dominance.
            change_threshold: Fraction of window that must change for detection.
            min_confidence: Minimum confidence to consider a line matched.
        """
        self.window_size = window_size
        self.change_threshold = change_threshold
        self.min_confidence = min_confidence

    def _get_dominant_pattern(self, window: list[str | None]) -> str | None:
        """Get the most common pattern in a window."""
        if not window:
            return None
        counts: dict[str | None, int] = defaultdict(int)
        for p in window:
            counts[p] += 1
        return max(counts.keys(), key=lambda k: counts[k])

    def detect(
        self,
        source: str | Path,
        patterns: PatternSet,
    ) -> DriftReport:
        """
        Detect format changes in a log file.

        Args:
            source: Path to log file.
            patterns: PatternSet to use for matching.

        Returns:
            DriftReport with detected changes.
        """
        source = Path(source)

        # Collect all records
        records = list(parse_logs(source, patterns))

        total_lines = len(records)
        matched_lines = sum(1 for r in records if r.matched)

        # Count pattern distribution
        pattern_dist: dict[str, int] = defaultdict(int)
        for r in records:
            if r.pattern_id:
                pattern_dist[r.pattern_id] += 1

        # Detect format changes using sliding window
        format_changes: list[FormatChange] = []
        dominant_patterns: list[tuple[int, int, str]] = []

        if total_lines == 0:
            return DriftReport(
                total_lines=0,
                matched_lines=0,
                pattern_distribution=dict(pattern_dist),
                format_changes=[],
                dominant_patterns=[],
            )

        # Build pattern sequence
        pattern_seq = [r.pattern_id for r in records]

        # Track dominant pattern regions
        current_dominant: str | None = None
        region_start = 1

        for i in range(total_lines):
            # Get window around current position
            window_start = max(0, i - self.window_size // 2)
            window_end = min(total_lines, i + self.window_size // 2)
            window = pattern_seq[window_start:window_end]

            dominant = self._get_dominant_pattern(window)

            if dominant != current_dominant and dominant is not None:
                if current_dominant is not None:
                    # Record the completed region
                    dominant_patterns.append((region_start, i, current_dominant))

                    # Detect format change
                    context_before = records[i - 1].raw if i > 0 else None
                    context_after = records[i].raw if i < total_lines else None

                    # Calculate confidence based on how dominant the new pattern is
                    new_count = sum(1 for p in window if p == dominant)
                    confidence = new_count / len(window) if window else 0

                    if confidence >= self.min_confidence:
                        format_changes.append(FormatChange(
                            line_number=i + 1,  # 1-indexed
                            old_pattern_id=current_dominant,
                            new_pattern_id=dominant,
                            confidence=confidence,
                            context_before=context_before,
                            context_after=context_after,
                        ))

                current_dominant = dominant
                region_start = i + 1

        # Record final region
        if current_dominant is not None:
            dominant_patterns.append((region_start, total_lines, current_dominant))

        return DriftReport(
            total_lines=total_lines,
            matched_lines=matched_lines,
            pattern_distribution=dict(pattern_dist),
            format_changes=format_changes,
            dominant_patterns=dominant_patterns,
        )


def detect_drift(
    source: str | Path,
    patterns: PatternSet,
    window_size: int = 100,
    change_threshold: float = 0.5,
) -> DriftReport:
    """
    Convenience function to detect format drift.

    Args:
        source: Path to log file.
        patterns: PatternSet to use.
        window_size: Lines to consider for dominance.
        change_threshold: Change fraction threshold.

    Returns:
        DriftReport with analysis results.
    """
    detector = DriftDetector(window_size=window_size, change_threshold=change_threshold)
    return detector.detect(source, patterns)
