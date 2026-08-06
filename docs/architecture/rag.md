# RAG Answer Generation

## Overview

Retrieval-Augmented Generation pipeline: query → retrieve → compress → generate → cite.

## Pipeline Flow

```
User Question
      │
      ▼
┌─────────────────┐
│  Guardrails     │  ← Input validation, safety checks
│  (input)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Retrieval      │  ← Hybrid search + rerank + compress
│  Pipeline       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Prompt Builder │  ← Template + context + question
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Generation │  ← Ollama streaming/non-streaming
│  (streaming)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Guardrails     │  ← Output validation, citation check
│  (output)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Citation       │  ← Match answer to source chunks
│  Attribution    │
└────────┬────────┘
         │
         ▼
   Final Response
```

## RAG Service

```python
# services/rag/service.py
class RAGService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        guardrails: GuardrailsService,
        citation_extractor: CitationExtractor,
        settings: Settings
    ):
        self.retrieval = retrieval_service
        self.llm = llm_service
        self.prompt_builder = prompt_builder
        self.guardrails = guardrails
        self.citations = citation_extractor
        self.settings = settings
    
    async def query(
        self,
        question: str,
        org_id: str,
        kb_ids: List[str],
        top_k: int = 5,
        minimum_score: float = 0.3,
        conversation_id: str = None,
        filters: dict = None,
        stream: bool = False
    ) -> Union[RAGResponse, AsyncGenerator[RAGEvent, None]]:
        
        # 1. Input guardrails
        guard_result = await self.guardrails.check_input(question)
        if not guard_result.allowed:
            return RAGResponse(
                answer=guard_result.message,
                citations=[],
                confidence=0.0,
                sources_found=0,
                guardrails_triggered=True
            )
        
        # 2. Retrieve context
        retrieval_results = await self.retrieval.search_with_rerank(
            query=question,
            org_id=org_id,
            kb_ids=kb_ids,
            top_k=top_k,
            minimum_score=minimum_score,
            filters=filters
        )
        
        # 3. Compress context
        context = self.context_compressor.build_context(question, retrieval_results.results)
        
        # 4. Build prompt
        prompt = await self.prompt_builder.build_rag_prompt(
            question=question,
            context=context,
            conversation_history=await self._get_conversation_history(conversation_id)
        )
        
        # 5. Generate answer
        if stream:
            return self._stream_generate(prompt, context.citations)
        else:
            return await self._generate_complete(prompt, context.citations)
    
    async def _stream_generate(
        self,
        prompt: str,
        citations: List[Citation]
    ) -> AsyncGenerator[RAGEvent, None]:
        """Stream answer with citations"""
        # Start event
        yield RAGEvent(event="start", data={"session_id": str(uuid.uuid4())})
        
        # Retrieval complete
        yield RAGEvent(event="retrieval", data={
            "chunks_found": len(citations),
            "time_ms": retrieval_time_ms
        })
        
        # Token streaming
        full_answer = ""
        async for token in self.llm.stream_generate(prompt):
            full_answer += token
            yield RAGEvent(event="token", data={"text": token})
        
        # Extract citations from answer
        answer_citations = self.citations.extract(full_answer, citations)
        
        # Output guardrails
        guard_result = await self.guardrails.check_output(full_answer)
        if not guard_result.allowed:
            yield RAGEvent(event="error", data={"message": guard_result.message})
            return
        
        # Citations event
        yield RAGEvent(event="citations", data={
            "citations": [c.to_dict() for c in answer_citations]
        })
        
        # Complete event
        confidence = self._calculate_confidence(full_answer, answer_citations)
        yield RAGEvent(event="complete", data={
            "answer": full_answer,
            "citations": [c.to_dict() for c in answer_citations],
            "confidence": confidence,
            "sources_found": len(citations),
            "response_time_ms": total_time_ms
        })
    
    async def _generate_complete(
        self,
        prompt: str,
        citations: List[Citation]
    ) -> RAGResponse:
        """Non-streaming generation"""
        answer = await self.llm.generate(prompt)
        
        # Guardrails
        guard_result = await self.guardrails.check_output(answer)
        if not guard_result.allowed:
            return RAGResponse(
                answer=guard_result.message,
                citations=[],
                confidence=0.0,
                sources_found=0
            )
        
        # Extract citations
        answer_citations = self.citations.extract(answer, citations)
        confidence = self._calculate_confidence(answer, answer_citations)
        
        return RAGResponse(
            answer=answer,
            citations=[c.to_dict() for c in answer_citations],
            confidence=confidence,
            sources_found=len(citations),
            response_time_ms=total_time_ms
        )
```

