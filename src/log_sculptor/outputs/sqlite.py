"""SQLite output writer."""

import sqlite3
from pathlib import Path
from typing import Iterable

from log_sculptor.core.patterns import ParsedRecord, PatternSet
from log_sculptor.exceptions import OutputError


def _sanitize_column_name(name: str) -> str:
    sanitized = "".join(c if c.isalnum() else "_" for c in name)
    if sanitized and sanitized[0].isdigit():
        sanitized = "f_" + sanitized
    return sanitized or "field"


def write_sqlite(
    records: Iterable[ParsedRecord],
    output: str | Path,
    patterns: PatternSet | None = None,
    include_raw: bool = True,
    include_typed: bool = True,
) -> int:
    output = Path(output)

    try:
        if output.exists():
            output.unlink()

        conn = sqlite3.connect(output)
        cursor = conn.cursor()

        if patterns:
            cursor.execute("""
                CREATE TABLE patterns (
                    id TEXT PRIMARY KEY, frequency INTEGER, confidence REAL, structure TEXT, example TEXT
                )
            """)
            for pattern in patterns.patterns:
                structure_parts = []
                for elem in pattern.elements:
                    if elem.type == "literal" and elem.token_type and elem.token_type.value == "WHITESPACE":
                        continue
                    elif elem.type == "literal":
                        structure_parts.append(f'"{elem.value}"')
                    else:
                        structure_parts.append(f"<{elem.field_name}:{elem.token_type.value if elem.token_type else '?'}>")
                cursor.execute(
                    "INSERT INTO patterns (id, frequency, confidence, structure, example) VALUES (?, ?, ?, ?, ?)",
                    (pattern.id, pattern.frequency, pattern.confidence, " ".join(structure_parts), pattern.example),
                )

        buffered_records: list[ParsedRecord] = list(records)
        all_field_names: set[str] = set()
        for record in buffered_records:
            if include_typed and record.typed_fields:
                all_field_names.update(record.typed_fields.keys())
            else:
                all_field_names.update(record.fields.keys())

        columns = ["line_number INTEGER PRIMARY KEY", "pattern_id TEXT", "matched INTEGER", "confidence REAL"]
        if include_raw:
            columns.append("raw TEXT")

        field_column_map: dict[str, str] = {}
        for field_name in sorted(all_field_names):
            col_name = _sanitize_column_name(field_name)
            base_col = col_name
            counter = 1
            while col_name in field_column_map.values():
                col_name = f"{base_col}_{counter}"
                counter += 1
            field_column_map[field_name] = col_name
            columns.append(f"{col_name} TEXT")

        cursor.execute(f"CREATE TABLE logs ({', '.join(columns)})")

        count = 0
        for record in buffered_records:
            values = {
                "line_number": record.line_number,
                "pattern_id": record.pattern_id,
                "matched": 1 if record.matched else 0,
                "confidence": record.confidence,
            }
            if include_raw:
                values["raw"] = record.raw

            if include_typed and record.typed_fields:
                for field_name, typed_data in record.typed_fields.items():
                    col_name = field_column_map.get(field_name)
                    if col_name:
                        values[col_name] = str(typed_data["value"]) if typed_data["value"] is not None else None
            else:
                for field_name, value in record.fields.items():
                    col_name = field_column_map.get(field_name)
                    if col_name:
                        values[col_name] = value

            col_names = list(values.keys())
            placeholders = ", ".join("?" for _ in col_names)
            cursor.execute(f"INSERT INTO logs ({', '.join(col_names)}) VALUES ({placeholders})", list(values.values()))
            count += 1

        conn.commit()
        conn.close()
        return count

    except Exception as e:
        raise OutputError(f"Failed to write SQLite output to {output}: {e}") from e
