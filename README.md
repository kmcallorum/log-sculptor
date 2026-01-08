# log-sculptor

Parse unstructured logs by learning patterns automatically.

## Installation

```bash
pip install log-sculptor
```

## Quick Start

```bash
# Learn patterns from a log file
log-sculptor learn server.log -o patterns.json

# Parse using learned patterns
log-sculptor parse server.log -p patterns.json -f jsonl -o parsed.jsonl

# Or do both in one step
log-sculptor auto server.log -f jsonl -o parsed.jsonl

# Output to SQLite
log-sculptor auto server.log -f sqlite -o logs.db
```

## License

MIT
