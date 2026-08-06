import re
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

from app.services.citations.schemas import Citation
from app.services.citations.exceptions import (
    MissingChunkError,
    DeletedDocumentError,
    InvalidMetadataError,
)


class CitationFormatter:
    """Formats citations for API responses and inline text."""

    @classmethod
    def format_inline(cls, citation: Citation) -> str:
        """Format a single citation for inline reference (e.g., [1])."""
        parts = [citation.document_name]
        if citation.page_number:
            parts.append(f"p. {citation.page_number}")
        if citation.section:
            parts.append(f"§ {citation.section}")
        return "[" + ", ".join(parts) + "]"

    @classmethod
    def format_bibliography(cls, citations: List[Citation]) -> List[Dict[str, Any]]:
        """Format citations for bibliography/reference list."""
        formatted = []
        for i, citation in enumerate(citations, 1):
            formatted.append({
                "index": i,
                "document_id": citation.document_id,
                "document_name": citation.document_name,
                "page_number": citation.page_number,
                "section": citation.section,
                "chunk_id": citation.chunk_id,
                "chunk_index": citation.chunk_index,
                "similarity_score": round(citation.similarity_score, 4),
            })
        return formatted

    @classmethod
    def inject_inline_citations(cls, answer: str, citations: List[Citation]) -> str:
        """
        Inject inline citation markers into answer text.
        
        Note: This is a simplified version. In production, you'd use
        sentence-level attribution from the LLM.
        """
        if not citations:
            return answer
        
        # For now, append bibliography at the end
        bib = "\n\n**Sources:**\n"
        for i, citation in enumerate(citations, 1):
            parts = [citation.document_name]
            if citation.page_number:
                parts.append(f"p. {citation.page_number}")
            if citation.section:
                parts.append(f"§ {citation.section}")
            bib += f"[{i}] {', '.join(parts)}\n"
        
        return answer + bib


class CitationDeduplicator:
    """Removes duplicate citations and merges overlapping ones."""

    @classmethod
    def deduplicate(cls, citations: List[Citation]) -> List[Citation]:
        """
        Remove duplicate citations.
        
        Citations are considered duplicates if they reference the same chunk_id.
        Keeps the citation with the highest similarity_score.
        """
        seen: Dict[str, Citation] = {}
        
        for citation in citations:
            key = citation.chunk_id
            if key not in seen or citation.similarity_score > seen[key].similarity_score:
                seen[key] = citation
        
        return list(seen.values())

    @classmethod
    def merge_overlapping(cls, citations: List[Citation]) -> List[Citation]:
        """
        Merge citations that refer to the same document and page/section.
        
        Keeps the highest similarity score among merged citations.
        """
        groups = defaultdict(list)
        
        for citation in citations:
            key = (citation.document_id, citation.page_number, citation.section)
            groups[key].append(citation)
        
        merged = []
        for group in groups.values():
            # Keep the one with highest similarity
            best = max(group, key=lambda c: c.similarity_score)
            merged.append(best)
        
        return merged

    @classmethod
    def sort_by_score(cls, citations: List[Citation], descending: bool = True) -> List[Citation]:
        """Sort citations by similarity score."""
        return sorted(citations, key=lambda c: c.similarity_score, reverse=descending)


class CitationValidator:
    """Validates citations against database."""

    def __init__(self):
        pass

    def validate_citation(self, citation: Citation) -> Tuple[bool, Optional[str]]:
        """
        Validate a single citation.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not citation.document_id:
            return False, "Missing document_id"
        if not citation.document_name:
            return False, "Missing document_name"
        if not citation.chunk_id:
            return False, "Missing chunk_id"
        if citation.chunk_index is None:
            return False, "Missing chunk_index"
        if citation.similarity_score < 0 or citation.similarity_score > 1:
            return False, "Invalid similarity_score (must be 0-1)"
        
        return True, None

    def validate_batch(self, citations: List[Citation]) -> List[Citation]:
        """
        Validate a batch of citations, returning only valid ones.
        
        Invalid citations are logged and excluded.
        """
        valid = []
        for citation in citations:
            is_valid, error = self.validate_citation(citation)
            if is_valid:
                valid.append(citation)
            else:
                # Log but don't fail - just exclude invalid
                print(f"Warning: Invalid citation excluded: {error} - {citation.chunk_id}")
        return valid

    async def verify_against_db(self, citations: List[Citation]) -> List[Citation]:
        """
        Verify citations exist in database (optional, for production).
        
        This would check against the document_chunks table.
        For now, returns citations as-is.
        """
        # In production, you'd query the database here
        # For now, return as-is
        return citations


class CitationBuilder:
    """Builds citations from retrieval results."""

    @classmethod
    def from_retrieval_results(
        cls,
        results: List[Dict[str, Any]],
        min_score: float = 0.0,
    ) -> List[Citation]:
        """
        Build citations from retrieval engine results.
        
        Args:
            results: List of retrieval results with metadata
            min_score: Minimum similarity score to include
            
        Returns:
            List of validated, deduplicated citations
        """
        citations = []
        
        for result in results:
            metadata = result.get("metadata", {})
            score = result.get("similarity_score", result.get("score", 0))
            
            if score < min_score:
                continue
            
            citation = Citation(
                document_id=metadata.get("document_id", ""),
                document_name=metadata.get("document_name", "Unknown"),
                page_number=metadata.get("page"),
                section=metadata.get("section"),
                chunk_id=metadata.get("chunk_id", result.get("chunk_id", "")),
                chunk_index=metadata.get("chunk_index", 0),
                similarity_score=round(score, 4),
            )
            citations.append(citation)
        
        # Deduplicate and sort
        citations = CitationDeduplicator.deduplicate(citations)
        citations = CitationDeduplicator.sort_by_score(citations)
        
        return citations

    @classmethod
    def from_rag_sources(cls, sources: List[Any]) -> List[Citation]:
        """Build citations from RAG source objects."""
        citations = []
        
        for source in sources:
            citation = Citation(
                document_id=source.document_id,
                document_name=source.document_name,
                page_number=source.page,
                section=source.section,
                chunk_id=source.chunk_id,
                chunk_index=source.chunk_index,
                similarity_score=source.similarity_score,
            )
            citations.append(citation)
        
        # Deduplicate and sort
        citations = CitationDeduplicator.deduplicate(citations)
        citations = CitationDeduplicator.sort_by_score(citations)
        
        return citations