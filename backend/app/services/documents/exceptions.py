from typing import Optional, Dict, Any


class DocumentServiceError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "DOCUMENT_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class FileValidationError(DocumentServiceError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FILE_VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class FileSizeError(DocumentServiceError):
    def __init__(self, file_size: int, max_size: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"File size {file_size} bytes exceeds maximum allowed {max_size} bytes",
            code="FILE_SIZE_EXCEEDED",
            status_code=413,
            details={"file_size": file_size, "max_size": max_size, **(details or {})},
        )


class UnsupportedFileTypeError(DocumentServiceError):
    def __init__(self, file_type: str, allowed_types: list, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Unsupported file type: {file_type}. Allowed types: {', '.join(allowed_types)}",
            code="UNSUPPORTED_FILE_TYPE",
            status_code=415,
            details={"file_type": file_type, "allowed_types": allowed_types, **(details or {})},
        )


class DuplicateFileError(DocumentServiceError):
    def __init__(self, filename: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"File with name '{filename}' already exists",
            code="DUPLICATE_FILE",
            status_code=409,
            details={"filename": filename, **(details or {})},
        )


class DocumentNotFoundError(DocumentServiceError):
    def __init__(self, document_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Document with ID '{document_id}' not found",
            code="DOCUMENT_NOT_FOUND",
            status_code=404,
            details={"document_id": document_id, **(details or {})},
        )


class ParsingError(DocumentServiceError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Document parsing failed: {message}",
            code="PARSING_ERROR",
            status_code=500,
            details=details,
        )


class ChunkingError(DocumentServiceError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Document chunking failed: {message}",
            code="CHUNKING_ERROR",
            status_code=500,
            details=details,
        )


class EmbeddingGenerationError(DocumentServiceError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Embedding generation failed: {message}",
            code="EMBEDDING_GENERATION_ERROR",
            status_code=500,
            details=details,
        )


class VectorStoreError(DocumentServiceError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Vector store operation failed: {message}",
            code="VECTOR_STORE_ERROR",
            status_code=500,
            details=details,
        )


class DatabaseError(DocumentServiceError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Database operation failed: {message}",
            code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )