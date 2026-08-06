"""Exceptions for Context Compression."""


class ContextCompressionError(Exception):
    """Base exception for context compression errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class CompressionError(ContextCompressionError):
    """Raised when context compression fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class DeduplicationError(ContextCompressionError):
    """Raised when deduplication fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class ChunkMergingError(ContextCompressionError):
    """Raised when chunk merging fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class LowValueRemovalError(ContextCompressionError):
    """Raised when low-value text removal fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class TokenBudgetExceededError(ContextCompressionError):
    """Raised when token budget is exceeded and cannot be satisfied."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class InvalidChunkError(ContextCompressionError):
    """Raised when a chunk is invalid or malformed."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class InvalidConfigError(ContextCompressionError):
    """Raised when compression configuration is invalid."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class ChunkMergingError(ContextCompressionError):
    """Raised when chunk merging fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)