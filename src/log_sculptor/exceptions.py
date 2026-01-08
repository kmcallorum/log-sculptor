"""Custom exceptions for log-sculptor."""


class LogSculptorError(Exception):
    """Base exception for log-sculptor."""


class TokenizationError(LogSculptorError):
    """Error during line tokenization."""


class PatternError(LogSculptorError):
    """Error with pattern operations."""


class PatternNotFoundError(PatternError):
    """No matching pattern found for a log line."""


class PatternLoadError(PatternError):
    """Error loading patterns from file."""


class PatternSaveError(PatternError):
    """Error saving patterns to file."""


class OutputError(LogSculptorError):
    """Error writing output."""
