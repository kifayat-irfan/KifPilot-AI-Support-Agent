# Streaming Pipeline

## Overview

Server-Sent Events (SSE) based streaming for real-time chat responses with token-by-token delivery.

## Architecture

```
Client                          Server
  │                                │
  ├─ POST /chat/stream ──────────► │
  │  { question, top_k }          ├─ Auth, rate limit
  │                                ├─ Create generator
  │                                │
  │ ◄── 200 OK (text/event-stream)─┤
  │                                │
  ├─ Event: start ◄────────────────┤  { session_id }
  ├─ Event: retrieval ◄────────────┤  { chunks, time_ms }
  ├─ Event: token ◄────────────────┤  { text } (repeated)
  ├─ Event: citations ◄────────────┤  { citations[] }
  ├─ Event: complete ◄─────────────┤  { answer, confidence }
  │                                │
  │ (disconnect)                   ├─ Cancel generation
```

## SSE Format

```
event: start
data: {"session_id": "abc-123"}

event: retrieval
data: {"chunks_found": 12, "time_ms": 45}

event: token
data: {"text": "The"}

event: token
data: {"text": " return"}

event: token
data: {"text": " policy"}

event: citations
data: {"citations": [{"id": "[1]", "text": "...", "score": 0.92}]}

event: complete
data: {"answer": "The return policy...", "confidence": 0.89, "sources_found": 3, "response_time_ms": 1250}

event: error
data: {"message": "Generation failed", "code": "GENERATION_ERROR"}
```

## Streaming Service

```python
# services/streaming/service.py
class StreamingService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        citation_extractor: CitationExtractor,
        guardrails: GuardrailsService,
        settings: Settings
    ):
        self.retrieval = retrieval_service
        self.llm = llm_service
        self.prompt_builder = prompt_builder
        self.citations = citation_extractor
        self.guardrails = guardrails
        self.settings = settings
    
    async def stream_chat(
        self,
        request: StreamChatRequest
    ) -> AsyncGenerator[str, None]:
        """Main streaming entry point"""
        session_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        
        try:
            # 1. Input guardrails
            guard = await self.guardrails.check_input(request.question)
            if not guard.allowed:
                yield self._format_error(guard.message, "GUARDRAILS_INPUT")
                return
            
            # 2. Retrieval
            retrieval_start = time.perf_counter()
            retrieval_results = await self.retrieval.search_with_rerank(
                query=request.question,
                org_id=request.organization_id,
                kb_ids=request.kb_ids,
                top_k=request.top_k,
                minimum_score=request.minimum_score,
                filters=request.filters
            )
            retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000
            
            # 3. Build context with citations
            context = self.context_compressor.build_context(
                request.question,
                retrieval_results.results
            )
            
            # 4. Send start event
            yield self._format_event("start", {"session_id": session_id})
            
            # 5. Send retrieval event
            yield self._format_event("retrieval", {
                "chunks_found": len(context.citations),
                "time_ms": round(retrieval_time_ms)
            })
            
            # 6. Build prompt
            prompt = await self.prompt_builder.build_rag_prompt(
                question=request.question,
                context=context
            )
            
            # 6. Stream tokens
            full_answer = ""
            token_count = 0
            
            async for token in self.llm.stream_generate(prompt):
                # Check client disconnect
                if await self._check_disconnected():
                    logger.info(f"Client disconnected during streaming: {session_id}")
                    break
                
                full_answer += token
                token_count += 1
                
                yield self._format_event("token", {"text": token})
            
            # 7. Extract citations from generated answer
            answer_citations = self.citations.extract(full_answer, context.citations)
            
            # 8. Output guardrails
            guard = await self.guardrails.check_output(full_answer)
            if not guard.allowed:
                yield self._format_error(guard.message, "GUARDRAILS_OUTPUT")
                return
            
            # 9. Citations event
            yield self._format_event("citations", {
                "citations": [c.to_dict() for c in answer_citations]
            })
            
            # 10. Complete event
            total_time_ms = (time.perf_counter() - start_time) * 1000
            confidence = self._calculate_confidence(full_answer, answer_citations)
            
            yield self._format_event("complete", {
                "answer": full_answer,
                "citations": [c.to_dict() for c in answer_citations],
                "confidence": confidence,
                "sources_found": len(context.citations),
                "response_time_ms": round(total_time_ms),
                "tokens_generated": token_count
            })
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield self._format_error(str(e), "STREAM_ERROR")
    
    def _format_event(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
    
    def _format_error(self, message: str, code: str) -> str:
        return self._format_event("error", {"message": message, "code": code})
    
    async def _check_disconnected(self) -> bool:
        # In FastAPI, check request.is_disconnected()
        # This is called from the endpoint with request context
        return False
```

## SSE Endpoint

