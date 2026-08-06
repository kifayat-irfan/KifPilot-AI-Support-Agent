from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class ModelRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ModelRole
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    model: str
    message: ChatMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class ChatStreamChunk(BaseModel):
    model: str
    message: ChatMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class EmbeddingRequest(BaseModel):
    input: List[str] = Field(..., min_length=1)
    model: Optional[str] = None


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None


class ModelInfo(BaseModel):
    name: str
    modified_at: Optional[str] = None
    size: Optional[int] = None
    digest: Optional[str] = None
    details: Optional[dict] = None


class ModelsListResponse(BaseModel):
    models: List[ModelInfo]


class OllamaHealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    ollama_running: bool
    chat_model_available: bool
    embed_model_available: bool
    base_url: str
    chat_model: str
    embed_model: str
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: str