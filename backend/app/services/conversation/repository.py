from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, update
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database.models import ChatSession, ChatMessage, MessageRole
from app.services.conversation.exceptions import (
    SessionNotFoundError,
    MessageNotFoundError,
    SessionCreationError,
    MessageSaveError,
    SessionDeletionError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationRepository:
    """Repository for conversation database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_session(self, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        try:
            chat_session = ChatSession(title=title)
            self._session.add(chat_session)
            await self._session.flush()
            await self._session.refresh(chat_session)
            logger.info("Session created", session_id=chat_session.id, title=title)
            return chat_session
        except Exception as e:
            logger.error("Failed to create session", error=str(e))
            raise SessionCreationError(str(e))

    async def get_session(self, session_id: str) -> ChatSession:
        """Get a session by ID."""
        result = await self._session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError(session_id)
        return session

    async def get_session_with_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> ChatSession:
        """Get a session with its messages."""
        query = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await self._session.execute(query)
        session = result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError(session_id)

        # Sort messages by created_at
        session.messages.sort(key=lambda m: m.created_at)

        if limit and len(session.messages) > limit:
            session.messages = session.messages[-limit:]

        return session

    async def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "last_activity",
        sort_order: str = "desc",
    ) -> Tuple[List[ChatSession], int]:
        """List sessions with pagination and sorting."""
        # Build sort column
        sort_column = getattr(ChatSession, sort_by, ChatSession.last_activity)
        if sort_order == "desc":
            sort_column = desc(sort_column)
        else:
            sort_column = asc(sort_column)

        # Count total
        count_result = await self._session.execute(
            select(func.count(ChatSession.id))
        )
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self._session.execute(
            select(ChatSession)
            .order_by(sort_column)
            .offset(offset)
            .limit(page_size)
        )
        sessions = list(result.scalars().all())

        return sessions, total

    async def update_session(
        self, session_id: str, title: Optional[str] = None
    ) -> ChatSession:
        """Update session title."""
        session = await self.get_session(session_id)
        if title is not None:
            session.title = title
            session.updated_at = datetime.utcnow()
            await self._session.flush()
            await self._session.refresh(session)
        return session

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        try:
            session = await self.get_session(session_id)
            await self._session.delete(session)
            await self._session.flush()
            logger.info("Session deleted", session_id=session_id)
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete session", session_id=session_id, error=str(e))
            raise SessionDeletionError(session_id, str(e))

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        message: str,
        citations: Optional[List[dict]] = None,
        confidence: Optional[float] = None,
        token_count: Optional[int] = None,
        response_time_ms: Optional[float] = None,
    ) -> ChatMessage:
        """Add a message to a session."""
        try:
            # Verify session exists
            session = await self.get_session(session_id)

            chat_message = ChatMessage(
                session_id=session_id,
                role=role,
                message=message,
                citations_json=citations,
                confidence=confidence,
                token_count=token_count,
                response_time_ms=response_time_ms,
            )
            self._session.add(chat_message)

            # Update session message count and last_activity
            session.message_count += 1
            session.last_activity = datetime.utcnow()
            session.updated_at = datetime.utcnow()

            await self._session.flush()
            await self._session.refresh(chat_message)

            logger.info(
                "Message saved",
                session_id=session_id,
                message_id=chat_message.id,
                role=role.value,
                token_count=token_count,
            )
            return chat_message
        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to save message", session_id=session_id, error=str(e))
            raise MessageSaveError(str(e))

    async def get_messages(
        self, session_id: str, limit: Optional[int] = None, offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages for a session."""
        await self.get_session(session_id)  # Verify session exists

        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_recent_messages(
        self, session_id: str, limit: int
    ) -> List[ChatMessage]:
        """Get the most recent messages for a session."""
        await self.get_session(session_id)  # Verify session exists

        result = await self._session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological order
        return messages

    async def count_messages(self, session_id: str) -> int:
        """Count messages in a session."""
        result = await self._session.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        return result.scalar() or 0

    async def update_session_activity(self, session_id: str) -> None:
        """Update session last_activity timestamp."""
        await self._session.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(last_activity=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        await self._session.flush()