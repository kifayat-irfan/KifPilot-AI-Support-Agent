from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from app.services.hybrid_search import (
    hybrid_search_service,
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchHealthResponse,
)
from app.services.hybrid_search.exceptions import (
    HybridSearchError,
    EmptyQueryError,
    InvalidTopKError,
    InvalidRRFConstantError,
    InvalidWeightError,
    VectorSearchError,
    BM25SearchError,
    FusionError,
)
from app.core.security import get_current_user
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/retrieval", tags=["Retrieval"])


@router.post("/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Perform hybrid search combining vector and BM25 search with RRF fusion.
    
    This endpoint combines semantic vector search with keyword-based BM25 search
    using Reciprocal Rank Fusion (RRF) for improved retrieval quality.
    
    Args:
        request: Hybrid search request with query, filters, and fusion parameters
        
    Returns:
        Ranked search results with RRF-fused scores and individual component scores
    """
    try:
        organization_id = getattr(current_user, 'organization_id', None)
        
        response = await hybrid_search_service.search(
            request=request,
            organization_id=organization_id,
        )
        
        return response
        
    except EmptyQueryError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    except InvalidTopKError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvalidRRFConstantError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvalidWeightError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VectorSearchError as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vector search failed"
        )
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hybrid search failed"
        )


@router.post("/hybrid-search/build-index")
async def build_bm25_index(
    organization_id: Optional[str] = None,
    batch_size: int = 100,
    current_user: User = Depends(get_current_user),
):
    """
    Build or rebuild BM25 index from vector store.
    
    Args:
        organization_id: Optional organization ID to filter chunks
        batch_size: Number of chunks to process per batch
        
    Returns:
        Index build statistics
    """
    try:
        org_id = organization_id or getattr(current_user, 'organization_id', None)
        
        result = await hybrid_search_service.build_bm25_index(
            organization_id=org_id,
            batch_size=batch_size,
        )
        
        return result
        
    except Exception as e:
        logger.error(f"BM25 index build error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BM25 index build failed: {str(e)}"
        )


@router.get("/hybrid-search/health", response_model=HybridSearchHealthResponse)
async def hybrid_search_health(
    organization_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Check health of hybrid search system.
    
    Returns:
        Health status of vector store, embedding service, and BM25 index
    """
    try:
        org_id = organization_id or getattr(current_user, 'organization_id', None)
        
        health = await hybrid_search_service.health_check(
            organization_id=org_id,
        )
        
        return health
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )