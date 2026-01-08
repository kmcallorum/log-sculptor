"""CLI for log-sculptor."""

import sys
from pathlib import Path

import click

from log_sculptor.core.patterns import PatternSet, learn_patterns, parse_logs
from log_sculptor.outputs.jsonl import write_jsonl
from log_sculptor.outputs.sqlite import write_sqlite


FORMAT_CHOICES = ["jsonl", "sqlite", "duckdb", "parquet"]


def _preprocess_lines(logfile: Path, multiline: bool):
    """Preprocess log file lines, optionally joining multi-line entries."""
    if multiline:
        from log_sculptor.parsers.multiline import join_multiline
        with logfile.open("r", errors="replace") as f:
            yield from join_multiline(f)
    else:
        with logfile.open("r", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n\r")


@click.group()
@click.version_option()
def main() -> None:
    """Parse unstructured logs by learning patterns automatically."""
    pass


@main.command()
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path), help="Output patterns file")
@click.option("--sample-size", type=int, default=None, help="Max lines to sample")
@click.option("--min-frequency", type=int, default=1, help="Minimum pattern frequency")
@click.option("--cluster/--no-cluster", default=False, help="Use similarity-based clustering")
@click.option("--cluster-threshold", type=float, default=0.7, help="Clustering similarity threshold")
@click.option("--multiline/--no-multiline", default=False, help="Handle multi-line log entries")
@click.option("--update", type=click.Path(exists=True, path_type=Path), help="Update existing patterns file")
@click.option("--merge-threshold", type=float, default=0.8, help="Similarity threshold for merging patterns")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def learn(logfile: Path, output: Path, sample_size: int | None, min_frequency: int,
          cluster: bool, cluster_threshold: float, multiline: bool, update: Path | None,
          merge_threshold: float, verbose: bool) -> None:
    """Learn patterns from a log file."""
    if verbose:
        click.echo(f"Learning patterns from {logfile}...")

    if multiline:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
            for line in _preprocess_lines(logfile, multiline=True):
                # Collapse multi-line entries into single lines for pattern learning
                collapsed = line.replace("\n", " ").replace("\r", "")
                tmp.write(collapsed + "\n")
            tmp_path = Path(tmp.name)
        patterns = learn_patterns(tmp_path, sample_size=sample_size, min_frequency=min_frequency,
                                 use_clustering=cluster, cluster_threshold=cluster_threshold)
        tmp_path.unlink()
    else:
        patterns = learn_patterns(logfile, sample_size=sample_size, min_frequency=min_frequency,
                                 use_clustering=cluster, cluster_threshold=cluster_threshold)

    if verbose:
        click.echo(f"Found {len(patterns.patterns)} patterns")

    if update:
        existing = PatternSet.load(update)
        if verbose:
            click.echo(f"Updating {len(existing.patterns)} existing patterns...")
        existing.update(patterns, merge=True, threshold=merge_threshold)
        patterns = existing

    patterns.save(output)
    click.echo(f"Learned {len(patterns.patterns)} patterns -> {output}")


