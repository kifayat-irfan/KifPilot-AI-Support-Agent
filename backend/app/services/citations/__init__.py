"""
Citation Engine - Precise source attribution for RAG answers.

This module provides a production-grade citation engine that:
- Generates precise citations for every factual statement
- Deduplicates and validates citations
- Ensures citations reference valid, non-deleted documents
- Formats citations for API responses
"""

from app.services.citations.service import CitationService, citation_service
from app.services.citations.formatter import (
    CitationBuilder,
    CitationDeduplicator,
    CitationFormatter,
)
from app.services.citations.validator import (
    CitationValidator,
    CitationSanitizer,
    CitationEnricher,
)
from app.services.citations.schemas import (
    Citation,
    CitedAnswer,
    CitationHealthResponse,
)
from app.services.citations.exceptions import (
    CitationError,
    MissingChunkError,
    DeletedDocumentError,
    InvalidMetadataError,
    CitationGenerationError,
    CitationValidationError,
)

__all__ = [
    # Services
    "CitationService",
    "citation_service",
    "CitationBuilder",
    "CitationDeduplicator",
    "CitationFormatter",
    "CitationValidator",
    "CitationSanitizer",
    "CitationEnricher",
    # Schemas
    "Citation",
    "CitedAnswer",
    "CitationHealthResponse",
    # Exceptions
    "CitationError",
    "MissingChunkError",
    "DeletedDocumentError",
    "InvalidMetadataError",
    "CitationGenerationError",
    "CitationValidationError",
]