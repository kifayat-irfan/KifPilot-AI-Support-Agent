from typing import Optional, Dict, Any


class StreamingError(Exception):
    """Base exception for streaming errors."""
    def __init__(
        self,
        message: str,
        code: str = "STREAMING_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class RetrievalFailedError(StreamingError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Retrieval failed: {message}",
            code="RETRIEVAL_FAILED",
            status_code=500,
            details=details,
        )


class NoContextFoundError(StreamingError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="No relevant context found for the question",
            code="NO_CONTEXT_FOUND",
            status_code=404,
            details=details,
        )


class GenerationFailedError(StreamingError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Answer generation failed: {message}",
            code="GENERATION_FAILED",
            status_code=500,
            details=details,
        )


class OllamaUnavailableError(StreamingError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Ollama service is not available",
            code="OLLAMA_UNAVAILABLE",
            status_code=503,
            details=details,
        )


class CitationGenerationError(StreamingError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Citation generation failed: {message}",
            code="CITATION_GENERATION_FAILED",
            status_code=500,
            details=details,
        )


class StreamingTimeoutError(StreamingError):
    def __init__(self, timeout_seconds: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Streaming request timed out after {timeout_seconds} seconds",
            code="STREAMING_TIMEOUT",
            status_code=408,
            details={"timeout_seconds": timeout_seconds, **(details or {})},
        )


class ClientDisconnectedError(StreamingError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Client disconnected during streaming",
            code="CLIENT_DISCONNECTED",
            status_code=499,
            details=details,
        )


class GuardrailsError(StreamingError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="GUARDRAILS_VIOLATION",
            status_code=400,
            details=details,
        )