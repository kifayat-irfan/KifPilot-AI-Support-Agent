from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict, Any

from app.services.citations import (
    citation_service,
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
from app.core.logging import get_logger
from app.presentation.api.v1.dependencies import get_current_active_user, require_chat

router = APIRouter(prefix="/citations", tags=["Citations"])
logger = get_logger(__name__)


@router.post(
    "/ask",
    response_model=CitedAnswer,
    responses={
        200: {"model": CitedAnswer, "description": "Answer with full citations"},
        400: {"description": "Invalid question"},
        404: {"description": "No relevant context found or referenced document/chunk missing"},
        500: {"description": "Citation generation failed"},
    },
    dependencies=[Depends(require_chat)],
)
async def ask_with_citations(
    question: str,
    top_k: int = 5,
    minimum_score: float = 0.65,
    filters: Optional[Dict[str, Any]] = None,
    current_user = Depends(get_current_active_user),
):
    """
    Generate an answer with full source citations.
    
    Every factual statement in the answer is backed by retrieved document chunks.
    Citations include: document name, page number, section, chunk ID, similarity score.
    
    **Citation rules enforced:**
    - Duplicate citations removed (by chunk_id)
    - Citations sorted by similarity score
    - Invalid citations (missing chunks, deleted docs) rejected
    - Confidence calculated from retrieval quality
    
    **Guardrails:**
    - Empty questions rejected
    - Prompt injection attempts rejected
    """
    try:
        response = await citation_service.ask_with_citations(
            question=question,
            top_k=top_k,
            minimum_score=minimum_score,
            filters=filters,
        )
        return response

    except CitationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except MissingChunkError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except DeletedDocumentError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except InvalidMetadataError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except CitationGenerationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except CitationValidationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except Exception as e:
        logger.error("Citation ask failed", error=str(e), question=question[:100] if question else "N/A")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/health",
    response_model=CitationHealthResponse,
    responses={
        200: {"model": CitationHealthResponse, "description": "Health check status"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def health_check(current_user = Depends(get_current_active_user)):
    """Check health of citation service dependencies."""
    response = await citation_service.health_check()
    return response