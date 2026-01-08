"""log-sculptor: Parse unstructured logs by learning patterns automatically."""

from log_sculptor.core.tokenizer import Token, tokenize
from log_sculptor.core.patterns import Pattern, PatternElement, PatternSet, ParsedRecord, learn_patterns, parse_logs
from log_sculptor.core.clustering import Cluster, cluster_lines
from log_sculptor.types.detector import TypedValue, detect_type, FieldType
from log_sculptor.outputs.jsonl import write_jsonl
from log_sculptor.outputs.sqlite import write_sqlite

__version__ = "0.1.0"

__all__ = [
    "Token",
    "tokenize",
    "Pattern",
    "PatternElement",
    "PatternSet",
    "ParsedRecord",
    "learn_patterns",
    "parse_logs",
    "Cluster",
    "cluster_lines",
    "TypedValue",
    "detect_type",
    "FieldType",
    "write_jsonl",
    "write_sqlite",
]
