"""Mock implementations for testing."""

from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field


@dataclass
class MockFileReader:
    """Mock file reader for testing."""

    files: dict[str, list[str]] = field(default_factory=dict)
    read_count: int = 0
    on_read: Callable[[Path], None] | None = None

    def add_file(self, path: str | Path, lines: list[str]) -> None:
        """Add a mock file with content."""
        self.files[str(path)] = lines

    def read_lines(self, path: Path) -> list[str]:
        """Read all lines from a mock file."""
        self.read_count += 1
        if self.on_read:
            self.on_read(path)
        key = str(path)
        if key not in self.files:
            raise FileNotFoundError(f"Mock file not found: {path}")
        return self.files[key].copy()

    def iter_lines(self, path: Path):
        """Iterate over lines in a mock file."""
        for line in self.read_lines(path):
            yield line


@dataclass
class MockFileWriter:
    """Mock file writer for testing."""

    written: dict[str, str | bytes] = field(default_factory=dict)
    write_count: int = 0
    on_write: Callable[[Path, Any], None] | None = None

    def write_text(self, path: Path, content: str) -> None:
        """Write text to a mock file."""
        self.write_count += 1
        if self.on_write:
            self.on_write(path, content)
        self.written[str(path)] = content

    def write_bytes(self, path: Path, content: bytes) -> None:
        """Write bytes to a mock file."""
        self.write_count += 1
        if self.on_write:
            self.on_write(path, content)
        self.written[str(path)] = content

    def get_written(self, path: str | Path) -> str | bytes | None:
        """Get content written to a path."""
        return self.written.get(str(path))


@dataclass
class MockToken:
    """Mock token for testing."""
    type: str
    value: str
    start: int = 0
    end: int = 0


@dataclass
class MockTokenizer:
    """Mock tokenizer for testing."""

    responses: dict[str, list[MockToken]] = field(default_factory=dict)
    default_tokens: list[MockToken] | None = None
    call_count: int = 0
    calls: list[str] = field(default_factory=list)

    def add_response(self, line: str, tokens: list[MockToken]) -> None:
        """Add a mock response for a specific line."""
        self.responses[line] = tokens

    def tokenize(self, line: str) -> list[MockToken]:
        """Tokenize a line (mock)."""
        self.call_count += 1
        self.calls.append(line)
        if line in self.responses:
            return self.responses[line]
        if self.default_tokens is not None:
            return self.default_tokens
        # Return simple word tokens by default
        return [MockToken(type="WORD", value=w, start=0, end=len(w))
                for w in line.split()]


@dataclass
class MockPattern:
    """Mock pattern for testing."""
    id: str
    confidence: float = 1.0


@dataclass
class MockPatternMatcher:
    """Mock pattern matcher for testing."""

    responses: dict[str, tuple[MockPattern | None, dict | None]] = field(default_factory=dict)
    default_response: tuple[MockPattern | None, dict | None] = (None, None)
    call_count: int = 0
    calls: list[str] = field(default_factory=list)

    def add_response(self, line: str, pattern: MockPattern | None, fields: dict | None) -> None:
        """Add a mock response for a specific line."""
        self.responses[line] = (pattern, fields)

    def set_default(self, pattern: MockPattern | None, fields: dict | None) -> None:
        """Set the default response for unregistered lines."""
        self.default_response = (pattern, fields)

    def match(self, line: str) -> tuple[MockPattern | None, dict | None]:
        """Match a line (mock)."""
        self.call_count += 1
        self.calls.append(line)
        if line in self.responses:
            return self.responses[line]
        return self.default_response


@dataclass
class MockTypedValue:
    """Mock typed value for testing."""
    type: str
    value: Any
    normalized: Any


@dataclass
class MockTypeDetector:
    """Mock type detector for testing."""

    responses: dict[str, MockTypedValue] = field(default_factory=dict)
    default_type: str = "STRING"
    call_count: int = 0
    calls: list[str] = field(default_factory=list)

    def add_response(self, value: str, typed: MockTypedValue) -> None:
        """Add a mock response for a specific value."""
        self.responses[value] = typed

    def detect(self, value: str) -> MockTypedValue:
        """Detect type (mock)."""
        self.call_count += 1
        self.calls.append(value)
        if value in self.responses:
            return self.responses[value]
        return MockTypedValue(type=self.default_type, value=value, normalized=value)


class CallRecorder:
    """Records function calls for verification."""

    def __init__(self):
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return None

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def assert_called(self) -> None:
        assert self.call_count > 0, "Expected at least one call"

    def assert_called_once(self) -> None:
        assert self.call_count == 1, f"Expected exactly one call, got {self.call_count}"

    def assert_called_with(self, *args, **kwargs) -> None:
        assert len(self.calls) > 0, "No calls recorded"
        last_args, last_kwargs = self.calls[-1]
        assert last_args == args, f"Args mismatch: {last_args} != {args}"
        assert last_kwargs == kwargs, f"Kwargs mismatch: {last_kwargs} != {kwargs}"

    def reset(self) -> None:
        self.calls.clear()
