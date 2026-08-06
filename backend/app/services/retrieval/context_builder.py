from typing import List, Optional, Dict, Any, Set
from app.services.vectorstore.models import SearchResult


class ContextBuilder:
    """Builds clean context from retrieved chunks for RAG."""

    def __init__(
        self,
        max_context_chars: int = 8000,
        include_metadata: bool = True,
    ):
        self.max_context_chars = max_context_chars
        self.include_metadata = include_metadata

    def build_context(
        self,
        results: List[SearchResult],
        query: str = "",
    ) -> tuple[str, List[SearchResult]]:
        """
        Build context string from ranked search results.
        
        Requirements:
        - Preserve document order (by document_id, then chunk_index)
        - Preserve page numbers
        - Preserve section headings
        - Remove duplicate chunks (by chunk_id)
        - Respect maximum context size
        
        Args:
            results: Ranked search results
            query: Original search query (for reference)
            
        Returns:
            Tuple of (context_string, used_results)
        """
        if not results:
            return "", []

        # Remove duplicates by chunk_id, keeping highest scored
        unique_results = self._deduplicate_chunks(results)

        # Sort by document_id then chunk_index to preserve document order
        unique_results.sort(key=lambda r: (
            r.metadata.get("document_id", ""),
            r.metadata.get("chunk_index", 0)
        ))

        # Build context chunks
        context_parts = []
        used_results = []
        current_chars = 0

        for result in unique_results:
            chunk_text = self._format_chunk(result)
            chunk_chars = len(chunk_text)

            # Check if adding this chunk would exceed max context
            if current_chars + chunk_chars > self.max_context_chars:
                # Try to truncate this chunk if it's the first one
                if not context_parts:
                    remaining = self.max_context_chars - current_chars - 100  # Leave room for truncation marker
                    if remaining > 200:
                        chunk_text = chunk_text[:remaining] + "\n... [truncated]"
                        context_parts.append(chunk_text)
                        used_results.append(result)
                break

            context_parts.append(chunk_text)
            used_results.append(result)
            current_chars += chunk_chars

        context = "\n\n---\n\n".join(context_parts)
        return context, used_results

    def _deduplicate_chunks(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate chunks by chunk_id, keeping highest scored."""
        seen: Dict[str, SearchResult] = {}
        
        for result in results:
            chunk_id = result.metadata.get("chunk_id") or result.id
            if chunk_id not in seen or result.score > seen[chunk_id].score:
                seen[chunk_id] = result
        
        return list(seen.values())

    def _format_chunk(self, result: SearchResult) -> str:
        """Format a single chunk for context inclusion."""
        metadata = result.metadata or {}
        
        parts = []
        
        # Document header
        doc_name = metadata.get("document_name", "Unknown Document")
        parts.append(f"[Document: {doc_name}]")
        
        # Section/heading if available
        section = metadata.get("section")
        heading = metadata.get("heading")
        if section:
            parts.append(f"Section: {section}")
        elif heading:
            parts.append(f"Heading: {heading}")
        
        # Page number if available
        page = metadata.get("page")
        if page:
            parts.append(f"Page: {page}")
        
        # Chunk text
        text = result.document.strip()
        if text:
            parts.append(text)
        
        return "\n".join(parts)

    def build_context_with_citations(
        self,
        results: List[SearchResult],
        query: str = "",
    ) -> tuple[str, List[SearchResult], Dict[int, Dict[str, Any]]]:
        """
        Build context with citation markers for later reference.
        
        Returns:
            Tuple of (context_string, used_results, citation_map)
        """
        context, used_results = self.build_context(results, query)
        
        # Build citation map for the LLM
        citation_map = {}
        for idx, result in enumerate(used_results):
            metadata = result.metadata or {}
            citation_map[idx + 1] = {
                "document_id": metadata.get("document_id"),
                "document_name": metadata.get("document_name"),
                "chunk_id": metadata.get("chunk_id") or result.id,
                "chunk_index": metadata.get("chunk_index"),
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "similarity_score": round(result.score, 4),
            }
        
        return context, used_results, citation_map