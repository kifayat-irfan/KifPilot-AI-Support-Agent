from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conversation.repository import ConversationRepository
from app.services.conversation.schemas import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatSessionUpdate,
    SessionListParams,
    ChatConversationResponse,
    ChatMessageResponse,
)
from app.services.conversation.exceptions import SessionNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionService:
    """Service for managing chat sessions."""

    def __init__(self, session: AsyncSession):
        self._repo = ConversationRepository(session)

    async def create_session(self, request: ChatSessionCreate) -> ChatSessionResponse:
        """Create a new chat session."""
        chat_session = await self._repo.create_session(title=request.title)
        return ChatSessionResponse.model_validate(chat_session)

    async def get_session(self, session_id: str) -> ChatSessionResponse:
        """Get a session by ID."""
        chat_session = await self._repo.get_session(session_id)
        return ChatSessionResponse.model_validate(chat_session)

    async def get_conversation(self, session_id: str) -> ChatConversationResponse:
        """Get a session with all its messages."""
        chat_session = await self._repo.get_session_with_messages(session_id)
        session_response = ChatSessionResponse.model_validate(chat_session)
        messages = [
            ChatMessageResponse.model_validate(msg) for msg in chat_session.messages
        ]
        return ChatConversationResponse(session=session_response, messages=messages)

    async def list_sessions(self, params: SessionListParams) -> ChatSessionListResponse:
        """List sessions with pagination and sorting."""
        sessions, total = await self._repo.list_sessions(
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        session_responses = [
            ChatSessionResponse.model_validate(s) for s in sessions
        ]
        return ChatSessionListResponse(
            sessions=session_responses,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def update_session(
        self, session_id: str, request: ChatSessionUpdate
    ) -> ChatSessionResponse:
        """Update session title."""
        chat_session = await self._repo.update_session(session_id, title=request.title)
        return ChatSessionResponse.model_validate(chat_session)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        await self._repo.delete_session(session_id)
        logger.info("Session deleted via service", session_id=session_id)

    async def generate_title_from_first_message(self, session_id: str) -> str:
        """Generate a session title from the first user message."""
        messages = await self._repo.get_messages(session_id, limit=1)
        if not messages:
            return "New Conversation"

        first_message = messages[0].message
        # Truncate to 60 characters
        title = first_message[:60].strip()
        if len(first_message) > 60:
            title = title.rsplit(" ", 1)[0] + "..."

        return title or "New Conversation"

    async def auto_update_title_if_needed(self, session_id: str) -> None:
        """Auto-generate title from first user message if session has no title."""
        session = await self._repo.get_session(session_id)
        if not session.title:
            title = await self.generate_title_from_first_message(session_id)
            await self._repo.update_session(session_id, title=title)
            logger.info("Auto-generated session title", session_id=session_id, title=title)