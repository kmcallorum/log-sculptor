"""Shared pytest fixtures."""
from pathlib import Path
import pytest

@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def simple_log(fixtures_dir: Path) -> Path:
    return fixtures_dir / "simple.log"

@pytest.fixture
def apache_log(fixtures_dir: Path) -> Path:
    return fixtures_dir / "apache_access.log"

@pytest.fixture
def java_stacktrace_log(fixtures_dir: Path) -> Path:
    return fixtures_dir / "java_stacktrace.log"
