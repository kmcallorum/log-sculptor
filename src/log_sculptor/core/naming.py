"""Smart field naming for log patterns."""

import regex
from log_sculptor.core.tokenizer import Token, TokenType


# Common log field indicators (word before a value often indicates its meaning)
FIELD_INDICATORS = {
    # Time-related
    "time", "timestamp", "date", "datetime", "at", "when",
    # Identity
    "user", "username", "uid", "client", "host", "hostname", "server",
    "ip", "addr", "address", "src", "dst", "source", "dest", "destination",
    # HTTP/Web
    "method", "verb", "action", "path", "url", "uri", "endpoint", "route",
    "status", "code", "response", "request", "referer", "referrer", "agent",
    # Size/Count
    "size", "bytes", "length", "count", "total", "num", "amount",
    # Duration
    "duration", "elapsed", "took", "latency", "ms", "sec",
    # Identifiers
    "id", "pid", "tid", "uuid", "guid", "session", "request_id", "trace",
    # Level/Type
    "level", "severity", "priority", "type", "kind", "category",
    # Message
    "msg", "message", "error", "reason", "description", "text",
    # Other common
    "name", "key", "value", "result", "port", "version", "module", "class",
}

# Patterns that suggest field meaning from value content
VALUE_PATTERNS = [
    (regex.compile(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$"), "method"),
    (regex.compile(r"^[1-5]\d{2}$"), "status"),
    (regex.compile(r"^/[\w/.-]*$"), "path"),
    (regex.compile(r"^https?://"), "url"),
    (regex.compile(r"^\d+\.\d+\.\d+\.\d+$"), "ip"),
    (regex.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", regex.I), "uuid"),
    (regex.compile(r"^(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)$", regex.I), "level"),
    (regex.compile(r"^(true|false)$", regex.I), "flag"),
    (regex.compile(r"^\d+ms$"), "duration_ms"),
    (regex.compile(r"^\d+s$"), "duration_sec"),
]

# Key-value separators
KV_PATTERN = regex.compile(r"^(\w+)[=:](.+)$")


def infer_field_name(
    token: Token,
    index: int,
    prev_token: Token | None,
    next_token: Token | None,
    all_tokens: list[Token],
    existing_names: set[str],
) -> str:
    """
    Infer a meaningful field name based on context.

    Args:
        token: The token to name.
        index: Position in the non-whitespace token sequence.
        prev_token: Previous non-whitespace token.
        next_token: Next non-whitespace token.
        all_tokens: All tokens in the line.
        existing_names: Names already assigned (to avoid duplicates).

    Returns:
        A meaningful field name.
    """
    name = None

    # Strategy 1: Check if previous token is a known field indicator
    if prev_token and prev_token.type == TokenType.WORD:
        prev_lower = prev_token.value.lower()
        if prev_lower in FIELD_INDICATORS:
            name = prev_lower

    # Strategy 2: Check for key=value or key:value pattern in the token itself
    if name is None and token.type in (TokenType.WORD, TokenType.QUOTED):
        kv_match = KV_PATTERN.match(token.value.strip('"\''))
        if kv_match:
            name = kv_match.group(1).lower()

    # Strategy 3: Infer from value content patterns
    if name is None:
        value = token.value.strip('"\'[]')
        for pattern, suggested_name in VALUE_PATTERNS:
            if pattern.match(value):
                name = suggested_name
                break

    # Strategy 4: Use token type as base name
    if name is None:
        type_names = {
            TokenType.TIMESTAMP: "timestamp",
            TokenType.IP: "ip",
            TokenType.QUOTED: "message",
            TokenType.BRACKET: "data",
            TokenType.NUMBER: "value",
            TokenType.WORD: "field",
        }
        name = type_names.get(token.type, "field")

    # Ensure uniqueness
    base_name = name
    counter = 1
    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1

    return name


def generate_field_names(tokens: list[Token]) -> list[str]:
    """
    Generate meaningful field names for all non-whitespace tokens.

    Args:
        tokens: List of tokens from a log line.

    Returns:
        List of field names (same length as non-whitespace tokens).
    """
    non_ws_tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
    names: list[str] = []
    existing: set[str] = set()

    for i, token in enumerate(non_ws_tokens):
        prev_token = non_ws_tokens[i - 1] if i > 0 else None
        next_token = non_ws_tokens[i + 1] if i < len(non_ws_tokens) - 1 else None

        name = infer_field_name(token, i, prev_token, next_token, tokens, existing)
        names.append(name)
        existing.add(name)

    return names


def refine_pattern_names(elements: list, example_lines: list[str] | None = None) -> None:
    """
    Refine field names in pattern elements based on analysis.

    Modifies elements in place.

    Args:
        elements: List of PatternElement objects.
        example_lines: Optional example lines for additional context.
    """
    from log_sculptor.core.tokenizer import tokenize

    # If we have example lines, analyze them for better naming
    if example_lines and len(example_lines) > 0:
        # Use the first example to generate names
        tokens = tokenize(example_lines[0])
        names = generate_field_names(tokens)

        # Apply names to field elements
        name_idx = 0
        for elem in elements:
            if elem.type == "field":
                if name_idx < len(names):
                    elem.field_name = names[name_idx]
                name_idx += 1
