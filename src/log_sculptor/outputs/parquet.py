"""Parquet output writer (optional dependency)."""

from pathlib import Path
from typing import Iterable

from log_sculptor.core.patterns import ParsedRecord, PatternSet
from log_sculptor.exceptions import OutputError


def _sanitize_column_name(name: str) -> str:
    sanitized = "".join(c if c.isalnum() else "_" for c in name)
    if sanitized and sanitized[0].isdigit():
        sanitized = "f_" + sanitized
    return sanitized or "field"


def write_parquet(
    records: Iterable[ParsedRecord],
    output: str | Path,
    patterns: PatternSet | None = None,
    include_raw: bool = True,
    include_typed: bool = True,
) -> int:
    """
    Write parsed records to a Parquet file.

    Requires pyarrow package: pip install log-sculptor[parquet]

    Args:
        records: Parsed log records to write.
        output: Output file path.
        patterns: Optional PatternSet (written to separate _patterns.parquet file).
        include_raw: Include raw log line in output.
        include_typed: Use typed field values.

    Returns:
        Number of records written.

    Raises:
        OutputError: If pyarrow is not installed or write fails.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise OutputError(
            "Parquet output requires the pyarrow package. "
            "Install with: pip install log-sculptor[parquet]"
        )

    output = Path(output)

    try:
        buffered_records: list[ParsedRecord] = list(records)

        if not buffered_records:
            return 0

        all_field_names: set[str] = set()
        for record in buffered_records:
            if include_typed and record.typed_fields:
                all_field_names.update(record.typed_fields.keys())
            else:
                all_field_names.update(record.fields.keys())

        field_column_map: dict[str, str] = {}
        for field_name in sorted(all_field_names):
            col_name = _sanitize_column_name(field_name)
            base_col = col_name
            counter = 1
            while col_name in field_column_map.values():
                col_name = f"{base_col}_{counter}"
                counter += 1
            field_column_map[field_name] = col_name

        data: dict[str, list] = {
            "line_number": [],
            "pattern_id": [],
            "matched": [],
            "confidence": [],
        }
        if include_raw:
            data["raw"] = []

        for col_name in field_column_map.values():
            data[col_name] = []

        for record in buffered_records:
            data["line_number"].append(record.line_number)
            data["pattern_id"].append(record.pattern_id)
            data["matched"].append(record.matched)
            data["confidence"].append(record.confidence)

            if include_raw:
                data["raw"].append(record.raw)

            record_fields: dict[str, str | None] = {}
            if include_typed and record.typed_fields:
                for field_name, typed_data in record.typed_fields.items():
                    record_fields[field_name] = str(typed_data["value"]) if typed_data["value"] is not None else None
            else:
                record_fields = dict(record.fields)

            for field_name, col_name in field_column_map.items():
                data[col_name].append(record_fields.get(field_name))

        table = pa.table(data)
        pq.write_table(table, output)

        if patterns:
            patterns_data = {
                "id": [],
                "frequency": [],
                "confidence": [],
                "structure": [],
                "example": [],
            }
            for pattern in patterns.patterns:
                structure_parts = []
                for elem in pattern.elements:
                    if elem.type == "literal" and elem.token_type and elem.token_type.value == "WHITESPACE":
                        continue
                    elif elem.type == "literal":
                        structure_parts.append(f'"{elem.value}"')
                    else:
                        structure_parts.append(f"<{elem.field_name}:{elem.token_type.value if elem.token_type else '?'}>")

                patterns_data["id"].append(pattern.id)
                patterns_data["frequency"].append(pattern.frequency)
                patterns_data["confidence"].append(pattern.confidence)
                patterns_data["structure"].append(" ".join(structure_parts))
                patterns_data["example"].append(pattern.example)

            patterns_table = pa.table(patterns_data)
            patterns_output = output.with_stem(output.stem + "_patterns")
            pq.write_table(patterns_table, patterns_output)

        return len(buffered_records)

    except Exception as e:
        if "pyarrow" in str(type(e).__module__):
            raise OutputError(f"Failed to write Parquet output to {output}: {e}") from e
        raise
