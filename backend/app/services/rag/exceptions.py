from typing import Optional, Dict, Any


class RAGError(Exception):
    """Base exception for RAG errors."""
    def __init__(
        self,
        message: str,
        code: str = "RAG_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class EmptyQuestionError(RAGError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Question cannot be empty",
            code="EMPTY_QUESTION",
            status_code=400,
            details=details,
        )


class PromptInjectionError(RAGError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Question contains potential prompt injection attempt",
            code="PROMPT_INJECTION",
            status_code=400,
            details=details,
        )


class QuestionTooLongError(RAGError):
    def __init__(self, length: int, max_length: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Question too long: {length} characters (max {max_length})",
            code="QUESTION_TOO_LONG",
            status_code=400,
            details={"length": length, "max_length": max_length, **(details or {})},
        )


class RetrievalFailedError(RAGError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Retrieval failed: {message}",
            code="RETRIEVAL_FAILED",
            status_code=500,
            details=details,
        )


class NoContextFoundError(RAGError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="No relevant context found for the question",
            code="NO_CONTEXT_FOUND",
            status_code=404,
            details=details,
        )


class GenerationFailedError(RAGError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Answer generation failed: {message}",
            code="GENERATION_FAILED",
            status_code=500,
            details=details,
        )


class OllamaUnavailableError(RAGError):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Ollama service is not available",
            code="OLLAMA_UNAVAILABLE",
            status_code=503,
            details=details,
        )