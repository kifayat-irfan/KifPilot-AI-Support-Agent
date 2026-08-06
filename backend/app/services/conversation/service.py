from typing import Optional, List, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import time
import asyncio

from app.services.rag.prompt_builder import PromptBuilder
from app.services.streaming.events import SSEFormatter
from app.services.conversation.repository import ConversationRepository
from app.services.conversation.session import SessionService
from app.services.conversation.memory import ConversationMemory, MemoryConfig
from app.database.models import ChatMessage, MessageRole
from app.services.conversation.schemas import (
    StreamChatWithSessionRequest,
    ChatConversationResponse,
    ChatSessionResponse,
)
from app.services.conversation.exceptions import (
    SessionNotFoundError,
    SessionCreationError,
    MessageSaveError,
)
from app.services.retrieval import retrieval_service
from app.services.retrieval.schemas import RetrievalContextRequest, RetrievalFilters
from app.services.citations import citation_service
from app.services.citations.formatter import CitationBuilder
from app.services.rag.schemas import RAGSource
from app.services.rag import rag_service
from app.services.llm import ollama_service
from app.services.llm.models import ChatCompletionRequest, ChatMessage as LLMChatMessage, ModelRole
from app.core.logging import get_logger
from app.core.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class ConversationService:
    """Main conversation service orchestrating sessions, memory, and streaming."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = ConversationRepository(session)
        self._session_service = SessionService(session)

    async def create_session(self, title: Optional[str] = None) -> ChatSessionResponse:
        """Create a new chat session."""
        from app.services.conversation.schemas import ChatSessionCreate
        request = ChatSessionCreate(title=title)
        return await self._session_service.create_session(request)

    async def get_session(self, session_id: str) -> ChatSessionResponse:
        """Get a session by ID."""
        return await self._session_service.get_session(session_id)

    async def get_conversation(self, session_id: str) -> ChatConversationResponse:
        """Get full conversation with messages."""
        return await self._session_service.get_conversation(session_id)

    async def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "last_activity",
        sort_order: str = "desc",
    ):
        """List sessions with pagination."""
        from app.services.conversation.schemas import SessionListParams
        params = SessionListParams(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return await self._session_service.list_sessions(params)

    async def update_session_title(self, session_id: str, title: str) -> ChatSessionResponse:
        """Update session title."""
        from app.services.conversation.schemas import ChatSessionUpdate
        request = ChatSessionUpdate(title=title)
        return await self._session_service.update_session(session_id, request)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        await self._session_service.delete_session(session_id)

    async def stream_chat_with_session(
        self,
        request: StreamChatWithSessionRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat with conversation memory and auto-save.
        
        Pipeline:
        1. Get or create session
        2. Retrieve conversation history for context
        3. Retrieve relevant documents (RAG)
        4. Build prompt with conversation history + retrieved context
        5. Stream response
        6. Auto-save question and answer with citations
        7. Auto-generate title if needed
        """
        start_time = time.time()
        session_id = request.session_id
        created_new_session = False

        try:
            # Step 1: Get or create session
            if session_id:
                try:
                    await self._repo.get_session(session_id)
                except SessionNotFoundError:
                    # Session doesn't exist, create new one
                    session = await self._repo.create_session()
                    session_id = session.id
                    created_new_session = True
            else:
                # Create new session
                session = await self._repo.create_session()
                session_id = session.id
                created_new_session = True

            logger.info(
                "Streaming chat with session",
                session_id=session_id,
                created_new=created_new_session,
                question=request.question[:100],
            )

            # Step 2: Get conversation context
            memory_config = request.memory_config or MemoryConfig()
            memory = ConversationMemory(self._session, memory_config)
            conversation_history = await memory.get_context_for_streaming(session_id)

            # Step 3: Retrieve relevant documents (RAG)
            retrieval_request = RetrievalContextRequest(
                query=request.question,
                top_k=request.top_k,
                minimum_score=request.minimum_score,
                filters=RetrievalFilters(**request.filters) if request.filters else None,
                max_context_chars=8000,
            )
            
            context_response = await retrieval_service.build_context(retrieval_request)

            if not context_response.sources:
                logger.info("No sources found", question=request.question[:100])
                # Still need to yield events for the streaming response
                formatter = SSEFormatter()
                yield formatter.format_start()
                yield formatter.format_error(
                    "I cannot find this information in the indexed documentation.",
                    "NO_CONTEXT_FOUND"
                )
                return

            # Step 4: Build citations from sources
            citations = CitationBuilder.from_rag_sources(context_response.sources)

            # Step 5: Build prompt with conversation history + retrieved context
            # Convert sources to RAGSource format
            sources = []
            for s in context_response.sources:
                sources.append(RAGSource(
                    document_id=s.document_id,
                    document_name=s.document_name,
                    chunk_id=s.chunk_id,
                    chunk_index=s.chunk_index,
                    page=s.page,
                    section=s.section,
                    similarity_score=s.similarity_score,
                ))

            # Build prompt with conversation history
            prompt_messages = PromptBuilder.build_prompt_with_sources_and_history(
                request.question,
                context_response.context,
                sources,
                conversation_history
            )

            # Step 6: Stream from Ollama with custom prompt
            chat_request = ChatCompletionRequest(
                messages=[LLMChatMessage(role=ModelRole(m["role"]), content=m["content"]) for m in prompt_messages],
                model=settings.OLLAMA_CHAT_MODEL,
                temperature=0.0,
                top_p=1.0,
                max_tokens=2048,
                stream=True,
            )

            # Step 7: Stream response and collect for saving
            formatter = SSEFormatter()
            full_answer_parts = []
            citations_data = None
            confidence = 0.0
            sources_found = 0
            response_time_ms = 0.0
            token_count = 0

            # Emit start event
            yield formatter.format_start()

            # Emit retrieval event
            yield formatter.format_retrieval(
                chunks_found=len(context_response.sources),
                search_time_ms=context_response.search_time_ms
            )

            # Stream tokens from Ollama
            try:
                stream = await asyncio.wait_for(
                    ollama_service.chat_stream(chat_request),
                    timeout=120
                )

                async for chunk in stream:
                    if chunk.message.content:
                        text = chunk.message.content
                        full_answer_parts.append(text)
                        token_count += 1
                        yield formatter.format_token(text)

                        if chunk.done:
                            break

            except asyncio.TimeoutError:
                logger.error("Streaming timeout", session_id=session_id)
                yield formatter.format_error("Request timeout", "STREAMING_TIMEOUT")
                return
            except Exception as e:
                logger.error("Streaming generation failed", session_id=session_id, error=str(e))
                yield formatter.format_error(f"Generation failed: {str(e)}", "GENERATION_FAILED")
                return

            full_answer = "".join(full_answer_parts)

            if not full_answer.strip():
                full_answer = "I cannot find this information in the indexed documentation."

            # Step 8: Emit citations
            citation_data = []
            for citation in citations:
                citation_data.append({
                    "document_id": citation.document_id,
                    "document_name": citation.document_name,
                    "page_number": citation.page_number,
                    "section": citation.section,
                    "chunk_id": citation.chunk_id,
                    "chunk_index": citation.chunk_index,
                    "similarity_score": citation.similarity_score,
                })

            yield formatter.format_citations(citation_data)

            # Step 9: Calculate confidence
            confidence = rag_service._calculate_confidence(
                sources=sources,
                context_chars=context_response.total_chars,
                answer=full_answer,
            )

            # Step 10: Emit completion
            total_time_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                "Streaming chat completed",
                question=request.question[:100],
                answer_length=len(full_answer),
                token_count=token_count,
                citations_count=len(citations),
                confidence=round(confidence, 4),
                total_time_ms=total_time_ms,
            )

            yield formatter.format_complete(
                confidence=confidence,
                sources_found=len(citations),
                response_time_ms=total_time_ms
            )

            # Step 11: Save messages
            # Save user question
            await self._repo.add_message(
                session_id=session_id,
                role=MessageRole.USER,
                message=request.question,
            )

            # Save assistant answer
            await self._repo.add_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                message=full_answer,
                citations=citation_data,
                confidence=confidence,
                token_count=token_count,
                response_time_ms=total_time_ms,
            )

            # Step 12: Auto-generate title if this was the first user message
            if created_new_session:
                await self._session_service.auto_update_title_if_needed(session_id)

            logger.info(
                "Conversation saved",
                session_id=session_id,
                question_length=len(request.question),
                answer_length=len(full_answer),
                token_count=token_count,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(
                "Streaming chat with session failed",
                session_id=session_id,
                error=str(e),
            )
            # Re-raise to let the caller handle it
            raise

    async def ask_with_session(
        self,
        request: StreamChatWithSessionRequest,
    ) -> dict:
        """
        Non-streaming version that returns complete response.
        """
        events = []
        async for event in self.stream_chat_with_session(request):
            events.append(event)

        # Parse events to build response
        answer = ""
        citations = []
        confidence = 0.0
        sources_found = 0
        response_time_ms = 0.0

        for event in events:
            if event.startswith("event: token"):
                import json
                lines = event.strip().split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        answer += data.get("text", "")
            elif event.startswith("event: citations"):
                import json
                lines = event.strip().split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        citations = data.get("citations", [])
            elif event.startswith("event: complete"):
                import json
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
            "session_id": request.session_id,
        }