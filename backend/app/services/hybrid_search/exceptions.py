"""Exceptions for hybrid search service."""


class HybridSearchError(Exception):
    """Base exception for hybrid search errors."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class EmptyQueryError(HybridSearchError):
    """Raised when search query is empty."""
    def __init__(self):
        super().__init__("Search query cannot be empty")


class InvalidTopKError(HybridSearchError):
    """Raised when top_k parameter is invalid."""
    def __init__(self, top_k: int):
        super().__init__(f"Invalid top_k value: {top_k}. Must be between 1 and 20.")
        self.top_k = top_k


class InvalidRRFConstantError(HybridSearchError):
    """Raised when RRF constant is invalid."""
    def __init__(self, rrf_constant: int):
        super().__init__(f"Invalid RRF constant: {rrf_constant}. Must be between 1 and 1000.")
        self.rrf_constant = rrf_constant


class InvalidWeightError(HybridSearchError):
    """Raised when vector or BM25 weight is invalid."""
    def __init__(self, weight_name: str, weight: float):
        super().__init__(f"Invalid {weight_name}: {weight}. Must be between 0.0 and 2.0.")
        self.weight_name = weight_name
        self.weight = weight


class BM25IndexError(HybridSearchError):
    """Raised when BM25 index operations fail."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class BM25IndexNotFoundError(BM25IndexError):
    """Raised when BM25 index is not found."""
    def __init__(self):
        super().__init__("BM25 index not found. Please build the index first.")


class BM25IndexBuildError(BM25IndexError):
    """Raised when BM25 index build fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class BM25IndexUpdateError(BM25IndexError):
    """Raised when BM25 index update fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class BM25SearchError(HybridSearchError):
    """Raised when BM25 search fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class FusionError(HybridSearchError):
    """Raised when rank fusion fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class VectorSearchError(HybridSearchError):
    """Raised when vector search fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class EmbeddingGenerationError(HybridSearchError):
    """Raised when embedding generation fails."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)


class InvalidFiltersError(HybridSearchError):
    """Raised when search filters are invalid."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)