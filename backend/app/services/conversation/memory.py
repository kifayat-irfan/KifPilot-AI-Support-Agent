from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conversation.repository import ConversationRepository
from app.database.models import ChatMessage, MessageRole
from app.services.conversation.schemas import MemoryConfig
from app.services.conversation.exceptions import MemoryConfigError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Manages conversation history for context injection."""

    DEFAULT_MAX_MESSAGES = 20
    DEFAULT_MAX_TOKENS = 8000

    def __init__(
        self,
        session: AsyncSession,
        config: Optional[MemoryConfig] = None,
    ):
        self._repo = ConversationRepository(session)
        self._config = config or MemoryConfig()

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return len(text) // 4

    def _build_message_dict(self, message: ChatMessage) -> dict:
        """Convert a ChatMessage to a dict for LLM consumption."""
        return {
            "role": message.role.value,
            "content": message.message,
        }

    async def get_context_messages(
        self, session_id: str
    ) -> List[dict]:
        """
        Get conversation history formatted for LLM context.
        
        Returns messages in chronological order, respecting max_messages and max_tokens limits.
        Oldest messages are removed first.
        """
        if self._config.max_messages <= 0:
            return []

        # Get recent messages (we'll filter by tokens after)
        messages = await self._repo.get_recent_messages(
            session_id, limit=self._config.max_messages
        )

        if not messages:
            return []

        # Convert to dict format
        message_dicts = [self._build_message_dict(msg) for msg in messages]

        # Apply token limit
        if self._config.max_tokens > 0:
            message_dicts = self._apply_token_limit(message_dicts)

        logger.debug(
            "Retrieved conversation context",
            session_id=session_id,
            message_count=len(message_dicts),
            config_max_messages=self._config.max_messages,
            config_max_tokens=self._config.max_tokens,
        )

        return message_dicts

    def _apply_token_limit(self, messages: List[dict]) -> List[dict]:
        """Apply token limit by removing oldest messages first."""
        if not messages:
            return []

        total_tokens = sum(
            self._estimate_tokens(msg.get("content", "")) for msg in messages
        )

        if total_tokens <= self._config.max_tokens:
            return messages

        # Remove oldest messages until under token limit
        filtered = []
        current_tokens = 0
        for msg in reversed(messages):  # Start from newest
            msg_tokens = self._estimate_tokens(msg.get("content", ""))
            if current_tokens + msg_tokens <= self._config.max_tokens:
                filtered.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        logger.debug(
            "Applied token limit",
            original_count=len(messages),
            filtered_count=len(filtered),
            original_tokens=total_tokens,
            filtered_tokens=current_tokens,
            max_tokens=self._config.max_tokens,
        )

        return filtered

    async def get_context_for_streaming(
        self, session_id: str
    ) -> List[dict]:
        """
        Get conversation context for streaming chat.
        Includes system prompt if configured.
        """
        context_messages = await self.get_context_messages(session_id)

        if self._config.include_system_prompt and context_messages:
            # Check if first message is already a system message
            has_system = any(m.get("role") == "system" for m in context_messages)
            if not has_system:
                system_prompt = (
                    "You are a helpful AI assistant for customer support. "
                    "Use the provided context to answer questions accurately. "
                    "If you don't know the answer, say so honestly."
                )
                context_messages.insert(0, {"role": "system", "content": system_prompt})

        return context_messages

    def update_config(self, config: MemoryConfig) -> None:
        """Update memory configuration."""
        if config.max_messages < 1 or config.max_messages > 100:
            raise MemoryConfigError("max_messages must be between 1 and 100")
        if config.max_tokens < 1000 or config.max_tokens > 32000:
            raise MemoryConfigError("max_tokens must be between 1000 and 32000")
        self._config = config
        logger.info("Memory config updated", max_messages=config.max_messages, max_tokens=config.max_tokens)

    @property
    def config(self) -> MemoryConfig:
        """Get current memory configuration."""
        return self._config