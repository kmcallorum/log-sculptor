"""Core data models for log-sculptor."""

from dataclasses import dataclass
from typing import Literal

from log_sculptor.core.tokenizer import Token, TokenType


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
