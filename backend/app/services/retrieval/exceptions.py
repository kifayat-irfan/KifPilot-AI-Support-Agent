from typing import Optional, Dict, Any


class RetrievalError(Exception):
    """Base exception for retrieval errors."""
    def __init__(
        self,
        message: str,
        code: str = "RETRIEVAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class EmptyQueryError(RetrievalError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Search query cannot be empty",
            code="EMPTY_QUERY",
            status_code=400,
            details=details,
        )


class InvalidFiltersError(RetrievalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Invalid filters: {message}",
            code="INVALID_FILTERS",
            status_code=400,
            details=details,
        )


class InvalidTopKError(RetrievalError):
    def __init__(self, top_k: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Invalid top_k value: {top_k}. Must be between 1 and 20",
            code="INVALID_TOP_K",
            status_code=400,
            details={"top_k": top_k, **(details or {})},
        )


class InvalidUUIDError(RetrievalError):
    def __init__(self, field: str, value: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Invalid UUID format for {field}: {value}",
            code="INVALID_UUID",
            status_code=400,
            details={"field": field, "value": value, **(details or {})},
        )


class EmbeddingGenerationError(RetrievalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Embedding generation failed: {message}",
            code="EMBEDDING_GENERATION_ERROR",
            status_code=500,
            details=details,
        )


class VectorSearchError(RetrievalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Vector search failed: {message}",
            code="VECTOR_SEARCH_ERROR",
            status_code=500,
            details=details,
        )


class ContextBuildError(RetrievalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Context building failed: {message}",
            code="CONTEXT_BUILD_ERROR",
            status_code=500,
            details=details,
        )


class NoResultsError(RetrievalError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="No results found matching the query and filters",
            code="NO_RESULTS",
            status_code=404,
            details=details,
        )