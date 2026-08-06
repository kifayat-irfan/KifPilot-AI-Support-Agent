from typing import Optional, Dict, Any


class OllamaServiceError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "OLLAMA_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class OllamaConnectionError(OllamaServiceError):
    def __init__(self, message: str = "Cannot connect to Ollama service", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="OLLAMA_CONNECTION_ERROR",
            status_code=503,
            details=details,
        )


class OllamaTimeoutError(OllamaServiceError):
    def __init__(self, message: str = "Request to Ollama timed out", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="OLLAMA_TIMEOUT",
            status_code=504,
            details=details,
        )


class ModelNotFoundError(OllamaServiceError):
    def __init__(self, model: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Model '{model}' not found in Ollama",
            code="MODEL_NOT_FOUND",
            status_code=404,
            details={"model": model, **(details or {})},
        )


class InvalidResponseError(OllamaServiceError):
    def __init__(self, message: str = "Invalid response from Ollama", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INVALID_RESPONSE",
            status_code=502,
            details=details,
        )


class EmptyPromptError(OllamaServiceError):
    def __init__(self, message: str = "Prompt cannot be empty", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="EMPTY_PROMPT",
            status_code=400,
            details=details,
        )


class ModelPullError(OllamaServiceError):
    def __init__(self, model: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Failed to pull model '{model}': {message}",
            code="MODEL_PULL_ERROR",
            status_code=500,
            details={"model": model, **(details or {})},
        )