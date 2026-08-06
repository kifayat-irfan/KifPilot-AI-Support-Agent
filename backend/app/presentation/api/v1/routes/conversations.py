from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.core.database import get_db_session
from app.services.conversation import (
    ConversationService,
    ConversationMemory,
    MemoryConfig,
    StreamChatWithSessionRequest,
    ChatSessionCreate,
    ChatSessionUpdate,
    SessionListParams,
    ChatConversationResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.conversation.exceptions import (
    SessionNotFoundError,
    SessionCreationError,
    SessionDeletionError,
    MemoryConfigError,
)
from app.services.streaming import streaming_service, StreamChatRequest
from app.services.streaming.events import SSEFormatter
from app.core.logging import get_logger
from app.presentation.api.v1.dependencies import get_current_active_user, require_chat, require_view_sessions

router = APIRouter(prefix="/chat/session", tags=["Chat Sessions"])
logger = get_logger(__name__)


def get_conversation_service(db: AsyncSession = Depends(get_db_session)) -> ConversationService:
    return ConversationService(db)


@router.post(
    "",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Session created successfully"},
        500: {"description": "Failed to create session"},
    },
    dependencies=[Depends(require_view_sessions)],
)
async def create_session(
    request: ChatSessionCreate,
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """Create a new chat session."""
    try:
        session = await service.create_session(title=request.title)
        logger.info("Session created via API", session_id=session.id, title=request.title)
        return session
    except SessionCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "code": e.code},
        )


@router.get(
    "",
    response_model=ChatSessionListResponse,
    responses={
        200: {"description": "List of sessions"},
        400: {"description": "Invalid pagination parameters"},
    },
    dependencies=[Depends(require_view_sessions)],
)
async def list_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(
        "last_activity",
        pattern="^(created_at|updated_at|last_activity|message_count|title)$",
        description="Field to sort by",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """List chat sessions with pagination and sorting."""
    params = SessionListParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await service.list_sessions(params)


@router.get(
    "/{session_id}",
    response_model=ChatConversationResponse,
    responses={
        200: {"description": "Complete conversation with messages"},
        404: {"description": "Session not found"},
    },
    dependencies=[Depends(require_view_sessions)],
)
async def get_session(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """Get a session with all its messages."""
    try:
        return await service.get_conversation(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.patch(
    "/{session_id}",
    response_model=ChatSessionResponse,
    responses={
        200: {"description": "Session updated successfully"},
        404: {"description": "Session not found"},
    },
    dependencies=[Depends(require_view_sessions)],
)
async def update_session(
    session_id: str,
    request: ChatSessionUpdate,
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """Update session title."""
    try:
        return await service.update_session_title(session_id, request.title)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Session deleted successfully"},
        404: {"description": "Session not found"},
        500: {"description": "Failed to delete session"},
    },
    dependencies=[Depends(require_view_sessions)],
)
async def delete_session(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """Delete a session and all its messages."""
    try:
        await service.delete_session(session_id)
        logger.info("Session deleted via API", session_id=session_id)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )
    except SessionDeletionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "code": e.code},
        )


@router.post(
    "/{session_id}/stream",
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
async def stream_chat_with_session(
    session_id: str,
    request: StreamChatWithSessionRequest,
    http_request: Request,
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """
    Stream a chat response with conversation memory and auto-save.
    
    The session_id in the path takes precedence over request.session_id.
    If session doesn't exist, a new one will be created.
    
    The stream emits the following events in order:
    1. `start` - Streaming started
    2. `retrieval` - Retrieval completed with chunk count and timing
    3. `token` - Individual token chunks (multiple)
    4. `citations` - Citations for the answer
    5. `complete` - Final completion with confidence and metadata
    6. `error` - Error event (if any)
    
    **Auto-save:** Question, answer, citations, confidence, and timing are automatically saved.
    **Title generation:** Session title is auto-generated from first user message (max 60 chars).
    **Memory:** Previous conversation context is included based on memory_config.
    """
    # Override session_id from path
    request.session_id = session_id

    logger.info(
        "Streaming chat with session request received",
        session_id=session_id,
        question=request.question[:100],
        top_k=request.top_k,
        minimum_score=request.minimum_score,
    )

    async def event_generator():
        """Generate SSE events from the conversation service."""
        try:
            async for event in service.stream_chat_with_session(request):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info("Client disconnected during streaming", session_id=session_id)
                    yield SSEFormatter.format_error("Client disconnected", "CLIENT_DISCONNECTED")
                    return
                yield event
        except Exception as e:
            logger.error("Streaming error", session_id=session_id, error=str(e))
            yield SSEFormatter.format_error(str(e), "INTERNAL_ERROR")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{session_id}/ask",
    response_model=dict,
    responses={
        200: {"description": "Complete answer with citations (non-streaming)"},
        400: {"description": "Invalid request"},
        404: {"description": "No relevant context found"},
        500: {"description": "Generation failed"},
        503: {"description": "Ollama service unavailable"},
    },
    dependencies=[Depends(require_chat)],
)
async def ask_with_session(
    session_id: str,
    request: StreamChatWithSessionRequest,
    service: ConversationService = Depends(get_conversation_service),
    current_user = Depends(get_current_active_user),
):
    """
    Non-streaming version for clients that don't support SSE.
    Returns the complete answer with citations in a single response.
    Includes conversation memory and auto-save.
    """
    request.session_id = session_id

    logger.info(
        "Non-streaming chat with session request received",
        session_id=session_id,
        question=request.question[:100],
    )

    try:
        return await service.ask_with_session(request)
    except Exception as e:
        logger.error("Non-streaming chat with session failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )