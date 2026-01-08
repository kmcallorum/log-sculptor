"""Field type detection and normalization."""

from dataclasses import dataclass
from enum import Enum
from typing import Any
import regex

from log_sculptor.types.timestamp import parse_timestamp, normalize_timestamp


class FieldType(str, Enum):
    TIMESTAMP = "timestamp"
    IP = "ip"
    URL = "url"
    UUID = "uuid"
    HEX = "hex"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"


@dataclass(frozen=True, slots=True)
class TypedValue:
    raw: str
    type: FieldType
    normalized: Any

    def to_dict(self) -> dict:
        return {"raw": self.raw, "type": self.type.value, "normalized": self.normalized}


_IPV4_PATTERN = regex.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
_IPV6_PATTERN = regex.compile(
    r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    r'|^(?:[0-9a-fA-F]{1,4}:){1,7}:$'
    r'|^::$'
)
_URL_PATTERN = regex.compile(r'^https?://[^\s]+$', regex.IGNORECASE)
_UUID_PATTERN = regex.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
_HEX_PATTERN = regex.compile(r'^(?:0x)?[0-9a-fA-F]{8,}$')
_INT_PATTERN = regex.compile(r'^-?\d+$')
_FLOAT_PATTERN = regex.compile(r'^-?\d+\.\d+$')
_BOOL_VALUES = {'true': True, 'false': False, 'yes': True, 'no': False, '1': True, '0': False, 'on': True, 'off': False}


def _is_valid_ipv4(value: str) -> bool:
    match = _IPV4_PATTERN.match(value)
    if not match:
        return False
    return all(int(g) <= 255 for g in match.groups())


def detect_type(value: str) -> TypedValue:
    value = value.strip()

    dt = parse_timestamp(value)
    if dt is not None:
        return TypedValue(value, FieldType.TIMESTAMP, normalize_timestamp(dt))

    if _is_valid_ipv4(value):
        return TypedValue(value, FieldType.IP, value)
    if _IPV6_PATTERN.match(value):
        return TypedValue(value, FieldType.IP, value.lower())

    if _URL_PATTERN.match(value):
        return TypedValue(value, FieldType.URL, value)

    if _UUID_PATTERN.match(value):
        return TypedValue(value, FieldType.UUID, value.lower())

    if _HEX_PATTERN.match(value) and not _INT_PATTERN.match(value):
        normalized = value.lower()
        if normalized.startswith('0x'):
            normalized = normalized[2:]
        return TypedValue(value, FieldType.HEX, normalized)

    lower_value = value.lower()
    if lower_value in _BOOL_VALUES:
        return TypedValue(value, FieldType.BOOL, _BOOL_VALUES[lower_value])

    if _INT_PATTERN.match(value):
        try:
            return TypedValue(value, FieldType.INT, int(value))
        except ValueError:
            pass

    if _FLOAT_PATTERN.match(value):
        try:
            return TypedValue(value, FieldType.FLOAT, float(value))
        except ValueError:
            pass

    return TypedValue(value, FieldType.STRING, value)


def detect_types_for_fields(fields: dict[str, str]) -> dict[str, TypedValue]:
    return {name: detect_type(value) for name, value in fields.items()}
