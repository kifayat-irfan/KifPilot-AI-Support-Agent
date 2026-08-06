from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.services.vectorstore import (
    vector_store_service,
    InsertEmbeddingsRequest,
    InsertEmbeddingsResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    DeleteRequest,
    DeleteResponse,
    ResetCollectionRequest,
    ResetCollectionResponse,
    ChromaDBHealthResponse,
    CollectionsListResponse,
    CollectionStatsResponse,
    ErrorResponse,
    ChromaDBConnectionError,
    CollectionNotFoundError,
    InvalidEmbeddingError,
    MetadataValidationError,
    QueryError,
    DeleteError,
    ResetError,
)
from app.core.logging import get_logger

router = APIRouter(prefix="/vector", tags=["Vector Store"])
logger = get_logger(__name__)


@router.get(
    "/health/chromadb",
    response_model=ChromaDBHealthResponse,
    responses={
        200: {"model": ChromaDBHealthResponse},
        503: {"model": ErrorResponse},
    },
)
async def chromadb_health():
    try:
        health = await vector_store_service.health_check()
        return health
    except Exception as e:
        logger.error("ChromaDB health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Health check failed", "detail": str(e), "code": "HEALTH_CHECK_FAILED"},
        )


@router.get(
    "/collections",
    response_model=CollectionsListResponse,
    responses={
        200: {"model": CollectionsListResponse},
        503: {"model": ErrorResponse},
    },
)
async def list_collections():
    try:
        return await vector_store_service._collection_manager.list_collections()
    except ChromaDBConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("List collections failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to list collections", "detail": str(e), "code": "LIST_COLLECTIONS_FAILED"},
        )


@router.get(
    "/stats",
    response_model=CollectionStatsResponse,
    responses={
        200: {"model": CollectionStatsResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def get_collection_stats(collection_name: str = "kifpilot_documents"):
    try:
        return await vector_store_service._collection_manager.get_collection_stats(collection_name)
    except CollectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ChromaDBConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Get collection stats failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get collection stats", "detail": str(e), "code": "GET_STATS_FAILED"},
        )


@router.post(
    "/insert",
    response_model=InsertEmbeddingsResponse,
    responses={
        200: {"model": InsertEmbeddingsResponse},
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def insert_embeddings(request: InsertEmbeddingsRequest):
    try:
        return await vector_store_service.insert_embeddings(request)
    except (InvalidEmbeddingError, MetadataValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ChromaDBConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Insert embeddings failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Insert embeddings failed", "detail": str(e), "code": "INSERT_FAILED"},
        )


@router.post(
    "/search",
    response_model=SimilaritySearchResponse,
    responses={
        200: {"model": SimilaritySearchResponse},
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def similarity_search(request: SimilaritySearchRequest):
    try:
        return await vector_store_service.similarity_search(request)
    except InvalidEmbeddingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except CollectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except QueryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ChromaDBConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Similarity search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Similarity search failed", "detail": str(e), "code": "SEARCH_FAILED"},
        )


@router.post(
    "/delete",
    response_model=DeleteResponse,
    responses={
        200: {"model": DeleteResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def delete_documents(request: DeleteRequest):
    try:
        return await vector_store_service.delete_documents(request)
    except CollectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except DeleteError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ChromaDBConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Delete documents failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Delete documents failed", "detail": str(e), "code": "DELETE_FAILED"},
        )


@router.post(
    "/reset",
    response_model=ResetCollectionResponse,
    responses={
        200: {"model": ResetCollectionResponse},
        503: {"model": ErrorResponse},
    },
)
async def reset_collection(request: ResetCollectionRequest):
    try:
        return await vector_store_service.reset_collection(request)
    except ResetError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except ChromaDBConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.message, "detail": str(e.details), "code": e.code},
        )
    except Exception as e:
        logger.error("Reset collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Reset collection failed", "detail": str(e), "code": "RESET_FAILED"},
        )