# Context Compression

## Overview

Intelligent context compression reduces retrieved document text to fit within token limits while preserving relevance for answer generation.

## Problem

```
Retrieved: 50 chunks × 200 tokens = 10,000 tokens
Context Window: 8,000 tokens (after prompt + question + answer)
Gap: 2,000 tokens over budget
```

## Compression Strategies

### 1. Priority-Based Selection
- Rank chunks by relevance score
- Include highest-scoring chunks first
- Stop at token budget

### 2. Iterative Refinement
- Start with all chunks
- Remove lowest-scoring until under budget
- Preserve citation integrity

### 3. Summary-Based
- Summarize low-priority chunks
- Keep high-priority chunks full
- Trade detail for breadth

## Implementation

```python
# services/retrieval/context_builder.py
class ContextCompressionService:
    def __init__(
        self,
        max_tokens: int = 8000,
        max_documents: int = 20,
        max_chunks: int = 50,
        tokenizer = None
    ):
        self.max_tokens = max_tokens
        self.max_documents = max_documents
        self.max_chunks = max_chunks
        self.tokenizer = tokenizer or self._default_tokenizer
    
    def _default_tokenizer(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token"""
        return len(text) // 4
    
    def build_context(
        self,
        query: str,
        results: List[RetrievalResult],
        reserved_tokens: int = 2000  # For prompt, question, answer
    ) -> CompressedContext:
        """Build compressed context from retrieval results"""
        available_tokens = self.max_tokens - reserved_tokens
        
        # Filter and limit results
        candidates = self._filter_candidates(results)
        
        # Select chunks by priority
        selected_chunks = self._select_chunks(candidates, available_tokens)
        
        # Build context text
        context_parts = []
        total_tokens = 0
        citations = []
        
        for i, chunk in enumerate(selected_chunks):
            chunk_tokens = self.tokenizer(chunk.text)
            
            if total_tokens + chunk_tokens > available_tokens:
                break
            
            # Format with citation marker
            citation_id = f"[{i+1}]"
            context_parts.append(f"{citation_id} {chunk.text}")
            
            citations.append(Citation(
                id=citation_id,
                document_id=chunk.metadata.get("document_id"),
                chunk_id=chunk.metadata.get("chunk_id"),
                text=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                score=chunk.score
            ))
            
            total_tokens += chunk_tokens
        
        return CompressedContext(
            context="\n\n".join(context_parts),
            citations=citations,
            total_tokens=total_tokens,
            chunks_used=len(selected_chunks),
            chunks_available=len(candidates)
        )
    
    def _filter_candidates(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Apply filters and limits"""
        # Remove duplicates by document_id
        seen_docs = set()
        unique = []
        for r in results:
            doc_id = r.metadata.get("document_id")
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                unique.append(r)
        
        # Limit documents and chunks
        return unique[:self.max_documents][:self.max_chunks]
    
    def _select_chunks(
        self,
        candidates: List[RetrievalResult],
        token_budget: int
    ) -> List[RetrievalResult]:
        """Select chunks by relevance priority"""
        selected = []
        used_tokens = 0
        
        for chunk in candidates:
            chunk_tokens = self.tokenizer(chunk.text)
            
            if used_tokens + chunk_tokens > token_budget:
                # Try to fit partial chunk
                remaining = token_budget - used_tokens
                if remaining > 100:  # Minimum viable chunk
                    # Truncate chunk
                    truncated_text = chunk.text[:remaining * 4]  # Rough char estimate
                    chunk = RetrievalResult(
                        id=chunk.id,
                        text=truncated_text + "... [truncated]",
                        metadata=chunk.metadata,
                        score=chunk.score
                    )
                    selected.append(chunk)
                break
            
            selected.append(chunk)
            used_tokens += chunk_tokens
        
        return selected
```

## Citation Preservation

```python
# services/retrieval/context_builder.py
@dataclass
class Citation:
    id: str              # "[1]", "[2]", etc.
    document_id: str
    chunk_id: str
    text: str            # Snippet for display
    score: float
    page: int = None
    section: str = None

@dataclass
class CompressedContext:
    context: str         # Formatted context with citation markers
    citations: List[Citation]
    total_tokens: int
    chunks_used: int
    chunks_available: int
    compression_ratio: float = None
    
    def __post_init__(self):
        if self.chunks_available > 0:
            self.compression_ratio = self.chunks_used / self.chunks_available
```

