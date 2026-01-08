"""JSON Lines output writer."""

from pathlib import Path
from typing import Iterable, TextIO
import orjson

from log_sculptor.core.patterns import ParsedRecord
from log_sculptor.exceptions import OutputError


def write_jsonl(
    records: Iterable[ParsedRecord],
    output: str | Path | TextIO,
    include_raw: bool = False,
    include_unmatched: bool = True,
    include_typed: bool = False,
) -> int:
    count = 0

    def write_to_file(f: TextIO) -> int:
        nonlocal count
        for record in records:
            if not include_unmatched and not record.matched:
                continue

            data = {
                "line_number": record.line_number,
                "pattern_id": record.pattern_id,
                "matched": record.matched,
                "confidence": record.confidence,
                **record.fields,
            }
            if include_raw:
                data["_raw"] = record.raw
            if include_typed and record.typed_fields:
                data["_typed"] = record.typed_fields

            f.write(orjson.dumps(data).decode("utf-8"))
            f.write("\n")
            count += 1
        return count

    try:
        if isinstance(output, (str, Path)):
            with open(output, "w", encoding="utf-8") as f:
                write_to_file(f)
        else:
            write_to_file(output)
    except Exception as e:
        raise OutputError(f"Failed to write JSON Lines output: {e}") from e

    return count
