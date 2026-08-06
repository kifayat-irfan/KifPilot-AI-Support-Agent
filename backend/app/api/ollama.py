from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import json

from app.services.llm import (
    ollama_service,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamChunk,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelsListResponse,
    OllamaHealthResponse,
    ErrorResponse,
    OllamaConnectionError,
    OllamaTimeoutError,
    ModelNotFoundError,
    InvalidResponseError,
    EmptyPromptError,
)
from app.core.logging import get_logger

router = APIRouter(prefix="/ollama", tags=["Ollama"])
logger = get_logger(__name__)


@router.get(
    "/health",
    response_model=OllamaHealthResponse,
    responses={
        200: {"model": OllamaHealthResponse},
        503: {"model": ErrorResponse},
    },
)
async def ollama_health():
    try:
        health = await ollama_service.health_check()
        return health
    except Exception as e:
        logger.error("Ollama health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Health check failed", "detail": str(e), "code": "HEALTH_CHECK_FAILED"},
        )


@router.get(
    "/models",
    response_model=ModelsListResponse,
    responses={
        200: {"model": ModelsListResponse},
        503: {"model": ErrorResponse},
    },
)
async def list_models():
    try:
        return await ollama_service.list_models()
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("List models failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to list models", "detail": str(e), "code": "LIST_MODELS_FAILED"},
        )


@router.post(
    "/chat",
    response_model=ChatCompletionResponse,
    responses={
        200: {"model": ChatCompletionResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def chat_completion(request: ChatCompletionRequest):
    try:
        return await ollama_service.chat_completion(request)
    except EmptyPromptError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except InvalidResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Chat completion failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Chat completion failed", "detail": str(e), "code": "CHAT_FAILED"},
        )


@router.post(
    "/chat/stream",
    responses={
        200: {"description": "Streaming chat response"},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def chat_stream(request: ChatCompletionRequest):
    try:
        async def generate():
            async for chunk in ollama_service.chat_stream(request):
                yield f"data: {chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except EmptyPromptError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except InvalidResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Chat stream failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Chat stream failed", "detail": str(e), "code": "CHAT_STREAM_FAILED"},
        )


@router.post(
    "/embeddings",
    response_model=EmbeddingResponse,
    responses={
        200: {"model": EmbeddingResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def generate_embeddings(request: EmbeddingRequest):
    try:
        return await ollama_service.generate_embeddings(request)
    except EmptyPromptError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except OllamaTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except InvalidResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Embedding generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Embedding generation failed", "detail": str(e), "code": "EMBEDDING_FAILED"},
        )