"""Chunk selector for token budget management."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SelectionResult:
    """Result of chunk selection."""
    selected_chunks: List[Dict[str, Any]]
    total_tokens: int
    total_chars: int
    truncated: bool


class ChunkSelector:
    """Handles chunk selection within token budget."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the selector with configuration."""
        self.max_tokens = config.get("max_tokens", 8000)
        self.max_documents = config.get("max_documents", 20)
        self.max_chunks = config.get("max_chunks", 50)
        self.chars_per_token = config.get("chars_per_token", 4.0)
        self.preserve_document_order = config.get("preserve_document_order", True)
        self.preserve_page_numbers = config.get("preserve_page_numbers", True)
    
    def select_chunks(
        self,
        chunks: List[Dict[str, Any]],
        token_budget: Optional[int] = None,
    ) -> SelectionResult:
        """
        Select chunks within token budget.
        
        Args:
            chunks: List of chunk dictionaries (already scored/ranked)
            token_budget: Optional token budget override
            
        Returns:
            SelectionResult with selected chunks
        """
        budget = token_budget or self.max_tokens
        max_chars = int(budget * self._get_chars_per_token())
        
        if not chunks:
            return SelectionResult(
                selected_chunks=[],
                total_tokens=0,
                total_chars=0,
                truncated=False
            )
        
        # Group by document if preserving document order
        if self.preserve_document_order:
            selected = self._select_by_document_order(chunks, max_chars)
        else:
            selected = self._select_by_score(chunks, max_chars)
        
        # Apply max chunks limit
        if len(selected) > self.max_chunks:
            selected = selected[:self.max_chunks]
        
        # Apply max documents limit
        selected = self._apply_max_documents(selected)
        
        # Calculate totals
        total_chars = sum(len(c.get("text", "") or c.get("content", "")) for c in selected)
        total_tokens = int(total_chars / self._get_chars_per_token())
        truncated = len(selected) < len(chunks)
        
        logger.info(
            "Chunk selection completed",
            original_count=len(chunks),
            selected_count=len(selected),
            total_tokens=total_tokens,
            token_budget=budget,
            truncated=truncated,
        )
        
        return SelectionResult(
            selected_chunks=selected,
            total_tokens=total_tokens,
            total_chars=total_chars,
            truncated=truncated,
        )
    
    def _select_by_document_order(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int,
    ) -> List[Dict[str, Any]]:
        """Select chunks preserving document order."""
        # Group by document
        doc_chunks = {}
        for chunk in chunks:
            doc_id = chunk.get("document_id") or chunk.get("metadata", {}).get("document_id", "unknown")
            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = []
            doc_chunks[doc_id].append(chunk)
        
        # Sort documents by first chunk's score (descending)
        doc_scores = {}
        for doc_id, doc_chunks_list in doc_chunks.items():
            max_score = max(
                c.get("score", 0) or c.get("similarity_score", 0) or c.get("final_score", 0) or c.get("rrf_score", 0) or 0
                for c in doc_chunks_list
            )
            doc_scores[doc_id] = max_score
        
        sorted_docs = sorted(doc_scores.keys(), key=lambda d: doc_scores[d], reverse=True)
        
        # Select chunks document by document
        selected = []
        current_chars = 0
        
        for doc_id in sorted_docs:
            if len(selected) >= self.max_chunks:
                break
            
            doc_chunks_list = doc_chunks[doc_id]
            # Sort chunks within document by chunk_index
            doc_chunks_list.sort(key=lambda c: c.get("chunk_index", c.get("metadata", {}).get("chunk_index", 0)))
            
            for chunk in doc_chunks_list:
                if len(selected) >= self.max_chunks:
                    break
                    
                text = chunk.get("text", "") or chunk.get("content", "")
                chunk_chars = len(text)
                
                if current_chars + chunk_chars > max_chars:
                    if not selected:
                        # First chunk, truncate if needed
                        remaining = max_chars - current_chars
                        if remaining > 100:
                            truncated_chunk = chunk.copy()
                            truncated_chunk["text"] = text[:remaining] + "\n... [truncated]"
                            truncated_chunk["content"] = truncated_chunk["text"]
                            selected.append(truncated_chunk)
                            current_chars += remaining
                    break
                
                selected.append(chunk)
                current_chars += chunk_chars
                
                if len(selected) >= self.max_chunks:
                    break
        
        return selected
    
    def _select_by_score(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int,
    ) -> List[Dict[str, Any]]:
        """Select chunks by score descending."""
        # Sort by score descending
        scored_chunks = []
        for chunk in chunks:
            score = chunk.get("score", 0) or chunk.get("similarity_score", 0) or chunk.get("final_score", 0) or chunk.get("rrf_score", 0) or 0
            scored_chunks.append((score, chunk))
        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        selected = []
        current_chars = 0
        
        for score, chunk in scored_chunks:
            if len(selected) >= self.max_chunks:
                break
                
            text = chunk.get("text", "") or chunk.get("content", "")
            chunk_chars = len(text)
            
            if current_chars + chunk_chars > max_chars:
                if not selected:
                    # First chunk, truncate if needed
                    remaining = max_chars - current_chars
                    if remaining > 100:
                        truncated_chunk = chunk.copy()
                        truncated_chunk["text"] = text[:remaining] + "\n... [truncated]"
                        truncated_chunk["content"] = truncated_chunk["text"]
                        selected.append(truncated_chunk)
                        current_chars += remaining
                break
            
            selected.append(chunk)
            current_chars += chunk_chars
        
        return selected
    
    def _apply_max_documents(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Limit number of unique documents."""
        if len(chunks) <= 1:
            return chunks
        
        doc_ids = set()
        result = []
        
        for chunk in chunks:
            doc_id = chunk.get("document_id") or chunk.get("metadata", {}).get("document_id", "unknown")
            
            if doc_id not in doc_ids:
                if len(doc_ids) >= self.max_documents:
                    continue
                doc_ids.add(doc_id)
            
            result.append(chunk)
        
        return result
    
    def _get_chars_per_token(self) -> float:
        """Get chars per token estimate."""
        # This would ideally come from config, but we'll use a reasonable default
        return 4.0
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self._get_chars_per_token())
    
    def estimate_chunk_tokens(self, chunk: Dict[str, Any]) -> int:
        """Estimate tokens for a chunk."""
        text = chunk.get("text", "") or chunk.get("content", "")
        return self.estimate_tokens(text)