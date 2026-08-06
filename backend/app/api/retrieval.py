from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from uuid import UUID

from app.services.retrieval import (
    retrieval_service,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievalContextRequest,
    RetrievalContextResponse,
    RetrievalFilters,
    HealthCheckResponse,
)
from app.services.retrieval.exceptions import (
    RetrievalError,
    EmptyQueryError,
    InvalidTopKError,
    InvalidUUIDError,
    NoResultsError,
    ContextBuildError,
)
from app.core.logging import get_logger
from app.presentation.api.v1.dependencies import get_current_active_user, require_chat, get_current_organization_id

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])
logger = get_logger(__name__)


def validate_uuid(value: str, field: str = "id") -> str:
    """Validate UUID format."""
    try:
        UUID(value)
        return value
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid UUID format for {field}: {value}", "code": "INVALID_UUID"},
        )


@router.post(
    "/search",
    response_model=RetrievalSearchResponse,
    responses={
        200: {"model": RetrievalSearchResponse, "description": "Search results"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "No results found"},
        500: {"description": "Search failed"},
    },
    dependencies=[Depends(require_chat)],
)
async def search(
    query: str = Query(..., min_length=1, max_length=2000, description="Search query text"),
    top_k: int = Query(10, ge=1, le=20, description="Number of results to return"),
    minimum_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold"),
    category: Optional[str] = Query(None, description="Filter by document category"),
    language: Optional[str] = Query(None, description="Filter by document language (ISO 639-1)"),
    document_id: Optional[str] = Query(None, description="Filter by specific document ID"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    created_after: Optional[str] = Query(None, description="Filter documents created after this date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter documents created before this date (ISO format)"),
    current_user = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
):
    """
    Perform semantic vector search with optional metadata filters.
    
    Returns ranked chunks with similarity scores.
    """
    # Validate parameters early
    if top_k < 1 or top_k > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid top_k value: {top_k}. Must be between 1 and 20", "code": "INVALID_TOP_K"},
        )

    if document_id:
        validate_uuid(document_id, "document_id")

    # Parse date filters
    from datetime import datetime
    created_after_dt = None
    created_before_dt = None
    if created_after:
        try:
            created_after_dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid created_after format. Use ISO format.", "code": "INVALID_DATE"},
            )
    if created_before:
        try:
            created_before_dt = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid created_before format. Use ISO format.", "code": "INVALID_DATE"},
            )

    # Build filters
    filters = RetrievalFilters(
        category=category,
        language=language,
        document_id=document_id,
        file_type=file_type,
        processing_status=processing_status,
        created_after=created_after_dt,
        created_before=created_before_dt,
    )

    request = RetrievalSearchRequest(
        query=query,
        top_k=top_k,
        minimum_score=minimum_score,
        filters=filters,
    )

    try:
        response = await retrieval_service.search(request, organization_id=organization_id)
        return response

    except RetrievalError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except Exception as e:
        logger.error("Search failed", error=str(e), query=query[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )


@router.post(
    "/context",
    response_model=RetrievalContextResponse,
    responses={
        200: {"model": RetrievalContextResponse, "description": "Built context for RAG"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "No results found for context"},
        500: {"description": "Context building failed"},
    },
    dependencies=[Depends(require_chat)],
)
async def build_context(
    query: str = Query(..., min_length=1, max_length=2000, description="Original search query"),
    top_k: int = Query(10, ge=1, le=20, description="Number of chunks to include"),
    minimum_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold"),
    max_context_chars: int = Query(8000, ge=500, le=32000, description="Maximum context size in characters"),
    category: Optional[str] = Query(None, description="Filter by document category"),
    language: Optional[str] = Query(None, description="Filter by document language (ISO 639-1)"),
    document_id: Optional[str] = Query(None, description="Filter by specific document ID"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    created_after: Optional[str] = Query(None, description="Filter documents created after this date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter documents created before this date (ISO format)"),
    current_user = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
):
    """
    Build clean context for RAG from search results.
    
    Merges retrieved chunks, removes duplicates, preserves document order
    and section headings, respects maximum context size.
    """
    # Validate parameters early
    if top_k < 1 or top_k > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid top_k value: {top_k}. Must be between 1 and 20", "code": "INVALID_TOP_K"},
        )

    if document_id:
        validate_uuid(document_id, "document_id")

    # Parse date filters
    from datetime import datetime
    created_after_dt = None
    created_before_dt = None
    if created_after:
        try:
            created_after_dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid created_after format. Use ISO format.", "code": "INVALID_DATE"},
            )
    if created_before:
        try:
            created_before_dt = datetime.fromisoformat(created_before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid created_before format. Use ISO format.", "code": "INVALID_DATE"},
            )

    # Build filters
    filters = RetrievalFilters(
        category=category,
        language=language,
        document_id=document_id,
        file_type=file_type,
        processing_status=processing_status,
        created_after=created_after_dt,
        created_before=created_before_dt,
    )

    request = RetrievalContextRequest(
        query=query,
        top_k=top_k,
        minimum_score=minimum_score,
        filters=filters,
        max_context_chars=max_context_chars,
    )

    try:
        response = await retrieval_service.build_context(request, organization_id=organization_id)
        return response

    except RetrievalError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": e.message, "code": e.code, "details": e.details},
        )
    except Exception as e:
        logger.error("Context building failed", error=str(e), query=query[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        200: {"model": HealthCheckResponse, "description": "Health check status"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def health_check(current_user = Depends(get_current_active_user), organization_id: str = Depends(get_current_organization_id)):
    """Check health of retrieval system dependencies."""
    response = await retrieval_service.health_check(organization_id=organization_id)
    return response