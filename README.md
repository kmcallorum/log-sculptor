# log-sculptor

Parse unstructured logs by learning patterns automatically. No regex required.

## Features

- **Automatic pattern learning** - Analyzes log files and learns structural patterns
- **Smart field naming** - Infers meaningful field names from context (method, status, path, etc.)
- **Type detection** - Automatically detects timestamps, IPs, URLs, UUIDs, numbers, booleans
- **Multi-line support** - Handles stack traces and continuation lines
- **Format drift detection** - Detects when log formats change mid-file
- **Multiple outputs** - JSON Lines, SQLite, DuckDB, Parquet
- **Performance optimized** - Streaming processing and parallel learning for large files

## Installation

```bash
pip install log-sculptor

# With optional outputs
pip install log-sculptor[duckdb]    # DuckDB support
pip install log-sculptor[parquet]   # Parquet support
pip install log-sculptor[all]       # All optional dependencies
```

## Quick Start

```bash
# Learn and parse in one step
log-sculptor auto server.log -f jsonl -o parsed.jsonl

# Or separate steps for reuse
log-sculptor learn server.log -o patterns.json
log-sculptor parse server.log -p patterns.json -f jsonl -o parsed.jsonl
```

## CLI Commands

### auto
Learn patterns and parse in one step.
```bash
log-sculptor auto server.log -f jsonl -o output.jsonl
log-sculptor auto server.log -f sqlite -o logs.db
log-sculptor auto server.log -f duckdb -o logs.duckdb  # requires [duckdb]
log-sculptor auto server.log -f parquet -o logs.parquet  # requires [parquet]

# With multi-line support (stack traces, continuations)
log-sculptor auto server.log --multiline -f jsonl -o output.jsonl
```

### learn
Learn patterns from a log file.
```bash
log-sculptor learn server.log -o patterns.json

# With clustering for similar patterns
log-sculptor learn server.log -o patterns.json --cluster

# Incremental learning (update existing patterns)
log-sculptor learn new.log --update patterns.json -o patterns.json

# Handle multi-line entries
log-sculptor learn server.log -o patterns.json --multiline
```

### parse
Parse a log file using learned patterns.
```bash
log-sculptor parse server.log -p patterns.json -f jsonl -o output.jsonl
log-sculptor parse server.log -p patterns.json -f sqlite -o logs.db --include-raw
```

### show
Display patterns from a patterns file.
```bash
log-sculptor show patterns.json
```

### validate
Validate patterns against a log file.
```bash
log-sculptor validate patterns.json server.log
# Exit codes: 0 = all matched, 1 = partial match, 2 = no matches
```

### merge
Merge similar patterns in a patterns file.
```bash
log-sculptor merge patterns.json -o merged.json --threshold 0.8
```

### drift
Detect format changes in a log file.
```bash
log-sculptor drift server.log -p patterns.json
log-sculptor drift server.log -p patterns.json --window 50
```

### fast-learn
Learn patterns using parallel processing (for large files).
```bash
log-sculptor fast-learn large.log -o patterns.json --workers 4
```

## Output Formats

### JSON Lines (jsonl)
```json
{"line_number": 1, "pattern_id": "a1b2c3", "matched": true, "fields": {"timestamp": "2024-01-15T10:30:00", "level": "INFO", "message": "Server started"}}
```

### SQLite
Creates two tables:
- `patterns` - Pattern metadata (id, frequency, confidence, structure, example)
- `logs` - Parsed records with extracted fields as columns

### DuckDB
Same schema as SQLite, optimized for analytical queries. Requires `pip install log-sculptor[duckdb]`.

### Parquet
Columnar format for efficient analytics. Creates `output.parquet` for logs and `output_patterns.parquet` for patterns. Requires `pip install log-sculptor[parquet]`.

## Python API

```python
from log_sculptor.core import learn_patterns, parse_logs, PatternSet

# Learn patterns
patterns = learn_patterns("server.log")
patterns.save("patterns.json")

# Parse logs
for record in parse_logs("server.log", patterns):
    print(record.fields)

# Load existing patterns
patterns = PatternSet.load("patterns.json")

# Incremental learning
new_patterns = learn_patterns("new_logs.log")
patterns.update(new_patterns, merge=True)

# Merge similar patterns
patterns.merge_similar(threshold=0.8)
```

### Streaming for Large Files

```python
from log_sculptor.core.streaming import stream_parse, parallel_learn

# Memory-efficient parsing
for record in stream_parse("large.log", patterns):
    process(record)

# Parallel pattern learning
patterns = parallel_learn("large.log", num_workers=4)
```

### Format Drift Detection

```python
from log_sculptor.core import detect_drift

report = detect_drift("server.log", patterns)
print(f"Format changes: {len(report.format_changes)}")
for change in report.format_changes:
    print(f"  Line {change.line_number}: {change.old_pattern_id} -> {change.new_pattern_id}")
```

## How It Works

1. **Tokenization** - Lines are split into typed tokens (TIMESTAMP, IP, QUOTED, BRACKET, NUMBER, WORD, PUNCT, WHITESPACE)

2. **Clustering** - Lines with identical token signatures are grouped together

3. **Pattern Generation** - Each cluster becomes a pattern with fields for variable tokens

4. **Smart Naming** - Field names are inferred from context:
   - Previous token as indicator ("status 200" -> field named "status")
   - Value patterns (GET/POST -> "method", 404 -> "status", /api/users -> "path")
   - Token types (timestamps, IPs, UUIDs get appropriate names)

5. **Type Detection** - Field values are typed:
   - Timestamps (ISO 8601, Apache CLF, syslog, Unix epoch)
   - IPs, URLs, UUIDs
   - Integers, floats, booleans

## License

MIT