```python
# presentation/api/v1/routes/streaming.py
@router.post(
    "/stream",
    responses={
        200: {"description": "Server-Sent Events stream"},
        400: {"description": "Invalid request"},
        408: {"description": "Request timeout"},
        499: {"description": "Client disconnected"},
        500: {"description": "Generation failed"},
    },
    dependencies=[Depends(require_chat)]
)
async def stream_chat(
    request: StreamChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    streaming_service: StreamingService = Depends(get_streaming_service)
):
    """Stream chat response using SSE"""
    
    async def event_generator():
        try:
            async for event in streaming_service.stream_chat(request):
                # Check client disconnect
                if await http_request.is_disconnected():
                    logger.info("Client disconnected, stopping stream")
                    break
                yield event
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield SSEFormatter.format_error(str(e), "STREAM_ERROR")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

## Frontend SSE Consumer

```typescript
// src/services/chat.ts
export async function* streamChat(
  question: string,
  options: ChatOptions = {}
): AsyncGenerator<ChatEvent> {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`
    },
    body: JSON.stringify({ question, ...options })
  });
  
  if (!response.ok) {
    throw new Error(`Stream failed: ${response.status}`);
  }
  
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    
    for (const line of lines) {
      if (line.startsWith('event: ') || line.startsWith('data: ')) {
        yield parseSSEEvent(line);
      }
    }
  }
}

function parseSSEEvent(line: string): ChatEvent {
  if (line.startsWith('event: ')) {
    currentEvent = line.slice(7).trim();
    return { type: 'event', event: currentEvent };
  }
  
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6));
    return { type: 'data', event: currentEvent, data };
  }
  
  return { type: 'unknown' };
}

// Usage
async function handleStreamChat(question: string) {
  const messages = [];
  
  for await (const event of streamChat(question)) {
    switch (event.event) {
      case 'start':
        setSessionId(event.data.session_id);
        break;
      case 'retrieval':
        setRetrievalInfo(event.data);
        break;
      case 'token':
        appendToMessage(event.data.text);
        break;
      case 'citations':
        setCitations(event.data.citations);
        break;
      case 'complete':
        finalizeMessage(event.data);
        break;
      case 'error':
        handleError(event.data);
        break;
    }
  }
}
```

## Client Disconnect Handling

```python
# presentation/api/v1/routes/streaming.py
async def event_generator():
    try:
        async for event in streaming_service.stream_chat(request):
            # Critical: check disconnect BEFORE yielding
            if await http_request.is_disconnected():
                logger.info("Client disconnected, cancelling generation")
                # Signal cancellation to streaming service
                await streaming_service.cancel_session(session_id)
                break
            yield event
    except asyncio.CancelledError:
        logger.info("Stream cancelled by client disconnect")
        await streaming_service.cancel_session(session_id)
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield SSEFormatter.format_error(str(e), "STREAM_ERROR")

# In streaming service
class StreamingService:
    def __init__(self):
        self._active_sessions: Dict[str, asyncio.Event] = {}
    
    async def stream_chat(self, request):
        session_id = str(uuid.uuid4())
        cancel_event = asyncio.Event()
        self._active_sessions[session_id] = cancel_event
        
        try:
            async for token in self.llm.stream_generate(prompt):
                # Check cancel event
                if cancel_event.is_set():
                    break
                yield token
        finally:
            self._active_sessions.pop(session_id, None)
    
    async def cancel_session(self, session_id: str):
        if session_id in self._active_sessions:
            self._active_sessions[session_id].set()
```

## Timeout Handling

```python
# presentation/api/v1/routes/streaming.py
async def stream_chat(
    request: StreamChatRequest,
    http_request: Request,
    streaming_service: StreamingService = Depends(get_streaming_service)
):
    # Overall timeout
    try:
        async with asyncio.timeout(300):  # 5 minutes total
            return StreamingResponse(...)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={"detail": "Streaming timeout", "code": "STREAM_TIMEOUT"}
        )

# Per-token timeout in LLM service
class LLMService:
    async def stream_generate(self, prompt: str) -> AsyncGenerator[str, None]:
        async with self._semaphore:
            async with asyncio.timeout(30):  # 30s per token
                async for token in self._stream_generate(prompt):
                    yield token
```

## Health Check

```python
# presentation/api/v1/routes/streaming.py
@router.get("/stream/health")
async def stream_health(
    current_user: User = Depends(get_current_active_user),
    streaming_service: StreamingService = Depends(get_streaming_service)
) -> StreamHealthResponse:
    """Check streaming service health"""
    return StreamHealthResponse(
        status="healthy",
        active_sessions=len(streaming_service._active_sessions),
        ollama_healthy=await streaming_service.llm.health_check(),
        retrieval_healthy=await streaming_service.retrieval.health_check()
    )
```

## Monitoring

```python
streaming_sessions_active = Gauge("streaming_sessions_active", "Active streaming sessions")
streaming_duration = Histogram("streaming_duration_seconds", "Stream duration")
streaming_tokens_generated = Histogram("streaming_tokens_generated", "Tokens per stream")
streaming_disconnects = Counter("streaming_client_disconnects_total", "Client disconnects")
streaming_time_to_first_token = Histogram("streaming_ttft_seconds", "Time to first token")
streaming_errors = Counter("streaming_errors_total", "Stream errors", ["type"])

# In service
async def stream_chat(self, request):
    start = time.perf_counter()
    first_token = True
    
    async for token in self.llm.stream_generate(prompt):
        if first_token:
            streaming_time_to_first_token.observe(time.perf_counter() - start)
            first_token = False
        yield token
    
    streaming_duration.observe(time.perf_counter() - start)
    streaming_tokens_generated.observe(token_count)
```