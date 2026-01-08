"""Tests for dependency injection container."""
import pytest
from log_sculptor.di import (
    DIContainer,
    get_container,
    register,
    resolve,
    reset_container,
    register_instance,
    FileReader,
    FileWriter,
)


class TestDIContainer:
    """Tests for DIContainer class."""

    def test_register_and_resolve(self):
        container = DIContainer()

        class MyService:
            pass

        container.register(MyService, lambda: MyService())
        instance = container.resolve(MyService)

        assert isinstance(instance, MyService)

    def test_singleton_returns_same_instance(self):
        container = DIContainer()

        class MyService:
            pass

        container.register(MyService, lambda: MyService(), singleton=True)

        instance1 = container.resolve(MyService)
        instance2 = container.resolve(MyService)

        assert instance1 is instance2

    def test_non_singleton_returns_different_instances(self):
        container = DIContainer()

        class MyService:
            pass

        container.register(MyService, lambda: MyService(), singleton=False)

        instance1 = container.resolve(MyService)
        instance2 = container.resolve(MyService)

        assert instance1 is not instance2

    def test_register_instance(self):
        container = DIContainer()

        class MyService:
            pass

        instance = MyService()
        container.register_instance(MyService, instance)

        resolved = container.resolve(MyService)
        assert resolved is instance

    def test_resolve_unregistered_raises(self):
        container = DIContainer()

        class MyService:
            pass

        with pytest.raises(KeyError):
            container.resolve(MyService)

    def test_clear_removes_all(self):
        container = DIContainer()

        class MyService:
            pass

        container.register(MyService, lambda: MyService(), singleton=True)
        container.resolve(MyService)  # Create singleton

        container.clear()

        with pytest.raises(KeyError):
            container.resolve(MyService)


class TestGlobalContainer:
    """Tests for global container functions."""

    def setup_method(self):
        reset_container()

    def teardown_method(self):
        reset_container()

    def test_global_register_and_resolve(self):
        class TestService:
            pass

        register(TestService, lambda: TestService())
        instance = resolve(TestService)

        assert isinstance(instance, TestService)

    def test_global_register_instance(self):
        class TestService:
            pass

        instance = TestService()
        register_instance(TestService, instance)

        resolved = resolve(TestService)
        assert resolved is instance

    def test_reset_clears_container(self):
        class TestService:
            pass

        register(TestService, lambda: TestService())
        reset_container()

        # Should have default FileReader/FileWriter after reset
        # but not our TestService
        with pytest.raises(KeyError):
            resolve(TestService)


class TestDefaultImplementations:
    """Tests for default protocol implementations."""

    def setup_method(self):
        reset_container()
        from log_sculptor.di import configure_defaults
        configure_defaults()

    def teardown_method(self):
        reset_container()

    def test_default_file_reader_registered(self):
        reader = resolve(FileReader)
        assert reader is not None

    def test_default_file_writer_registered(self):
        writer = resolve(FileWriter)
        assert writer is not None

    def test_file_reader_reads_file(self, tmp_path):
        reader = resolve(FileReader)
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3")

        lines = reader.read_lines(test_file)
        assert lines == ["line1", "line2", "line3"]

    def test_file_writer_writes_file(self, tmp_path):
        writer = resolve(FileWriter)
        test_file = tmp_path / "test.txt"

        writer.write_text(test_file, "hello world")

        assert test_file.read_text() == "hello world"
