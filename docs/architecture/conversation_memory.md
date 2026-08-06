# Conversation Memory

## Overview

Persistent conversation management with context injection for multi-turn dialogues.

## Data Model

```python
# database/models.py
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"))
    organization_id = Column(UUID, ForeignKey("organizations.id"))
    title = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    messages = relationship("ConversationMessage", back_populates="conversation")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID, ForeignKey("conversations.id"))
    role = Column(Enum(MessageRole))  # user, assistant, system
    content = Column(Text)
    citations = Column(JSON, default=list)  # Citation references
    metadata = Column(JSON, default=dict)   # Model, tokens, confidence
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
```

## Conversation Service

```python
# services/conversation/service.py
class ConversationService:
    def __init__(
        self,
        repo: ConversationRepository,
        rag_service: RAGService,
        max_history: int = 20,
        max_context_tokens: int = 4000
    ):
        self.repo = repo
        self.rag = rag_service
        self.max_history = max_history
        self.max_context_tokens = max_context_tokens
    
    async def create_conversation(
        self,
        user_id: str,
        org_id: str,
        title: str = None
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            organization_id=org_id,
            title=title or "New Conversation"
        )
        return await self.repo.create(conversation)
    
    async def send_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        stream: bool = False
    ) -> Union[ConversationMessage, AsyncGenerator[ChatEvent, None]]:
        # 1. Verify ownership
        conversation = await self.repo.get(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        
        # 2. Save user message
        user_msg = ConversationMessage(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content
        )
        await self.repo.add_message(user_msg)
        
        # 3. Get conversation history for context
        history = await self._get_formatted_history(conversation_id)
        
        # 4. Query RAG with history
        if stream:
            return self._stream_rag_response(
                question=content,
                conversation_id=conversation_id,
                history=history
            )
        else:
            return await self._complete_rag_response(
                question=content,
                conversation_id=conversation_id,
                history=history
            )
    
    async def _get_formatted_history(
        self,
        conversation_id: str
    ) -> List[ChatMessage]:
        messages = await self.repo.get_messages(
            conversation_id,
            limit=self.max_history
        )
        
        return [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in reversed(messages)  # Oldest first
        ]
    
    async def _stream_rag_response(
        self,
        question: str,
        conversation_id: str,
        history: List[ChatMessage]
    ) -> AsyncGenerator[ChatEvent, None]:
        # Build RAG prompt with history
        prompt = await self.rag_prompt_builder.build_with_history(
            question=question,
            history=history,
            context=await self._get_relevant_context(question)
        )
        
        full_answer = ""
        async for token in self.llm.stream_generate(prompt):
            yield ChatEvent(event="token", data={"text": token})
            full_answer += token
        
        # Save assistant message
        await self.repo.add_message(ConversationMessage(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=full_answer,
            citations=[],  # Extracted from RAG
            metadata={"model": "qwen3.5:4b"}
        ))
        
        yield ChatEvent(event="complete", data={"answer": full_answer})
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> ConversationWithMessages:
        conversation = await self.repo.get(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        
        messages = await self.repo.get_messages(conversation_id)
        
        return ConversationWithMessages(
            conversation=conversation,
            messages=messages
        )
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        conversation = await self.repo.get(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ConversationNotFoundError(conversation_id)
        
        # Soft delete
        conversation.deleted_at = datetime.utcnow()
        await self.repo.update(conversation)
        return True
```

## Context Injection

```python
# services/rag/prompt_builder.py
class RAGPromptBuilder:
    async def build_with_history(
        self,
        question: str,
        history: List[ChatMessage],
        context: CompressedContext,
        max_history_tokens: int = 2000
    ) -> str:
        # Build history section
        history_text = ""
        if history:
            history_parts = []
            used_tokens = 0
            
            for msg in reversed(history):  # Most recent first
                msg_tokens = self.tokenizer(msg.content)
                if used_tokens + msg_tokens > max_history_tokens:
                    break
                history_parts.append(f"{msg.role.upper()}: {msg.content}")
                used_tokens += msg_tokens
            
            history_text = "\n".join(reversed(history_parts))  # Chronological
        
        # Build full prompt
        parts = [self.SYSTEM_PROMPT, "\n"]
        
        if context.citations:
            parts.append("Knowledge Base Context:\n")
            parts.append(context.context)
            parts.append("\n")
        
        if history_text:
            parts.append("Conversation History:\n")
            parts.append(history_text)
            parts.append("\n")
        
        parts.append(f"Current Question: {question}\n\n")
        parts.append("Answer:")
        
        return "".join(parts)
```

## Conversation API

```python
# presentation/api/v1/routes/conversations.py
@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    service: ConversationService = Depends(get_conversation_service)
):
    conversation = await service.create_conversation(
        user_id=current_user.id,
        org_id=current_user.organization_id,
        title=request.title
    )
    return ConversationResponse.from_orm(conversation)

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_user),
    service: ConversationService = Depends(get_conversation_service)
):
    conversations, total = await service.list_user_conversations(
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    return ConversationListResponse(
        conversations=conversations,
        total=total,
        page=page,
        page_size=page_size
    )

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    service: ConversationService = Depends(get_conversation_service)
):
    if request.stream:
        async def event_generator():
            async for event in service.send_message(
                conversation_id=conversation_id,
                user_id=current_user.id,
                content=request.content,
                stream=True
            ):
                if await http_request.is_disconnected():
                    break
                yield self._format_event(event.event, event.data)
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    else:
        result = await service.send_message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            content=request.content,
            stream=False
        )
        return result

@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ConversationService = Depends(get_conversation_service)
):
    conversation = await service.get_conversation(conversation_id, current_user.id)
    return MessageListResponse(messages=conversation.messages)

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    service: ConversationService = Depends(get_conversation_service)
):
    await service.delete_conversation(conversation_id, current_user.id)
    return {"success": True, "message": "Conversation deleted"}
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Conversation
    CONVERSATION_MAX_HISTORY: int = 20
    CONVERSATION_MAX_HISTORY_TOKENS: int = 4000
    CONVERSATION_MAX_TITLE_LENGTH: int = 500
    CONVERSATION_AUTO_TITLE: bool = True
    CONVERSATION_TITLE_MAX_LENGTH: int = 100
```

## Monitoring

```python
conversation_create_time = Histogram("conversation_create_seconds")
conversation_messages_total = Counter("conversation_messages_total", "Messages", ["role"])
conversation_history_tokens = Histogram("conversation_history_tokens", "History tokens used")
conversation_active = Gauge("conversation_active", "Active conversations")
```