## Prompt Builder

```python
# services/rag/prompt_builder.py
class PromptBuilder:
    SYSTEM_PROMPT = """You are a helpful AI assistant for customer support. 
Your role is to answer questions using ONLY the provided context from the knowledge base.

Guidelines:
1. Answer based ONLY on the provided context
2. If the context doesn't contain sufficient information, say "I don't have enough information to answer this question."
3. Be concise, accurate, and professional
4. Cite sources using [1], [2], etc. markers that correspond to the context
5. Do not make up information or use external knowledge
6. If asked about specific procedures, quote relevant sections"""

    def __init__(self):
        self.templates = {
            "default": self._default_template,
            "concise": self._concise_template,
            "detailed": self._detailed_template,
        }
    
    async def build_rag_prompt(
        self,
        question: str,
        context: CompressedContext,
        conversation_history: List[ChatMessage] = None,
        template: str = "default"
    ) -> str:
        builder = self.templates.get(template, self._default_template)
        return builder(question, context, conversation_history)
    
    def _default_template(
        self,
        question: str,
        context: CompressedContext,
        history: List[ChatMessage] = None
    ) -> str:
        parts = [self.SYSTEM_PROMPT, "\n"]
        
        if context.citations:
            parts.append("Context:\n")
            parts.append(context.context)
            parts.append("\n")
        
        if history:
            parts.append("Previous conversation:\n")
            for msg in history[-3:]:  # Last 3 messages
                role = "User" if msg.role == "user" else "Assistant"
                parts.append(f"{role}: {msg.content}\n")
            parts.append("\n")
        
        parts.append(f"Question: {question}\n\n")
        parts.append("Answer:")
        
        return "".join(parts)
    
    def _concise_template(self, question: str, context: CompressedContext, history: List[ChatMessage] = None):
        return f"""Answer briefly using only the context. Cite sources with [1], [2].

Context: {context.context}

Question: {question}

Answer:"""
    
    def _detailed_template(self, question: str, context: CompressedContext, history: List[ChatMessage] = None):
        return f"""{self.SYSTEM_PROMPT}

Provide a comprehensive answer with step-by-step explanations. Use multiple citations.

Context: {context.context}

Question: {question}

Detailed Answer:"""
```

## Citation Extraction

```python
# services/rag/citations.py
class CitationExtractor:
    def __init__(self, similarity_threshold: float = 0.7):
        self.threshold = similarity_threshold
    
    def extract(
        self,
        answer: str,
        available_citations: List[Citation]
    ) -> List[Citation]:
        """Extract which citations are actually used in the answer"""
        used_citations = []
        
        # Find explicit citation markers [1], [2], etc.
        import re
        cited_numbers = set()
        for match in re.finditer(r'\[(\d+)\]', answer):
            cited_numbers.add(int(match.group(1)))
        
        # Map to actual citations
        for num in sorted(cited_numbers):
            idx = num - 1
            if 0 <= idx < len(available_citations):
                used_citations.append(available_citations[idx])
        
        # If no explicit markers, use semantic matching
        if not used_citations and available_citations:
            used_citations = self._semantic_match(answer, available_citations)
        
        return used_citations
    
    def _semantic_match(
        self,
        answer: str,
        citations: List[Citation]
    ) -> List[Citation]:
        """Fallback: semantic similarity between answer and citation text"""
        # Simple keyword overlap
        answer_words = set(answer.lower().split())
        matched = []
        
        for cite in citations:
            cite_words = set(cite.text.lower().split())
            overlap = len(answer_words & cite_words) / max(len(answer_words), 1)
            if overlap > 0.1:  # At least 10% overlap
                matched.append(cite)
        
        return matched[:5]  # Limit to top 5
```

