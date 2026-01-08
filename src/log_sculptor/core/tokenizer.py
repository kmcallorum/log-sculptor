"""Line tokenization for log parsing."""

from dataclasses import dataclass
from enum import Enum
import regex


class TokenType(str, Enum):
    """Token types recognized by the tokenizer."""
    TIMESTAMP = "TIMESTAMP"
    IP = "IP"
    QUOTED = "QUOTED"
    BRACKET = "BRACKET"
    NUMBER = "NUMBER"
    WORD = "WORD"
    PUNCT = "PUNCT"
    WHITESPACE = "WHITESPACE"


@dataclass(frozen=True, slots=True)
class Token:
    """A single token from a log line."""
    type: TokenType
    value: str
    start: int
    end: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "value": self.value,
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Token":
        """Create from dictionary."""
        return cls(
            type=TokenType(data["type"]),
            value=data["value"],
            start=data["start"],
            end=data["end"],
        )


_TOKEN_PATTERNS: list[tuple[TokenType, regex.Pattern]] = [
    (TokenType.TIMESTAMP, regex.compile(
        r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?'
        r'|\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s*[+-]?\d{4}'
        r'|\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'
        r'|\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}'
    )),
    (TokenType.IP, regex.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')),
    (TokenType.QUOTED, regex.compile(r'"(?:[^"\\]|\\.)*"' r"|'(?:[^'\\]|\\.)*'")),
    (TokenType.BRACKET, regex.compile(r'\[[^\]]*\]' r'|\([^)]*\)' r'|\{[^}]*\}')),
    (TokenType.NUMBER, regex.compile(r'-?\d+\.\d+' r'|-?\d+')),
    (TokenType.WORD, regex.compile(r'[a-zA-Z_][a-zA-Z0-9_-]*')),
    (TokenType.PUNCT, regex.compile(r'[^\s\w]')),
    (TokenType.WHITESPACE, regex.compile(r'\s+')),
]


def tokenize(line: str) -> list[Token]:
    """Tokenize a log line into typed tokens."""
    tokens: list[Token] = []
    pos = 0
    length = len(line)

    while pos < length:
        matched = False
        for token_type, pattern in _TOKEN_PATTERNS:
            match = pattern.match(line, pos)
            if match:
                tokens.append(Token(type=token_type, value=match.group(0), start=pos, end=match.end()))
                pos = match.end()
                matched = True
                break
        if not matched:
            tokens.append(Token(type=TokenType.PUNCT, value=line[pos], start=pos, end=pos + 1))
            pos += 1

    return tokens


def token_signature(tokens: list[Token]) -> tuple[TokenType, ...]:
    """Get the type signature of a token list (excluding whitespace)."""
    return tuple(t.type for t in tokens if t.type != TokenType.WHITESPACE)
