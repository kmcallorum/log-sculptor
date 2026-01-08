"""Test fixtures and helpers for log-sculptor."""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from contextlib import contextmanager
import tempfile
import shutil

from log_sculptor.core.patterns import Pattern, PatternElement, PatternSet
from log_sculptor.core.tokenizer import TokenType
from log_sculptor.testing.generators import write_sample_logs
from log_sculptor.di import reset_container, register_instance, FileReader, FileWriter
from log_sculptor.testing.mocks import MockFileReader, MockFileWriter


def create_test_patterns(
    count: int = 3,
    with_examples: bool = True,
) -> PatternSet:
    """
    Create a PatternSet with test patterns.

    Args:
        count: Number of patterns to create.
        with_examples: Include example lines.

    Returns:
        PatternSet with test patterns.
    """
    ps = PatternSet()

    pattern_specs = [
        # Simple app log pattern
        {
            "id": "app_info",
            "elements": [
                PatternElement(type="field", token_type=TokenType.TIMESTAMP, field_name="timestamp"),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="literal", value="[", token_type=TokenType.PUNCT),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="level"),
                PatternElement(type="literal", value="]", token_type=TokenType.PUNCT),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="message"),
            ],
            "frequency": 100,
            "confidence": 0.95,
            "example": "2024-01-15T10:30:00 [INFO] Server started",
        },
        # HTTP request pattern
        {
            "id": "http_request",
            "elements": [
                PatternElement(type="field", token_type=TokenType.IP, field_name="client_ip"),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="method"),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="path"),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="field", token_type=TokenType.NUMBER, field_name="status"),
            ],
            "frequency": 50,
            "confidence": 0.90,
            "example": "192.168.1.1 GET /api/users 200",
        },
        # Error pattern
        {
            "id": "error_log",
            "elements": [
                PatternElement(type="field", token_type=TokenType.TIMESTAMP, field_name="timestamp"),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="literal", value="ERROR", token_type=TokenType.WORD),
                PatternElement(type="literal", value=":", token_type=TokenType.PUNCT),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="field", token_type=TokenType.QUOTED, field_name="error_message"),
            ],
            "frequency": 10,
            "confidence": 0.85,
            "example": '2024-01-15T10:30:00 ERROR: "Connection refused"',
        },
        # Key-value pattern
        {
            "id": "kv_log",
            "elements": [
                PatternElement(type="literal", value="event", token_type=TokenType.WORD),
                PatternElement(type="literal", value="=", token_type=TokenType.PUNCT),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="event"),
                PatternElement(type="literal", value=" ", token_type=TokenType.WHITESPACE),
                PatternElement(type="literal", value="user", token_type=TokenType.WORD),
                PatternElement(type="literal", value="=", token_type=TokenType.PUNCT),
                PatternElement(type="field", token_type=TokenType.WORD, field_name="user"),
            ],
            "frequency": 25,
            "confidence": 0.88,
            "example": "event=login user=admin",
        },
        # JSON-ish pattern
        {
            "id": "json_log",
            "elements": [
                PatternElement(type="field", token_type=TokenType.BRACKET, field_name="json_data"),
            ],
            "frequency": 30,
            "confidence": 0.92,
            "example": '{"level": "info", "message": "test"}',
        },
    ]

    for i, spec in enumerate(pattern_specs[:count]):
        pattern = Pattern(
            id=spec["id"],
            elements=spec["elements"],
            frequency=spec["frequency"],
            confidence=spec["confidence"],
            example=spec["example"] if with_examples else None,
        )
        ps.add(pattern)

    return ps


def create_test_log_file(
    path: Path,
    lines: list[str] | None = None,
    generator: str | None = None,
    count: int = 100,
    seed: int | None = 42,
) -> Path:
    """
    Create a test log file.

    Args:
        path: Output file path.
        lines: Specific lines to write (if provided, ignores generator).
        generator: Generator type if lines not provided.
        count: Number of lines for generator.
        seed: Random seed for reproducibility.

    Returns:
        Path to created file.
    """
    if lines is not None:
        with open(path, "w") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    if generator:
        return write_sample_logs(path, generator=generator, count=count, seed=seed)

    # Default: simple app logs
    return write_sample_logs(path, generator="app", count=count, seed=seed)


@dataclass
class SandboxContext:
    """
    Context manager for isolated testing with mocks.

    Usage:
        with SandboxContext() as ctx:
            ctx.mock_reader.add_file("/test.log", ["line1", "line2"])
            # ... run tests
    """

    temp_dir: Path = field(default=None)
    mock_reader: MockFileReader = field(default_factory=MockFileReader)
    mock_writer: MockFileWriter = field(default_factory=MockFileWriter)
    _cleanup: bool = True

    def __post_init__(self):
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="log_sculptor_test_"))
            self._cleanup = True

    def __enter__(self) -> "SandboxContext":
        """Enter context and register mocks."""
        reset_container()
        register_instance(FileReader, self.mock_reader)
        register_instance(FileWriter, self.mock_writer)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and cleanup."""
        reset_container()
        if self._cleanup and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_file(self, name: str, content: str | list[str]) -> Path:
        """Create a real file in the temp directory."""
        path = self.temp_dir / name
        if isinstance(content, list):
            content = "\n".join(content)
        path.write_text(content)
        return path

    def create_log_file(
        self,
        name: str = "test.log",
        generator: str = "app",
        count: int = 100,
        seed: int = 42,
    ) -> Path:
        """Create a log file using a generator."""
        path = self.temp_dir / name
        return create_test_log_file(path, generator=generator, count=count, seed=seed)

    def add_mock_file(self, path: str | Path, lines: list[str]) -> None:
        """Add a mock file to the mock reader."""
        self.mock_reader.add_file(path, lines)


@contextmanager
def isolated_test():
    """
    Context manager for isolated tests with automatic cleanup.

    Usage:
        with isolated_test() as ctx:
            log_file = ctx.create_log_file()
            patterns = learn_patterns(log_file)
    """
    ctx = SandboxContext()
    try:
        ctx.__enter__()
        yield ctx
    finally:
        ctx.__exit__(None, None, None)
