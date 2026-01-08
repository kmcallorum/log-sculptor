"""Dependency injection container for log-sculptor."""

from typing import Protocol, TypeVar, Callable, Any, runtime_checkable
from dataclasses import dataclass, field
from pathlib import Path


T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._factories: dict[type, Callable[[], Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._singleton_types: set[type] = set()

    def register(self, interface: type[T], factory: Callable[[], T], singleton: bool = False) -> None:
        """
        Register a factory for an interface.

        Args:
            interface: The type/protocol to register.
            factory: Callable that creates instances.
            singleton: If True, only one instance is created.
        """
        self._factories[interface] = factory
        if singleton:
            self._singleton_types.add(interface)

    def register_instance(self, interface: type[T], instance: T) -> None:
        """Register a pre-created instance as a singleton."""
        self._singletons[interface] = instance
        self._singleton_types.add(interface)

    def resolve(self, interface: type[T]) -> T:
        """
        Resolve an interface to an instance.

        Args:
            interface: The type/protocol to resolve.

        Returns:
            An instance of the requested type.

        Raises:
            KeyError: If the interface is not registered.
        """
        if interface in self._singletons:
            return self._singletons[interface]

        if interface not in self._factories:
            raise KeyError(f"No factory registered for {interface}")

        instance = self._factories[interface]()

        if interface in self._singleton_types:
            self._singletons[interface] = instance

        return instance

    def clear(self) -> None:
        """Clear all registrations and cached singletons."""
        self._factories.clear()
        self._singletons.clear()
        self._singleton_types.clear()


# Global container instance
_container = DIContainer()


def get_container() -> DIContainer:
    """Get the global DI container."""
    return _container


def register(interface: type[T], factory: Callable[[], T], singleton: bool = False) -> None:
    """Register a factory in the global container."""
    _container.register(interface, factory, singleton)


def register_instance(interface: type[T], instance: T) -> None:
    """Register an instance in the global container."""
    _container.register_instance(interface, instance)


def resolve(interface: type[T]) -> T:
    """Resolve from the global container."""
    return _container.resolve(interface)


def reset_container() -> None:
    """Reset the global container (useful for testing)."""
    _container.clear()


# Protocols for dependency injection

@runtime_checkable
class FileReader(Protocol):
    """Protocol for reading files."""

    def read_lines(self, path: Path) -> list[str]:
        """Read all lines from a file."""
        ...

    def iter_lines(self, path: Path):
        """Iterate over lines in a file."""
        ...


@runtime_checkable
class FileWriter(Protocol):
    """Protocol for writing files."""

    def write_text(self, path: Path, content: str) -> None:
        """Write text to a file."""
        ...

    def write_bytes(self, path: Path, content: bytes) -> None:
        """Write bytes to a file."""
        ...


@runtime_checkable
class Tokenizer(Protocol):
    """Protocol for tokenizing log lines."""

    def tokenize(self, line: str) -> list:
        """Tokenize a log line."""
        ...


@runtime_checkable
class PatternMatcher(Protocol):
    """Protocol for pattern matching."""

    def match(self, line: str) -> tuple[Any, dict | None]:
        """Match a line against patterns."""
        ...


@runtime_checkable
class TypeDetector(Protocol):
    """Protocol for type detection."""

    def detect(self, value: str) -> Any:
        """Detect the type of a value."""
        ...


# Default implementations

class DefaultFileReader:
    """Default file reader implementation."""

    def read_lines(self, path: Path) -> list[str]:
        with open(path, "r", errors="replace") as f:
            return [line.rstrip("\r\n") for line in f]

    def iter_lines(self, path: Path):
        with open(path, "r", errors="replace") as f:
            for line in f:
                yield line.rstrip("\r\n")


class DefaultFileWriter:
    """Default file writer implementation."""

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content)

    def write_bytes(self, path: Path, content: bytes) -> None:
        path.write_bytes(content)


def configure_defaults() -> None:
    """Configure default implementations in the global container."""
    register(FileReader, DefaultFileReader, singleton=True)
    register(FileWriter, DefaultFileWriter, singleton=True)


# Auto-configure defaults on import
configure_defaults()
