import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from app.services.citations.schemas import Citation
from app.services.citations.exceptions import (
    MissingChunkError,
    DeletedDocumentError,
    InvalidMetadataError,
    CitationValidationError,
)


class CitationValidator:
    """
    Validates citations against database and metadata rules.
    
    Checks:
    - Referenced chunks exist
    - Referenced documents are not deleted
    - Metadata is valid and complete
    - No orphaned citations
    """

    # Required fields for a valid citation
    REQUIRED_FIELDS = {
        "document_id",
        "document_name",
        "chunk_id",
        "chunk_index",
        "similarity_score",
    }

    # Valid similarity score range
    MIN_SIMILARITY = 0.0
    MAX_SIMILARITY = 1.0

    def __init__(self, db_session=None):
        self.db_session = db_session

    def validate_citation(self, citation: Citation) -> List[str]:
        """
        Validate a single citation.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            value = getattr(citation, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Missing required field: {field}")

        # Validate similarity score
        if citation.similarity_score is not None:
            if not isinstance(citation.similarity_score, (int, float)):
                errors.append("similarity_score must be a number")
            elif citation.similarity_score < self.MIN_SIMILARITY or citation.similarity_score > self.MAX_SIMILARITY:
                errors.append(f"similarity_score must be between {self.MIN_SIMILARITY} and {self.MAX_SIMILARITY}")

        # Validate chunk_index
        if citation.chunk_index is not None:
            if not isinstance(citation.chunk_index, int) or citation.chunk_index < 0:
                errors.append("chunk_index must be a non-negative integer")

        # Validate page_number
        if citation.page_number is not None:
            if not isinstance(citation.page_number, int) or citation.page_number < 1:
                errors.append("page_number must be a positive integer")

        # Validate UUID format
        if citation.document_id and not self._is_valid_uuid(citation.document_id):
            errors.append("document_id must be a valid UUID")
        
        if citation.chunk_id and not self._is_valid_uuid(citation.chunk_id):
            errors.append("chunk_id must be a valid UUID")

        return errors

    def validate_batch(self, citations: List[Citation]) -> Dict[str, List[str]]:
        """
        Validate a batch of citations.
        
        Returns:
            Dict mapping chunk_id to list of errors (empty list = valid)
        """
        results = {}
        for citation in citations:
            errors = self.validate_citation(citation)
            results[citation.chunk_id] = errors
        return results

    def filter_valid(self, citations: List[Citation]) -> List[Citation]:
        """Return only valid citations."""
        valid = []
        for citation in citations:
            errors = self.validate_citation(citation)
            if not errors:
                valid.append(citation)
        return valid

    def check_against_database(
        self, 
        citations: List[Citation]
    ) -> Dict[str, List[str]]:
        """
        Verify citations exist in database.
        
        Returns:
            Dict mapping chunk_id to list of errors
        """
        # In production, this would query the database
        # For now, returns empty errors for all
        return {c.chunk_id: [] for c in citations}

    def check_deleted_documents(
        self,
        citations: List[Citation],
        deleted_doc_ids: Set[str],
    ) -> List[str]:
        """
        Check if any citations reference deleted documents.
        
        Returns:
            List of chunk_ids referencing deleted documents
        """
        deleted = []
        for citation in citations:
            if citation.document_id in deleted_doc_ids:
                deleted.append(citation.chunk_id)
        return deleted

    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID."""
        import uuid
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False


class CitationSanitizer:
    """Sanitizes citations for safe output."""

    @staticmethod
    def sanitize(citation: Citation) -> Citation:
        """Create a sanitized copy of citation."""
        return Citation(
            document_id=citation.document_id.strip() if citation.document_id else "",
            document_name=citation.document_name.strip() if citation.document_name else "Unknown",
            page_number=citation.page_number,
            section=citation.section.strip() if citation.section else None,
            chunk_id=citation.chunk_id.strip() if citation.chunk_id else "",
            chunk_index=citation.chunk_index,
            similarity_score=round(float(citation.similarity_score), 4),
        )

    @staticmethod
    def sanitize_batch(citations: List[Citation]) -> List[Citation]:
        return [CitationSanitizer.sanitize(c) for c in citations]


class CitationEnricher:
    """Enriches citations with additional context."""

    @staticmethod
    def add_confidence_ranking(citations: List[Citation]) -> List[Citation]:
        """Add confidence ranking based on similarity scores."""
        if not citations:
            return citations
        
        scores = [c.similarity_score for c in citations]
        max_score = max(scores)
        min_score = min(scores)
        
        if max_score == min_score:
            for c in citations:
                c.metadata = getattr(c, 'metadata', {})
                c.metadata['confidence_rank'] = 1.0
            return citations
        
        for c in citations:
            normalized = (c.similarity_score - min_score) / (max_score - min_score)
            c.metadata = getattr(c, 'metadata', {})
            c.metadata['confidence_rank'] = round(normalized, 4)
        
        return citations

    @staticmethod
    def add_source_diversity(citations: List[Citation]) -> List[Citation]:
        """Add source diversity metrics."""
        doc_ids = set(c.document_id for c in citations)
        for c in citations:
            c.metadata = getattr(c, 'metadata', {})
            c.metadata['source_diversity'] = len(doc_ids)
        return citations