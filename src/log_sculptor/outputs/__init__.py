"""Output writers for log-sculptor."""

from log_sculptor.outputs.jsonl import write_jsonl
from log_sculptor.outputs.sqlite import write_sqlite

__all__ = ["write_jsonl", "write_sqlite"]


def write_duckdb(*args, **kwargs):
    """Write to DuckDB (lazy import to avoid dependency issues)."""
    from log_sculptor.outputs.duckdb import write_duckdb as _write_duckdb
    return _write_duckdb(*args, **kwargs)


def write_parquet(*args, **kwargs):
    """Write to Parquet (lazy import to avoid dependency issues)."""
    from log_sculptor.outputs.parquet import write_parquet as _write_parquet
    return _write_parquet(*args, **kwargs)
