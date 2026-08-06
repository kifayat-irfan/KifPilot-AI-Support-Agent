from typing import Optional, Dict, Any


class CitationError(Exception):
    """Base exception for citation errors."""
    def __init__(
        self,
        message: str,
        code: str = "CITATION_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class MissingChunkError(CitationError):
    def __init__(self, chunk_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Referenced chunk not found: {chunk_id}",
            code="MISSING_CHUNK",
            status_code=404,
            details={"chunk_id": chunk_id, **(details or {})},
        )


class DeletedDocumentError(CitationError):
    def __init__(self, document_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Referenced document has been deleted: {document_id}",
            code="DELETED_DOCUMENT",
            status_code=404,
            details={"document_id": document_id, **(details or {})},
        )


class InvalidMetadataError(CitationError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Invalid citation metadata: {message}",
            code="INVALID_METADATA",
            status_code=400,
            details=details,
        )


class CitationGenerationError(CitationError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Citation generation failed: {message}",
            code="CITATION_GENERATION_FAILED",
            status_code=500,
            details=details,
        )


class CitationValidationError(CitationError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Citation validation failed: {message}",
            code="CITATION_VALIDATION_FAILED",
            status_code=400,
            details=details,
        )