"""Tests for mock testing utilities."""
import pytest
from pathlib import Path
from log_sculptor.testing.mocks import (
    MockFileReader,
    MockFileWriter,
    MockTokenizer,
    MockPatternMatcher,
    MockTypeDetector,
    MockToken,
    MockPattern,
    MockTypedValue,
    CallRecorder,
)


class TestMockFileReader:
    """Tests for MockFileReader."""

    def test_add_and_read_file(self):
        reader = MockFileReader()
        reader.add_file("/test.log", ["line1", "line2", "line3"])

        lines = reader.read_lines(Path("/test.log"))

        assert lines == ["line1", "line2", "line3"]

    def test_read_count_increments(self):
        reader = MockFileReader()
        reader.add_file("/test.log", ["line1"])

        assert reader.read_count == 0
        reader.read_lines(Path("/test.log"))
        assert reader.read_count == 1
        reader.read_lines(Path("/test.log"))
        assert reader.read_count == 2

    def test_read_missing_file_raises(self):
        reader = MockFileReader()

        with pytest.raises(FileNotFoundError):
            reader.read_lines(Path("/nonexistent.log"))

    def test_iter_lines(self):
        reader = MockFileReader()
        reader.add_file("/test.log", ["a", "b", "c"])

        lines = list(reader.iter_lines(Path("/test.log")))

        assert lines == ["a", "b", "c"]

    def test_on_read_callback(self):
        reader = MockFileReader()
        reader.add_file("/test.log", ["line1"])

        callback_paths = []
        reader.on_read = lambda p: callback_paths.append(p)

        reader.read_lines(Path("/test.log"))

        assert len(callback_paths) == 1


class TestMockFileWriter:
    """Tests for MockFileWriter."""

    def test_write_text(self):
        writer = MockFileWriter()

        writer.write_text(Path("/out.txt"), "hello world")

        assert writer.get_written("/out.txt") == "hello world"

    def test_write_bytes(self):
        writer = MockFileWriter()

        writer.write_bytes(Path("/out.bin"), b"binary data")

        assert writer.get_written("/out.bin") == b"binary data"

    def test_write_count_increments(self):
        writer = MockFileWriter()

        assert writer.write_count == 0
        writer.write_text(Path("/a.txt"), "a")
        assert writer.write_count == 1
        writer.write_text(Path("/b.txt"), "b")
        assert writer.write_count == 2

    def test_on_write_callback(self):
        writer = MockFileWriter()
        callback_data = []
        writer.on_write = lambda p, c: callback_data.append((p, c))

        writer.write_text(Path("/test.txt"), "content")

        assert len(callback_data) == 1


class TestMockTokenizer:
    """Tests for MockTokenizer."""

    def test_default_tokenization(self):
        tokenizer = MockTokenizer()

        tokens = tokenizer.tokenize("hello world")

        assert len(tokens) == 2
        assert tokens[0].value == "hello"
        assert tokens[1].value == "world"

    def test_custom_response(self):
        tokenizer = MockTokenizer()
        custom_tokens = [MockToken(type="CUSTOM", value="custom")]
        tokenizer.add_response("special line", custom_tokens)

        tokens = tokenizer.tokenize("special line")

        assert tokens == custom_tokens

    def test_call_tracking(self):
        tokenizer = MockTokenizer()

        tokenizer.tokenize("line1")
        tokenizer.tokenize("line2")

        assert tokenizer.call_count == 2
        assert tokenizer.calls == ["line1", "line2"]


class TestMockPatternMatcher:
    """Tests for MockPatternMatcher."""

    def test_default_no_match(self):
        matcher = MockPatternMatcher()

        pattern, fields = matcher.match("any line")

        assert pattern is None
        assert fields is None

    def test_custom_response(self):
        matcher = MockPatternMatcher()
        test_pattern = MockPattern(id="p1", confidence=0.9)
        matcher.add_response("match this", test_pattern, {"field": "value"})

        pattern, fields = matcher.match("match this")

        assert pattern.id == "p1"
        assert fields == {"field": "value"}

    def test_set_default(self):
        matcher = MockPatternMatcher()
        default_pattern = MockPattern(id="default")
        matcher.set_default(default_pattern, {"default": True})

        pattern, fields = matcher.match("anything")

        assert pattern.id == "default"
        assert fields == {"default": True}

    def test_call_tracking(self):
        matcher = MockPatternMatcher()

        matcher.match("line1")
        matcher.match("line2")

        assert matcher.call_count == 2
        assert matcher.calls == ["line1", "line2"]


class TestMockTypeDetector:
    """Tests for MockTypeDetector."""

    def test_default_string_type(self):
        detector = MockTypeDetector()

        result = detector.detect("any value")

        assert result.type == "STRING"
        assert result.value == "any value"

    def test_custom_response(self):
        detector = MockTypeDetector()
        detector.add_response("123", MockTypedValue(type="INT", value=123, normalized=123))

        result = detector.detect("123")

        assert result.type == "INT"
        assert result.value == 123

    def test_call_tracking(self):
        detector = MockTypeDetector()

        detector.detect("val1")
        detector.detect("val2")

        assert detector.call_count == 2
        assert detector.calls == ["val1", "val2"]


class TestCallRecorder:
    """Tests for CallRecorder."""

    def test_records_calls(self):
        recorder = CallRecorder()

        recorder("a", "b", key="value")

        assert recorder.call_count == 1
        assert recorder.calls[0] == (("a", "b"), {"key": "value"})

    def test_assert_called(self):
        recorder = CallRecorder()

        with pytest.raises(AssertionError):
            recorder.assert_called()

        recorder()
        recorder.assert_called()  # Should not raise

    def test_assert_called_once(self):
        recorder = CallRecorder()

        recorder()
        recorder.assert_called_once()  # Should not raise

        recorder()
        with pytest.raises(AssertionError):
            recorder.assert_called_once()

    def test_assert_called_with(self):
        recorder = CallRecorder()
        recorder("arg1", key="val")

        recorder.assert_called_with("arg1", key="val")

        with pytest.raises(AssertionError):
            recorder.assert_called_with("wrong")

    def test_reset(self):
        recorder = CallRecorder()
        recorder()
        recorder()

        recorder.reset()

        assert recorder.call_count == 0
