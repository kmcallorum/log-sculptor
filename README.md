# log-sculptor

[![CI](https://github.com/kmcallorum/log-sculptor/actions/workflows/ci.yml/badge.svg)](https://github.com/kmcallorum/log-sculptor/actions/workflows/ci.yml)
[![CodeQL](https://github.com/kmcallorum/log-sculptor/actions/workflows/codeql.yml/badge.svg)](https://github.com/kmcallorum/log-sculptor/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/kmcallorum/log-sculptor/branch/main/graph/badge.svg)](https://codecov.io/gh/kmcallorum/log-sculptor)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Parse unstructured logs by learning patterns automatically. No regex required.

## Features

- **Automatic pattern learning** - Analyzes log files and learns structural patterns
- **Smart field naming** - Infers meaningful field names from context (method, status, path, etc.)
- **Type detection** - Automatically detects timestamps, IPs, URLs, UUIDs, numbers, booleans
- **Multi-line support** - Handles stack traces and continuation lines
- **Format drift detection** - Detects when log formats change mid-file
- **Multiple outputs** - JSON Lines, SQLite, DuckDB, Parquet
- **Performance optimized** - Streaming processing and parallel learning for large files
- **Testing utilities** - Mocks, fixtures, and sample data generators for reliable integrations

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

### generate
Generate sample log data for testing and demos.
```bash
log-sculptor generate sample.log -t app -n 1000
log-sculptor generate apache.log -t apache -n 500 --seed 42
log-sculptor generate mixed.log -t mixed -n 1000  # For drift testing
```

Available types: `app`, `apache`, `syslog`, `json`, `mixed`

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

## Testing Utilities

log-sculptor includes comprehensive testing utilities for building reliable integrations.

### Sample Data Generation

```python
from log_sculptor.testing import (
    generate_apache_logs,
    generate_syslog,
    generate_json_logs,
    generate_app_logs,
    write_sample_logs,
)

# Generate Apache logs
for line in generate_apache_logs(count=100, seed=42):
    print(line)

# Generate JSON structured logs
for line in generate_json_logs(count=50):
    print(line)

# Write directly to file
write_sample_logs("test.log", generator="app", count=1000, seed=42)
```

### Mock Objects

```python
from log_sculptor.testing import (
    MockFileReader,
    MockFileWriter,
    MockPatternMatcher,
    MockTypeDetector,
)

# Mock file reader
reader = MockFileReader()
reader.add_file("/test.log", ["line1", "line2", "line3"])
lines = reader.read_lines(Path("/test.log"))
assert reader.read_count == 1

# Mock pattern matcher with custom responses
matcher = MockPatternMatcher()
matcher.add_response("GET /api", MockPattern(id="http"), {"method": "GET"})
pattern, fields = matcher.match("GET /api")
```

### Test Fixtures

```python
from log_sculptor.testing import (
    create_test_patterns,
    create_test_log_file,
    SandboxContext,
    isolated_test,
)

# Create test patterns
patterns = create_test_patterns(count=3, with_examples=True)

# Create test log file
create_test_log_file(Path("test.log"), generator="apache", count=100)

# Isolated test environment with mocks
with isolated_test() as ctx:
    log_file = ctx.create_log_file("test.log", generator="app", count=50)
    ctx.add_mock_file("/virtual.log", ["mock line 1", "mock line 2"])
    # Tests run in isolation, temp files cleaned up automatically
```

### Dependency Injection

```python
from log_sculptor import get_container, register, resolve, reset_container
from log_sculptor.di import FileReader, FileWriter

# Register custom implementations
class MyFileReader:
    def read_lines(self, path):
        # Custom implementation
        pass

register(FileReader, lambda: MyFileReader())
reader = resolve(FileReader)

# Reset for test isolation
reset_container()
```

## License

MIT
