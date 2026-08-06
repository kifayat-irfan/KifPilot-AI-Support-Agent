from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any

from app.services.streaming import (
    streaming_service,
    StreamChatRequest,
    StreamHealthResponse,
)
from app.services.streaming.exceptions import (
    StreamingError,
    RetrievalFailedError,
    NoContextFoundError,
    GenerationFailedError,
    OllamaUnavailableError,
    CitationGenerationError,
    StreamingTimeoutError,
    ClientDisconnectedError,
    GuardrailsError,
)
from app.services.streaming.events import SSEFormatter
from app.core.logging import get_logger
from app.presentation.api.v1.dependencies import get_current_active_user, require_chat

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger(__name__)


@router.post(
    "/stream",
    responses={
        200: {"description": "Server-Sent Events stream"},
        400: {"description": "Invalid request"},
        404: {"description": "No relevant context found"},
        408: {"description": "Request timeout"},
        499: {"description": "Client disconnected"},
        500: {"description": "Generation failed"},
        503: {"description": "Ollama service unavailable"},
    },
    dependencies=[Depends(require_chat)],
)
async def stream_chat(
    request: StreamChatRequest,
    http_request: Request,
    current_user = Depends(get_current_active_user),
):
    """
    Stream a chat response using Server-Sent Events (SSE).
    
    The stream emits the following events in order:
    1. `start` - Streaming started
    2. `retrieval` - Retrieval completed with chunk count and timing
    3. `token` - Individual token chunks (multiple)
    4. `citations` - Citations for the answer
    5. `complete` - Final completion with confidence and metadata
    6. `error` - Error event (if any)
    
    **Cancellation:** If the client disconnects, generation stops immediately.
    **Timeout:** Requests exceeding the configured timeout are terminated.
    """
    logger.info(
        "Streaming chat request received",
        question=request.question[:100],
        top_k=request.top_k,
        minimum_score=request.minimum_score,
    )
    
    async def event_generator():
        """Generate SSE events from the streaming service."""
        try:
            async for event in streaming_service.stream_chat(request):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info("Client disconnected during streaming")
                    raise ClientDisconnectedError()
                yield event
        except ClientDisconnectedError:
            logger.info("Client disconnected, stopping generation")
            yield SSEFormatter.format_error("Client disconnected", "CLIENT_DISCONNECTED")
        except StreamingError as e:
            logger.warning("Streaming error", error=e.message, code=e.code)
            yield SSEFormatter.format_error(e.message, e.code)
        except Exception as e:
            logger.error("Unexpected streaming error", error=str(e))
            yield SSEFormatter.format_error("Internal server error", "INTERNAL_ERROR")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/stream/health",
    response_model=StreamHealthResponse,
    responses={
        200: {"model": StreamHealthResponse, "description": "Health check status"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def health_check(current_user = Depends(get_current_active_user)):
    """Check health of streaming service dependencies."""
    response = await streaming_service.health_check()
    return response


@router.post(
    "/ask",
    response_model=dict,
    responses={
        200: {"description": "Complete answer with citations (non-streaming)"},
        400: {"description": "Invalid request"},
        404: {"description": "No relevant context found"},
        500: {"description": "Generation failed"},
    },
    dependencies=[Depends(require_chat)],
)
async def ask_non_streaming(request: StreamChatRequest, current_user = Depends(get_current_active_user)):
    """
    Non-streaming version for clients that don't support SSE.
    Returns the complete answer with citations in a single response.
    """
    logger.info(
        "Non-streaming chat request received",
        question=request.question[:100],
    )
    
    try:
        # Collect all events from streaming service
        events = []
        async for event in streaming_service.stream_chat(request):
            events.append(event)
        
        # Parse events to build response
        answer = ""
        citations = []
        confidence = 0.0
        sources_found = 0
        response_time_ms = 0.0
        
        for event in events:
            if event.startswith("event: token"):
                # Extract token text from SSE
                import json
                lines = event.strip().split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        answer += data.get("text", "")
            elif event.startswith("event: citations"):
                lines = event.strip().split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        citations = data.get("citations", [])
            elif event.startswith("event: complete"):
                lines = event.strip().split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        confidence = data.get("confidence", 0.0)
                        sources_found = data.get("sources_found", 0)
                        response_time_ms = data.get("response_time_ms", 0.0)
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "sources_found": sources_found,
            "response_time_ms": response_time_ms,
        }
        
    except Exception as e:
        logger.error("Non-streaming chat failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )