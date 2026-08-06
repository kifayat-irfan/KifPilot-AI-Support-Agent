from typing import Optional, Dict, Any


class VectorStoreError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "VECTOR_STORE_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ChromaDBConnectionError(VectorStoreError):
    def __init__(self, message: str = "Cannot connect to ChromaDB", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CHROMADB_CONNECTION_ERROR",
            status_code=503,
            details=details,
        )


class CollectionNotFoundError(VectorStoreError):
    def __init__(self, collection_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Collection '{collection_name}' not found",
            code="COLLECTION_NOT_FOUND",
            status_code=404,
            details={"collection_name": collection_name, **(details or {})},
        )


class CollectionAlreadyExistsError(VectorStoreError):
    def __init__(self, collection_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Collection '{collection_name}' already exists",
            code="COLLECTION_ALREADY_EXISTS",
            status_code=409,
            details={"collection_name": collection_name, **(details or {})},
        )


class InvalidEmbeddingError(VectorStoreError):
    def __init__(
        self,
        message: str = "Invalid embedding dimension or format",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="INVALID_EMBEDDING",
            status_code=400,
            details=details,
        )


class MetadataValidationError(VectorStoreError):
    def __init__(
        self,
        message: str = "Metadata validation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="METADATA_VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class QueryError(VectorStoreError):
    def __init__(
        self,
        message: str = "Similarity search failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="QUERY_ERROR",
            status_code=500,
            details=details,
        )


class DeleteError(VectorStoreError):
    def __init__(
        self,
        message: str = "Delete operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="DELETE_ERROR",
            status_code=500,
            details=details,
        )


class ResetError(VectorStoreError):
    def __init__(
        self,
        message: str = "Reset operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="RESET_ERROR",
            status_code=500,
            details=details,
        )