@main.command()
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("-p", "--patterns", required=True, type=click.Path(exists=True, path_type=Path), help="Patterns file")
@click.option("-f", "--format", "output_format", type=click.Choice(FORMAT_CHOICES), default="jsonl")
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path), help="Output file")
@click.option("--include-raw", is_flag=True, help="Include raw line")
@click.option("--include-unmatched/--no-include-unmatched", default=True)
@click.option("--multiline/--no-multiline", default=False, help="Handle multi-line log entries")
@click.option("-v", "--verbose", is_flag=True)
def parse(logfile: Path, patterns: Path, output_format: str, output: Path,
          include_raw: bool, include_unmatched: bool, multiline: bool, verbose: bool) -> None:
    """Parse a log file using learned patterns."""
    pattern_set = PatternSet.load(patterns)
    if verbose:
        click.echo(f"Loaded {len(pattern_set.patterns)} patterns, parsing {logfile}...")

    if multiline:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
            for line in _preprocess_lines(logfile, multiline=True):
                collapsed = line.replace("\n", " ").replace("\r", "")
                tmp.write(collapsed + "\n")
            tmp_path = Path(tmp.name)
        records = parse_logs(tmp_path, pattern_set)
    else:
        records = parse_logs(logfile, pattern_set)

    if multiline:
        tmp_path.unlink()

    if output_format == "jsonl":
        count = write_jsonl(records, output, include_raw=include_raw, include_unmatched=include_unmatched)
    elif output_format == "sqlite":
        records_list = list(records)
        if not include_unmatched:
            records_list = [r for r in records_list if r.matched]
        count = write_sqlite(records_list, output, patterns=pattern_set, include_raw=include_raw)
    elif output_format == "duckdb":
        from log_sculptor.outputs import write_duckdb
        records_list = list(records)
        if not include_unmatched:
            records_list = [r for r in records_list if r.matched]
        count = write_duckdb(records_list, output, patterns=pattern_set, include_raw=include_raw)
    elif output_format == "parquet":
        from log_sculptor.outputs import write_parquet
        records_list = list(records)
        if not include_unmatched:
            records_list = [r for r in records_list if r.matched]
        count = write_parquet(records_list, output, patterns=pattern_set, include_raw=include_raw)
    else:
        raise ValueError(f"Unknown output format: {output_format}")

    click.echo(f"Parsed {count} records -> {output}")


@main.command()
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("-f", "--format", "output_format", type=click.Choice(FORMAT_CHOICES), default="jsonl")
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path))
@click.option("--sample-size", type=int, default=None)
@click.option("--include-raw", is_flag=True)
@click.option("--cluster/--no-cluster", default=False)
@click.option("--multiline/--no-multiline", default=False, help="Handle multi-line log entries")
@click.option("-v", "--verbose", is_flag=True)
def auto(logfile: Path, output_format: str, output: Path, sample_size: int | None,
         include_raw: bool, cluster: bool, multiline: bool, verbose: bool) -> None:
    """Learn patterns and parse in one step."""
    if verbose:
        click.echo(f"Learning patterns from {logfile}...")

    if multiline:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
            for line in _preprocess_lines(logfile, multiline=True):
                collapsed = line.replace("\n", " ").replace("\r", "")
                tmp.write(collapsed + "\n")
            tmp_path = Path(tmp.name)
        pattern_set = learn_patterns(tmp_path, sample_size=sample_size, use_clustering=cluster)
        if verbose:
            click.echo(f"Found {len(pattern_set.patterns)} patterns, parsing...")
        records = parse_logs(tmp_path, pattern_set)
    else:
        pattern_set = learn_patterns(logfile, sample_size=sample_size, use_clustering=cluster)
        if verbose:
            click.echo(f"Found {len(pattern_set.patterns)} patterns, parsing...")
        records = parse_logs(logfile, pattern_set)

    if multiline:
        tmp_path.unlink()

    if output_format == "jsonl":
        count = write_jsonl(records, output, include_raw=include_raw)
    elif output_format == "sqlite":
        count = write_sqlite(list(records), output, patterns=pattern_set, include_raw=include_raw)
    elif output_format == "duckdb":
        from log_sculptor.outputs import write_duckdb
        count = write_duckdb(list(records), output, patterns=pattern_set, include_raw=include_raw)
    elif output_format == "parquet":
        from log_sculptor.outputs import write_parquet
        count = write_parquet(list(records), output, patterns=pattern_set, include_raw=include_raw)
    else:
        raise ValueError(f"Unknown output format: {output_format}")

    click.echo(f"Learned {len(pattern_set.patterns)} patterns, parsed {count} records -> {output}")


@main.command()
@click.argument("patterns_file", type=click.Path(exists=True, path_type=Path))
def show(patterns_file: Path) -> None:
    """Display patterns from a patterns file."""
    pattern_set = PatternSet.load(patterns_file)
    click.echo(f"Patterns: {len(pattern_set.patterns)}")
    for i, p in enumerate(pattern_set.patterns, 1):
        click.echo(f"\nPattern {i}: {p.id}")
        click.echo(f"  Frequency: {p.frequency}, Confidence: {p.confidence:.2f}")
        if p.example:
            click.echo(f"  Example: {p.example[:80]}...")


@main.command()
@click.argument("patterns_file", type=click.Path(exists=True, path_type=Path))
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("-v", "--verbose", is_flag=True)
def validate(patterns_file: Path, logfile: Path, verbose: bool) -> None:
    """Validate patterns against a log file."""
    pattern_set = PatternSet.load(patterns_file)
    total, matched = 0, 0
    for record in parse_logs(logfile, pattern_set):
        total += 1
        if record.matched:
            matched += 1
    rate = (matched / total * 100) if total > 0 else 0.0
    click.echo(f"Matched: {matched}/{total} ({rate:.1f}%)")
    sys.exit(0 if matched == total else (1 if matched > 0 else 2))


@main.command()
@click.argument("patterns_file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Output file (defaults to overwrite input)")
@click.option("--threshold", type=float, default=0.8, help="Similarity threshold for merging")
@click.option("-v", "--verbose", is_flag=True)
def merge(patterns_file: Path, output: Path | None, threshold: float, verbose: bool) -> None:
    """Merge similar patterns in a patterns file."""
    pattern_set = PatternSet.load(patterns_file)
    original_count = len(pattern_set.patterns)

    if verbose:
        click.echo(f"Merging patterns with threshold {threshold}...")

    pattern_set.merge_similar(threshold)

    output_path = output or patterns_file
    pattern_set.save(output_path)

    click.echo(f"Merged {original_count} -> {len(pattern_set.patterns)} patterns -> {output_path}")


@main.command()
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("-p", "--patterns", required=True, type=click.Path(exists=True, path_type=Path), help="Patterns file")
@click.option("--window", type=int, default=100, help="Window size for drift detection")
@click.option("-v", "--verbose", is_flag=True)
def drift(logfile: Path, patterns: Path, window: int, verbose: bool) -> None:
    """Detect format changes in a log file."""
    from log_sculptor.core.drift import detect_drift

    pattern_set = PatternSet.load(patterns)
    if verbose:
        click.echo(f"Analyzing {logfile} for format changes...")

    report = detect_drift(logfile, pattern_set, window_size=window)

    click.echo(report.summary())

    if report.has_drift:
        sys.exit(1)
    sys.exit(0)


@main.command()
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path))
@click.option("--workers", type=int, default=4, help="Number of parallel workers")
@click.option("--chunk-size", type=int, default=10000, help="Lines per chunk")
@click.option("-v", "--verbose", is_flag=True)
def fast_learn(logfile: Path, output: Path, workers: int, chunk_size: int, verbose: bool) -> None:
    """Learn patterns using parallel processing (for large files)."""
    from log_sculptor.core.streaming import parallel_learn

    if verbose:
        click.echo(f"Learning patterns from {logfile} using {workers} workers...")

    patterns = parallel_learn(logfile, num_workers=workers, chunk_size=chunk_size)

    if verbose:
        click.echo(f"Found {len(patterns.patterns)} patterns")

    patterns.save(output)
    click.echo(f"Learned {len(patterns.patterns)} patterns -> {output}")


@main.command()
@click.argument("output", type=click.Path(path_type=Path))
@click.option("-t", "--type", "log_type", type=click.Choice(["app", "apache", "syslog", "json", "mixed"]), default="app", help="Log format type")
@click.option("-n", "--count", type=int, default=1000, help="Number of lines to generate")
@click.option("--seed", type=int, default=None, help="Random seed for reproducibility")
def generate(output: Path, log_type: str, count: int, seed: int | None) -> None:
    """Generate sample log data for testing."""
    from log_sculptor.testing.generators import write_sample_logs

    write_sample_logs(output, generator=log_type, count=count, seed=seed)
    click.echo(f"Generated {count} {log_type} log lines -> {output}")


if __name__ == "__main__":
    main()
