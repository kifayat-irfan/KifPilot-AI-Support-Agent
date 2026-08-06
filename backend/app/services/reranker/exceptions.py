"""Exceptions for Cross-Encoder Re-ranker."""


class RerankerError(Exception):
    """Base exception for reranker errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ModelNotLoadedError(RerankerError):
    """Raised when the Cross-Encoder model is not loaded."""
    def __init__(self, message: str = "Cross-Encoder model not loaded"):
        super().__init__(message)


class ModelLoadError(RerankerError):
    """Raised when the Cross-Encoder model fails to load."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class RerankingError(RerankerError):
    """Raised when reranking fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class RerankerTimeoutError(RerankerError):
    """Raised when reranking times out."""
    def __init__(self, timeout_seconds: float):
        super().__init__(f"Reranking timed out after {timeout_seconds} seconds")
        self.timeout_seconds = timeout_seconds


class InvalidCandidateError(RerankerError):
    """Raised when a candidate is invalid."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class EmptyCandidatesError(RerankerError):
    """Raised when no candidates are provided for reranking."""
    def __init__(self):
        super().__init__("No candidates provided for reranking")


class RerankerUnavailableError(RerankerError):
    """Raised when reranker is unavailable and fallback is not configured."""
    def __init__(self, message: str = "Reranker unavailable and no fallback configured"):
        super().__init__(message)