## Confidence Scoring

```python
# services/rag/service.py
class RAGService:
    def _calculate_confidence(
        self,
        answer: str,
        citations: List[Citation],
        retrieval_scores: List[float]
    ) -> float:
        """Calculate confidence score for the answer"""
        if not citations:
            return 0.0
        
        factors = []
        
        # 1. Citation coverage
        citation_ratio = len(citations) / max(len(retrieval_scores), 1)
        factors.append(min(citation_ratio, 1.0))
        
        # 2. Average retrieval score
        if retrieval_scores:
            avg_retrieval = sum(retrieval_scores) / len(retrieval_scores)
            factors.append(avg_retrieval)
        
        # 3. Answer completeness (not "I don't know")
        uncertainty_phrases = [
            "i don't know", "i don't have", "not enough information",
            "cannot answer", "unable to", "not mentioned"
        ]
        is_uncertain = any(phrase in answer.lower() for phrase in uncertainty_phrases)
        factors.append(0.0 if is_uncertain else 1.0)
        
        # 4. Citation quality (average citation score)
        if citations:
            avg_cite_score = sum(c.score for c in citations) / len(citations)
            factors.append(avg_cite_score)
        
        # Weighted average
        weights = [0.3, 0.3, 0.2, 0.2]
        confidence = sum(f * w for f, w in zip(factors, weights))
        
        return round(confidence, 2)
```

## Guardrails

```python
# services/rag/guardrails.py
class GuardrailsService:
    def __init__(self):
        self.input_patterns = [
            r"ignore previous instructions",
            r"system prompt",
            r"reveal.*prompt",
            r"pretend to be",
            r"you are now",
            r"act as",
        ]
        self.output_patterns = [
            r"password|secret|key|token",
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        ]
    
    async def check_input(self, text: str) -> GuardrailResult:
        # Check for injection attempts
        for pattern in self.input_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return GuardrailResult(
                    allowed=False,
                    message="I cannot process this request.",
                    reason="input_injection"
                )
        
        # Length check
        if len(text) > 10000:
            return GuardrailResult(
                allowed=False,
                message="Question too long. Please shorten.",
                reason="length_exceeded"
            )
        
        return GuardrailResult(allowed=True)
    
    async def check_output(self, text: str) -> GuardrailResult:
        # Check for PII leakage
        for pattern in self.output_patterns:
            if re.search(pattern, text):
                return GuardrailResult(
                    allowed=False,
                    message="I cannot provide that information.",
                    reason="pii_detected"
                )
        
        return GuardrailResult(allowed=True)
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # RAG
    RETRIEVAL_MIN_SCORE: float = 0.3
    RETRIEVAL_MAX_CONTEXT: int = 8000
    RETRIEVAL_TOP_K: int = 5
    
    # LLM
    OLLAMA_CHAT_MODEL: str = "qwen3.5:4b"
    OLLAMA_TEMPERATURE: float = 0.1
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_MAX_TOKENS: int = 2048
    
    # RAG
    RAG_CONFIDENCE_THRESHOLD: float = 0.5
    RAG_MAX_CITATIONS: int = 5
    RAG_TEMPLATE: str = "default"
    
    # Guardrails
    RAG_GUARDRAILS_ENABLED: bool = True
```

## Monitoring

```python
rag_query_time = Histogram("rag_query_seconds", "RAG query time")
rag_generation_time = Histogram("rag_generation_seconds", "LLM generation time")
rag_confidence = Histogram("rag_confidence", "Answer confidence")
rag_citations_count = Histogram("rag_citations_count", "Citations per answer")
rag_guardrails_triggered = Counter("rag_guardrails_triggered_total", "Guardrails triggered", ["type"])
rag_streaming_chunks = Counter("rag_streaming_chunks_total", "Streaming chunks sent")
```