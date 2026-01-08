"""Tests for test fixtures and helpers."""
import pytest
from pathlib import Path
from log_sculptor.testing.fixtures import (
    create_test_patterns,
    create_test_log_file,
    SandboxContext,
    isolated_test,
)
from log_sculptor.di import resolve, FileReader, FileWriter


class TestCreateTestPatterns:
    """Tests for create_test_patterns function."""

    def test_creates_patterns(self):
        ps = create_test_patterns(count=3)

        assert len(ps.patterns) == 3

    def test_patterns_have_required_fields(self):
        ps = create_test_patterns(count=1)
        pattern = ps.patterns[0]

        assert pattern.id is not None
        assert pattern.elements is not None
        assert pattern.frequency > 0
        assert pattern.confidence > 0

    def test_with_examples(self):
        ps = create_test_patterns(count=1, with_examples=True)

        assert ps.patterns[0].example is not None

    def test_without_examples(self):
        ps = create_test_patterns(count=1, with_examples=False)

        assert ps.patterns[0].example is None


class TestCreateTestLogFile:
    """Tests for create_test_log_file function."""

    def test_creates_file_from_lines(self, tmp_path):
        output = tmp_path / "test.log"
        lines = ["line1", "line2", "line3"]

        result = create_test_log_file(output, lines=lines)

        assert result == output
        assert output.exists()
        content = output.read_text().strip().split("\n")
        assert content == lines

    def test_creates_file_from_generator(self, tmp_path):
        output = tmp_path / "test.log"

        result = create_test_log_file(output, generator="app", count=50, seed=42)

        assert result == output
        assert output.exists()
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 50

    def test_default_creates_app_logs(self, tmp_path):
        output = tmp_path / "test.log"

        create_test_log_file(output, count=10)

        assert output.exists()
        content = output.read_text()
        assert "[" in content  # App logs have brackets


class TestSandboxContext:
    """Tests for SandboxContext class."""

    def test_creates_temp_dir(self):
        with SandboxContext() as ctx:
            assert ctx.temp_dir.exists()
            temp_dir = ctx.temp_dir

        # Should be cleaned up after exit
        assert not temp_dir.exists()

    def test_registers_mocks(self):
        with SandboxContext() as ctx:
            reader = resolve(FileReader)
            writer = resolve(FileWriter)

            assert reader is ctx.mock_reader
            assert writer is ctx.mock_writer

    def test_create_file(self):
        with SandboxContext() as ctx:
            path = ctx.create_file("test.txt", "hello world")

            assert path.exists()
            assert path.read_text() == "hello world"

    def test_create_file_from_list(self):
        with SandboxContext() as ctx:
            path = ctx.create_file("test.txt", ["line1", "line2"])

            assert path.read_text() == "line1\nline2"

    def test_create_log_file(self):
        with SandboxContext() as ctx:
            path = ctx.create_log_file("test.log", generator="app", count=20)

            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 20

    def test_add_mock_file(self):
        with SandboxContext() as ctx:
            ctx.add_mock_file("/virtual/test.log", ["mock line 1", "mock line 2"])

            lines = ctx.mock_reader.read_lines(Path("/virtual/test.log"))
            assert lines == ["mock line 1", "mock line 2"]


class TestIsolatedTest:
    """Tests for isolated_test context manager."""

    def test_provides_context(self):
        with isolated_test() as ctx:
            assert ctx is not None
            assert ctx.temp_dir.exists()

    def test_cleans_up_after(self):
        with isolated_test() as ctx:
            temp_dir = ctx.temp_dir
            ctx.create_file("test.txt", "content")

        assert not temp_dir.exists()

    def test_mocks_are_registered(self):
        with isolated_test() as ctx:
            ctx.add_mock_file("/test.log", ["line1"])

            reader = resolve(FileReader)
            lines = reader.read_lines(Path("/test.log"))

            assert lines == ["line1"]
