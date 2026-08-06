"""Exceptions for Query Expansion."""


class QueryExpansionError(Exception):
    """Base exception for query expansion errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ExpansionError(QueryExpansionError):
    """Raised when query expansion fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class NormalizationError(QueryExpansionError):
    """Raised when query normalization fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class RuleExpansionError(QueryExpansionError):
    """Raised when rule-based expansion fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class LLMExpansionError(QueryExpansionError):
    """Raised when LLM-based expansion fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class LLMTimeoutError(QueryExpansionError):
    """Raised when LLM expansion times out."""
    def __init__(self, timeout_seconds: float):
        super().__init__(f"LLM expansion timed out after {timeout_seconds} seconds")
        self.timeout_seconds = timeout_seconds


class ExpansionCacheError(QueryExpansionError):
    """Raised when cache operations fail."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class InvalidQueryError(QueryExpansionError):
    """Raised when the input query is invalid."""
    def __init__(self, message: str = "Invalid query provided"):
        super().__init__(message)


class MaxExpansionsExceededError(QueryExpansionError):
    """Raised when maximum expansions are exceeded."""
    def __init__(self, max_allowed: int):
        super().__init__(f"Maximum expansions ({max_allowed}) exceeded")
        self.max_allowed = max_allowed