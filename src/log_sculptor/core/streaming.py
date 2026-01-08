"""Streaming and performance optimizations for large log files."""

import mmap
from pathlib import Path
from typing import Iterator, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from log_sculptor.core.tokenizer import tokenize
from log_sculptor.core.patterns import PatternSet, ParsedRecord, Pattern


@dataclass
class ChunkResult:
    """Result from processing a chunk of lines."""
    records: list[ParsedRecord]
    line_offset: int


def _read_lines_mmap(path: Path, encoding: str = "utf-8") -> Iterator[str]:
    """Read lines using memory-mapped file for better performance on large files."""
    with open(path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for line in iter(mm.readline, b""):
                try:
                    yield line.decode(encoding).rstrip("\r\n")
                except UnicodeDecodeError:
                    yield line.decode(encoding, errors="replace").rstrip("\r\n")


def stream_parse(
    source: str | Path,
    patterns: PatternSet,
    chunk_size: int = 10000,
    use_mmap: bool = True,
    detect_types: bool = True,
    callback: Callable[[ParsedRecord], None] | None = None,
) -> Iterator[ParsedRecord]:
    """
    Stream-parse a log file with configurable chunk size.

    More memory-efficient than loading all records at once.

    Args:
        source: Path to log file.
        patterns: PatternSet for matching.
        chunk_size: Number of lines to buffer before yielding.
        use_mmap: Use memory-mapped file reading.
        detect_types: Whether to detect field types.
        callback: Optional callback for each record (for progress reporting).

    Yields:
        ParsedRecord for each line.
    """
    from log_sculptor.types.detector import detect_type

    source = Path(source)

    if use_mmap and source.stat().st_size > 1024 * 1024:  # > 1MB
        lines = _read_lines_mmap(source)
    else:
        f = source.open("r", errors="replace")
        lines = (line.rstrip("\r\n") for line in f)

    for i, line in enumerate(lines, start=1):
        if not line:
            continue

        pattern, fields = patterns.match(line)
        confidence = pattern.confidence if pattern else 0.0

        typed_fields = None
        if detect_types and fields:
            typed_fields = {}
            for name, value in fields.items():
                typed = detect_type(value)
                typed_fields[name] = {"value": typed.normalized, "type": typed.type.value}

        record = ParsedRecord(
            line_number=i,
            raw=line,
            fields=fields or {},
            pattern_id=pattern.id if pattern else None,
            matched=pattern is not None,
            confidence=confidence,
            typed_fields=typed_fields,
        )

        if callback:
            callback(record)

        yield record


class PatternCache:
    """Cache for faster pattern matching using signature lookup."""

    def __init__(self, patterns: PatternSet):
        self.patterns = patterns
        self._sig_to_patterns: dict[str, list[Pattern]] = {}
        self._build_cache()

    def _build_cache(self) -> None:
        """Build signature-based lookup cache."""
        for pattern in self.patterns.patterns:
            # Create a simplified signature for quick filtering
            sig_parts = []
            for elem in pattern.elements:
                if elem.type == "literal" and elem.token_type and elem.token_type.value != "WHITESPACE":
                    sig_parts.append(f"L:{elem.value}")
                elif elem.type == "field" and elem.token_type:
                    sig_parts.append(f"F:{elem.token_type.value}")
            sig = "|".join(sig_parts)

            if sig not in self._sig_to_patterns:
                self._sig_to_patterns[sig] = []
            self._sig_to_patterns[sig].append(pattern)

    def match(self, line: str) -> tuple[Pattern | None, dict | None]:
        """Match a line using cached patterns."""
        tokens = tokenize(line)

        # Try direct match first (most common case)
        for pattern in self.patterns.patterns:
            fields = pattern.match(tokens)
            if fields is not None:
                return pattern, fields

        return None, None


def parallel_learn(
    source: str | Path,
    sample_size: int | None = None,
    num_workers: int = 4,
    chunk_size: int = 10000,
) -> PatternSet:
    """
    Learn patterns using parallel processing.

    Splits file into chunks, processes in parallel, then merges results.

    Args:
        source: Path to log file.
        sample_size: Max lines to process.
        num_workers: Number of parallel workers.
        chunk_size: Lines per chunk.

    Returns:
        Merged PatternSet from all chunks.
    """
    from log_sculptor.core.patterns import learn_patterns
    from log_sculptor.core.clustering import cluster_by_exact_signature

    source = Path(source)

    # Read all lines (or sample)
    lines: list[str] = []
    with source.open("r", errors="replace") as f:
        for i, line in enumerate(f):
            if sample_size and i >= sample_size:
                break
            line = line.rstrip("\r\n")
            if line:
                lines.append(line)

    if len(lines) < chunk_size * 2:
        # File is small enough for single-threaded processing
        return learn_patterns(source, sample_size=sample_size)

    # Split into chunks
    chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]

    def process_chunk(chunk_lines: list[str]) -> PatternSet:
        """Process a single chunk."""
        from log_sculptor.core.patterns import _pattern_from_tokens
        from log_sculptor.core.tokenizer import tokenize

        # Tokenize and cluster
        tokenized = [(tokenize(line), line) for line in chunk_lines]
        clusters = cluster_by_exact_signature(tokenized)

        # Build pattern set
        ps = PatternSet()
        for cluster in clusters:
            tokens, line = cluster.members[0]
            pattern = _pattern_from_tokens(tokens, line)
            pattern.frequency = len(cluster.members)
            pattern.confidence = cluster.cohesion
            ps.add(pattern)

        return ps

    # Process chunks in parallel
    pattern_sets: list[PatternSet] = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            pattern_sets.append(future.result())

    # Merge all pattern sets
    if not pattern_sets:
        return PatternSet()

    merged = pattern_sets[0]
    for ps in pattern_sets[1:]:
        merged.update(ps, merge=True)

    return merged
