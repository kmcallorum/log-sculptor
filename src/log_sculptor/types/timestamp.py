"""Timestamp parsing and normalization."""

from datetime import datetime, timezone, timedelta
import regex
from dateutil import parser as dateutil_parser

_TIMESTAMP_PATTERNS: list[tuple[regex.Pattern, str]] = [
    (regex.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$'), "iso8601"),
    (regex.compile(r'^\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s*[+-]?\d{4}$'), "apache_clf"),
    (regex.compile(r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}$'), "syslog"),
    (regex.compile(r'^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}$'), "nginx"),
    (regex.compile(r'^\d{10}$'), "epoch_seconds"),
    (regex.compile(r'^\d{13}$'), "epoch_millis"),
]

_MONTH_MAP = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
              'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}


def _parse_apache_clf(value: str) -> datetime | None:
    try:
        parts = value.split()
        datetime_part = parts[0]
        tz_part = parts[1] if len(parts) > 1 else "+0000"
        day = int(datetime_part[0:2])
        month = _MONTH_MAP.get(datetime_part[3:6])
        year = int(datetime_part[7:11])
        hour = int(datetime_part[12:14])
        minute = int(datetime_part[15:17])
        second = int(datetime_part[18:20])
        if month is None:
            return None
        tz_sign = 1 if tz_part[0] == '+' else -1
        tz_hours = int(tz_part[1:3])
        tz_minutes = int(tz_part[3:5])
        offset_seconds = tz_sign * (tz_hours * 3600 + tz_minutes * 60)
        tz_offset = timezone(timedelta(seconds=offset_seconds))
        return datetime(year, month, day, hour, minute, second, tzinfo=tz_offset)
    except (ValueError, IndexError, KeyError):
        return None


def _parse_syslog(value: str) -> datetime | None:
    try:
        parts = value.split()
        month = _MONTH_MAP.get(parts[0])
        day = int(parts[1])
        time_parts = parts[2].split(':')
        hour, minute, second = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])
        if month is None:
            return None
        return datetime(datetime.now().year, month, day, hour, minute, second)
    except (ValueError, IndexError, KeyError):
        return None


def _parse_nginx(value: str) -> datetime | None:
    try:
        parts = value.split()
        date_parts = parts[0].split('/')
        time_parts = parts[1].split(':')
        return datetime(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
                       int(time_parts[0]), int(time_parts[1]), int(time_parts[2]))
    except (ValueError, IndexError):
        return None


def _looks_like_timestamp(value: str) -> bool:
    if not regex.search(r'[-/:T]', value):
        return False
    number_groups = regex.findall(r'\d+', value)
    if len(number_groups) < 2:
        return False
    if regex.match(r'^-?\d+\.?\d*$', value):
        return False
    return True


def parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None

    for pattern, format_name in _TIMESTAMP_PATTERNS:
        if pattern.match(value):
            if format_name == "apache_clf":
                return _parse_apache_clf(value)
            elif format_name == "syslog":
                return _parse_syslog(value)
            elif format_name == "nginx":
                return _parse_nginx(value)
            elif format_name == "epoch_seconds":
                try:
                    return datetime.fromtimestamp(int(value), tz=timezone.utc)
                except (ValueError, OSError):
                    pass
            elif format_name == "epoch_millis":
                try:
                    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
                except (ValueError, OSError):
                    pass
            break

    if not _looks_like_timestamp(value):
        return None

    try:
        return dateutil_parser.parse(value)
    except (ValueError, dateutil_parser.ParserError):
        return None


def normalize_timestamp(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def is_likely_timestamp(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    for pattern, _ in _TIMESTAMP_PATTERNS:
        if pattern.match(value):
            return True
    if regex.search(r'\d{4}[-/]\d{2}[-/]\d{2}', value):
        return True
    if regex.search(r'\d{2}[-/]\d{2}[-/]\d{4}', value):
        return True
    return False