## Advanced: Summary Compression

```python
class SummaryCompressionService:
    def __init__(
        self,
        llm_client: OllamaClient,
        summary_model: str = "qwen3.5:4b",
        max_summary_tokens: int = 200
    ):
        self.llm = llm_client
        self.summary_model = summary_model
        self.max_summary_tokens = max_summary_tokens
    
    async def compress_with_summaries(
        self,
        query: str,
        results: List[RetrievalResult],
        high_priority_count: int = 5
    ) -> CompressedContext:
        """Keep top chunks full, summarize the rest"""
        if len(results) <= high_priority_count:
            return self._build_full_context(results)
        
        # Keep top N chunks full
        high_priority = results[:high_priority_count]
        low_priority = results[high_priority_count:]
        
        # Summarize low-priority chunks in batches
        summaries = await self._summarize_batch(low_priority)
        
        # Combine
        all_chunks = high_priority + summaries
        
        return self._build_context(query, all_chunks)
    
    async def _summarize_batch(self, chunks: List[RetrievalResult]) -> List[RetrievalResult]:
        """Generate summaries for multiple chunks"""
        summaries = []
        
        for chunk in chunks:
            prompt = f"""Summarize the following text in {self.max_summary_tokens} tokens or less,
focusing on information relevant to answering questions. Preserve key facts, numbers, and names.

Text: {chunk.text}

Summary:"""
            
            response = await self.llm.generate(
                model=self.summary_model,
                prompt=prompt,
                options={"temperature": 0.1, "max_tokens": self.max_summary_tokens}
            )
            
            summary = RetrievalResult(
                id=chunk.id,
                text=response.response.strip(),
                metadata={**chunk.metadata, "summarized": True},
                score=chunk.score * 0.8  # Slightly reduce score for summarized
            )
            summaries.append(summary)
        
        return summaries
```

## Token Budget Management

```python
# services/rag/service.py
class RAGService:
    def __init__(self, settings: Settings):
        self.max_context_tokens = settings.CONTEXT_COMPRESSION_MAX_TOKENS
        self.reserved_tokens = 2000  # Prompt + question + answer buffer
    
    async def _build_prompt(self, question: str, context: CompressedContext) -> str:
        """Build RAG prompt with compressed context"""
        available = self.max_context_tokens - self.reserved_tokens
        
        prompt = f"""You are a helpful AI assistant. Answer the question using only the provided context.

Context:
{context.context}

Question: {question}

Instructions:
- Answer based ONLY on the provided context
- If the context doesn't contain the answer, say "I don't have enough information"
- Cite sources using the citation markers like [1], [2]
- Be concise and accurate

Answer:"""
        
        return prompt
    
    async def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4  # Rough estimate
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Context Compression
    CONTEXT_COMPRESSION_ENABLED: bool = True
    CONTEXT_COMPRESSION_MAX_TOKENS: int = 8000
    CONTEXT_COMPRESSION_MAX_DOCUMENTS: int = 20
    CONTEXT_COMPRESSION_MAX_CHUNKS: int = 50
    CONTEXT_COMPRESSION_RESERVED_TOKENS: int = 2000
    
    # Summary compression
    CONTEXT_COMPRESSION_USE_SUMMARIES: bool = True
    CONTEXT_COMPRESSION_HIGH_PRIORITY_COUNT: int = 5
    CONTEXT_COMPRESSION_MAX_SUMMARY_TOKENS: int = 200
```

## Monitoring

```python
context_compression_time = Histogram("context_compression_seconds", "Compression time")
context_chunks_in = Histogram("context_chunks_input", "Input chunks")
context_chunks_out = Histogram("context_chunks_output", "Output chunks")
context_compression_ratio = Histogram("context_compression_ratio", "Compression ratio")
context_tokens_saved = Counter("context_tokens_saved_total", "Tokens saved by compression")
```