"""Pattern representation, learning, and matching."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Any
import hashlib
import orjson

from log_sculptor.core.tokenizer import Token, TokenType, tokenize, token_signature
from log_sculptor.exceptions import PatternLoadError, PatternSaveError


@dataclass
class PatternElement:
    """A single element in a pattern (literal or field)."""
    type: Literal["literal", "field"]
    value: str | None = None
    token_type: TokenType | None = None
    field_name: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "token_type": self.token_type.value if self.token_type else None,
            "field_name": self.field_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternElement":
        return cls(
            type=data["type"],
            value=data.get("value"),
            token_type=TokenType(data["token_type"]) if data.get("token_type") else None,
            field_name=data.get("field_name"),
        )


@dataclass
class Pattern:
    """A pattern for matching log lines."""
    id: str
    elements: list[PatternElement]
    frequency: int = 0
    confidence: float = 1.0
    example: str | None = None

    def match(self, tokens: list[Token]) -> dict | None:
        non_ws_tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        non_ws_elements = [e for e in self.elements if not (e.type == "literal" and e.token_type == TokenType.WHITESPACE)]

        if len(non_ws_tokens) != len(non_ws_elements):
            return None

        fields: dict[str, str] = {}
        for token, element in zip(non_ws_tokens, non_ws_elements):
            if element.type == "literal":
                if token.value != element.value:
                    return None
            else:
                if element.token_type and token.type != element.token_type:
                    return None
                if element.field_name:
                    fields[element.field_name] = token.value

        return fields

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "elements": [e.to_dict() for e in self.elements],
            "frequency": self.frequency,
            "confidence": self.confidence,
            "example": self.example,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        return cls(
            id=data["id"],
            elements=[PatternElement.from_dict(e) for e in data["elements"]],
            frequency=data.get("frequency", 0),
            confidence=data.get("confidence", 1.0),
            example=data.get("example"),
        )


@dataclass
class PatternSet:
    """Collection of patterns for parsing logs."""
    patterns: list[Pattern] = field(default_factory=list)
    version: str = "1.0"

    def add(self, pattern: Pattern) -> None:
        self.patterns.append(pattern)

    def match(self, line: str) -> tuple[Pattern | None, dict | None]:
        tokens = tokenize(line)
        for pattern in self.patterns:
            fields = pattern.match(tokens)
            if fields is not None:
                return pattern, fields
        return None, None

    def save(self, path: str | Path) -> None:
        path = Path(path)
        data = {"version": self.version, "patterns": [p.to_dict() for p in self.patterns]}
        try:
            path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
        except Exception as e:
            raise PatternSaveError(f"Failed to save patterns to {path}: {e}") from e

    @classmethod
    def load(cls, path: str | Path) -> "PatternSet":
        path = Path(path)
        try:
            data = orjson.loads(path.read_bytes())
            return cls(version=data.get("version", "1.0"), patterns=[Pattern.from_dict(p) for p in data["patterns"]])
        except Exception as e:
            raise PatternLoadError(f"Failed to load patterns from {path}: {e}") from e

    def update(self, new_patterns: "PatternSet", merge: bool = True, threshold: float = 0.8) -> None:
        """
        Incrementally update patterns with new observations.

        Args:
            new_patterns: New patterns to incorporate.
            merge: Whether to merge similar patterns after update.
            threshold: Similarity threshold for merging.
        """
        # Add new patterns, merging frequencies for matching IDs
        existing_ids = {p.id: i for i, p in enumerate(self.patterns)}

        for new_p in new_patterns.patterns:
            if new_p.id in existing_ids:
                # Update existing pattern
                idx = existing_ids[new_p.id]
                old_p = self.patterns[idx]
                old_freq = old_p.frequency
                new_freq = new_p.frequency
                total_freq = old_freq + new_freq

                # Weighted average confidence
                old_p.frequency = total_freq
                old_p.confidence = (old_p.confidence * old_freq + new_p.confidence * new_freq) / total_freq
            else:
                # Add new pattern
                self.patterns.append(new_p)
                existing_ids[new_p.id] = len(self.patterns) - 1

        # Optionally merge similar patterns
        if merge:
            self.merge_similar(threshold)

        # Re-sort by frequency
        self.patterns.sort(key=lambda p: p.frequency, reverse=True)

    def merge_similar(self, threshold: float = 0.8) -> None:
        """
        Merge similar patterns within the set.

        Args:
            threshold: Similarity threshold for merging.
        """
        from log_sculptor.core.merging import merge_patterns
        self.patterns = merge_patterns(self.patterns, threshold)
        self.patterns.sort(key=lambda p: p.frequency, reverse=True)


def _generate_pattern_id(elements: list[PatternElement]) -> str:
    sig = "|".join(
        f"{e.type}:{e.token_type.value if e.token_type else e.value}"
        for e in elements
        if not (e.type == "literal" and e.token_type == TokenType.WHITESPACE)
    )
    return hashlib.md5(sig.encode()).hexdigest()[:12]


def _generate_field_name(token: Token, index: int, prev_token: Token | None) -> str:
    if prev_token and prev_token.type == TokenType.WORD:
        return prev_token.value.lower()
    type_names = {
        TokenType.TIMESTAMP: "timestamp",
        TokenType.IP: "ip",
        TokenType.QUOTED: "message",
        TokenType.BRACKET: "data",
        TokenType.NUMBER: "value",
        TokenType.WORD: "field",
    }
    base = type_names.get(token.type, "field")
    return f"{base}_{index}"


def _pattern_from_tokens(tokens: list[Token], line: str) -> Pattern:
    elements: list[PatternElement] = []
    field_index = 0
    prev_non_ws: Token | None = None

    for token in tokens:
        if token.type == TokenType.WHITESPACE:
            elements.append(PatternElement(type="literal", value=token.value, token_type=TokenType.WHITESPACE))
        else:
            field_name = _generate_field_name(token, field_index, prev_non_ws)
            elements.append(PatternElement(type="field", token_type=token.type, field_name=field_name))
            field_index += 1
            prev_non_ws = token

    pattern_id = _generate_pattern_id(elements)
    return Pattern(id=pattern_id, elements=elements, frequency=1, example=line)


def learn_patterns(
    source: str | Path,
    sample_size: int | None = None,
    min_frequency: int = 1,
    use_clustering: bool = False,
    cluster_threshold: float = 0.7,
) -> PatternSet:
    """Learn patterns from a log file."""
    from log_sculptor.core.clustering import cluster_lines, cluster_by_exact_signature

    source = Path(source)
    lines: list[tuple[list[Token], str]] = []

    with source.open("r", errors="replace") as f:
        for i, line in enumerate(f):
            if sample_size and i >= sample_size:
                break
            line = line.rstrip("\n\r")
            if not line:
                continue
            tokens = tokenize(line)
            lines.append((tokens, line))

    if use_clustering:
        clusters = cluster_lines(lines, threshold=cluster_threshold)
    else:
        clusters = cluster_by_exact_signature(lines)

    pattern_set = PatternSet()
    for cluster in clusters:
        if len(cluster.members) < min_frequency:
            continue
        tokens, line = cluster.members[0]
        pattern = _pattern_from_tokens(tokens, line)
        pattern.frequency = len(cluster.members)
        pattern.confidence = cluster.cohesion
        pattern_set.add(pattern)

    pattern_set.patterns.sort(key=lambda p: p.frequency, reverse=True)
    return pattern_set


@dataclass
class ParsedRecord:
    """A parsed log record."""
    line_number: int
    raw: str
    fields: dict[str, str]
    pattern_id: str | None
    matched: bool
    confidence: float = 1.0
    typed_fields: dict[str, Any] | None = None


def parse_logs(
    source: str | Path,
    patterns: PatternSet,
    detect_types: bool = True,
) -> Iterator[ParsedRecord]:
    """Parse a log file using learned patterns."""
    from log_sculptor.types.detector import detect_type

    source = Path(source)

    with source.open("r", errors="replace") as f:
        for i, line in enumerate(f, start=1):
            line = line.rstrip("\n\r")
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

            yield ParsedRecord(
                line_number=i,
                raw=line,
                fields=fields or {},
                pattern_id=pattern.id if pattern else None,
                matched=pattern is not None,
                confidence=confidence,
                typed_fields=typed_fields,
            )
