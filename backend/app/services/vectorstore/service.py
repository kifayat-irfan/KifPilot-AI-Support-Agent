import time
from typing import List, Optional, Dict, Any
from uuid import uuid4

from app.services.vectorstore.client import ChromaDBServiceClient, chromadb_service_client
from app.services.vectorstore.collections import CollectionManager, collection_manager
from app.services.vectorstore.embeddings import EmbeddingGenerator, embedding_generator
from app.services.vectorstore.models import (
    InsertEmbeddingsRequest,
    InsertEmbeddingsResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    SearchResult,
    DeleteRequest,
    DeleteResponse,
    ResetCollectionRequest,
    ResetCollectionResponse,
    ChromaDBHealthResponse,
)
from app.services.vectorstore.exceptions import (
    ChromaDBConnectionError,
    CollectionNotFoundError,
    InvalidEmbeddingError,
    MetadataValidationError,
    QueryError,
    DeleteError,
    ResetError,
)
from app.services.vectorstore.models import ChunkMetadata
from app.core.config import get_settings
from app.core.logging import get_logger
from app.monitoring import (
    chromadb_collections,
    chromadb_documents,
    chromadb_query_duration,
    ollama_embedding_duration,
    record_ai_tokens,
)

settings = get_settings()
logger = get_logger(__name__)


REQUIRED_METADATA_FIELDS = {
    "document_id",
    "document_name",
    "company",
    "file_type",
    "chunk_id",
    "chunk_index",
    "created_at",
}


def get_organization_collection_name(organization_id: str) -> str:
    """Get the ChromaDB collection name for an organization."""
    return f"kifpilot_org_{organization_id}"


class VectorStoreService:
    """Vector store service with multi-tenant support."""

    def __init__(
        self,
        chroma_client: Optional[ChromaDBServiceClient] = None,
        collection_mgr: Optional[CollectionManager] = None,
        embedding_gen: Optional[EmbeddingGenerator] = None,
    ):
        self._chroma_client = chroma_client or chromadb_service_client
        self._collection_manager = collection_mgr or collection_manager
        self._embedding_generator = embedding_gen or embedding_generator

    def _validate_metadata(self, metadata: ChunkMetadata) -> None:
        missing_fields = REQUIRED_METADATA_FIELDS - set(metadata.model_dump().keys())
        if missing_fields:
            raise MetadataValidationError(
                f"Missing required metadata fields: {missing_fields}",
                details={"missing_fields": list(missing_fields)},
            )

    def _metadata_to_dict(self, metadata: ChunkMetadata) -> Dict[str, Any]:
        data = metadata.model_dump()
        data["created_at"] = data["created_at"].isoformat() if isinstance(data["created_at"], str) else data["created_at"]
        return data

    async def health_check(self, organization_id: Optional[str] = None) -> ChromaDBHealthResponse:
        """Check health of ChromaDB for an organization or globally."""
        chromadb_running = False
        collection_exists = False
        document_count = 0
        error = None

        try:
            collections = self._chroma_client.list_collections()
            chromadb_running = True
            
            # Record ChromaDB metrics
            try:
                chromadb_collections.labels(instance="localhost").set(len(collections))
            except Exception as e:
                logger.warning(f"Failed to record ChromaDB collections metric: {e}")
                
        except Exception as e:
            error = str(e)
            logger.warning("ChromaDB health check failed", error=error)

        if chromadb_running and organization_id:
            collection_name = get_organization_collection_name(organization_id)
            try:
                collection_exists = self._chroma_client.collection_exists(collection_name)
                if collection_exists:
                    document_count = self._chroma_client.get_collection_count(collection_name)
                    
                    # Record document count
                    try:
                        chromadb_documents.labels(instance="localhost", collection=collection_name).set(document_count)
                    except Exception as e:
                        logger.warning(f"Failed to record ChromaDB documents metric: {e}")
                        
            except Exception as e:
                error = str(e)
                logger.warning("Collection check failed", error=error)

        return ChromaDBHealthResponse(
            status="healthy" if chromadb_running else "unhealthy",
            chromadb_running=chromadb_running,
            collection_exists=collection_exists,
            collection_name=get_organization_collection_name(organization_id) if organization_id else "global",
            document_count=document_count,
            persist_dir=settings.CHROMA_PERSIST_DIR,
            error=error,
        )

    async def insert_embeddings(
        self,
        request: InsertEmbeddingsRequest,
        organization_id: Optional[str] = None,
    ) -> InsertEmbeddingsResponse:
        """Insert embeddings into organization-specific collection."""
        try:
            collection_name = request.collection_name or (
                get_organization_collection_name(organization_id) if organization_id else "kifpilot_documents"
            )

            if len(request.documents) != len(request.embeddings) or len(request.documents) != len(request.metadatas):
                raise InvalidEmbeddingError("Documents, embeddings, and metadatas must have the same length")

            for metadata in request.metadatas:
                self._validate_metadata(metadata)

            ids = request.ids or [str(uuid4()) for _ in request.documents]
            if len(ids) != len(request.documents):
                raise InvalidEmbeddingError("IDs length must match documents length")

            metadatas_dict = [self._metadata_to_dict(m) for m in request.metadatas]

            # Ensure organization_id is in metadata for filtering
            for meta in metadatas_dict:
                if organization_id:
                    meta["organization_id"] = organization_id

            self._chroma_client.add_documents(
                collection_name=collection_name,
                ids=ids,
                documents=request.documents,
                embeddings=request.embeddings,
                metadatas=metadatas_dict,
            )

            logger.info("Embeddings inserted", collection=collection_name, count=len(request.documents))

            # Update document count metric
            try:
                chromadb_documents.labels(instance="localhost", collection=collection_name).inc(len(request.documents))
            except Exception as e:
                logger.warning(f"Failed to update ChromaDB documents metric: {e}")

            return InsertEmbeddingsResponse(
                success=True,
                inserted_count=len(request.documents),
                collection_name=collection_name,
            )

        except (InvalidEmbeddingError, MetadataValidationError):
            raise
        except Exception as e:
            logger.error("Insert embeddings failed", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to insert embeddings: {str(e)}")

    async def similarity_search(
        self,
        request: SimilaritySearchRequest,
        organization_id: Optional[str] = None,
    ) -> SimilaritySearchResponse:
        """Search in organization-specific collection."""
        start_time = time.time()

        try:
            collection_name = request.collection_name or (
                get_organization_collection_name(organization_id) if organization_id else "kifpilot_documents"
            )

            if not request.query_embedding:
                raise InvalidEmbeddingError("Query embedding cannot be empty")

            if not self._chroma_client.collection_exists(collection_name):
                raise CollectionNotFoundError(collection_name)

            # Add organization_id filter to where clause
            where = request.where or {}
            if organization_id:
                where["organization_id"] = organization_id

            results = self._chroma_client.query(
                collection_name=collection_name,
                query_embeddings=[request.query_embedding],
                n_results=request.n_results,
                where=where,
                where_document=request.where_document,
            )

            search_results = []
            if results and results.get("ids") and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 0.0
                    score = 1.0 - distance if distance <= 1.0 else 0.0

                    search_results.append(
                        SearchResult(
                            id=doc_id,
                            document=results["documents"][0][i] if results.get("documents") else "",
                            metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                            distance=distance,
                            score=score,
                        )
                    )

            query_time_ms = (time.time() - start_time) * 1000

            logger.info("Similarity search completed", collection=collection_name, results=len(search_results))

            # Record query duration metric
            try:
                chromadb_query_duration.labels(operation="similarity_search", collection=collection_name).observe(query_time_ms / 1000)
            except Exception as e:
                logger.warning(f"Failed to record ChromaDB query duration: {e}")

            return SimilaritySearchResponse(
                results=search_results,
                query_time_ms=query_time_ms,
                collection_name=collection_name,
            )

        except (CollectionNotFoundError, InvalidEmbeddingError):
            raise
        except Exception as e:
            logger.error("Similarity search failed", collection=collection_name, error=str(e))
            raise QueryError(f"Similarity search failed: {str(e)}")

    async def delete_documents(
        self,
        request: DeleteRequest,
        organization_id: Optional[str] = None,
    ) -> DeleteResponse:
        """Delete documents from organization-specific collection."""
        try:
            collection_name = request.collection_name or (
                get_organization_collection_name(organization_id) if organization_id else "kifpilot_documents"
            )

            if not self._chroma_client.collection_exists(collection_name):
                raise CollectionNotFoundError(collection_name)

            self._chroma_client.delete_documents(collection_name, request.ids)

            logger.info("Documents deleted", collection=collection_name, count=len(request.ids))

            return DeleteResponse(
                success=True,
                deleted_count=len(request.ids),
                collection_name=collection_name,
            )

        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error("Delete documents failed", collection=collection_name, error=str(e))
            raise DeleteError(f"Failed to delete documents: {str(e)}")

    async def reset_collection(
        self,
        request: ResetCollectionRequest,
        organization_id: Optional[str] = None,
    ) -> ResetCollectionResponse:
        """Reset organization-specific collection."""
        try:
            collection_name = request.collection_name or (
                get_organization_collection_name(organization_id) if organization_id else "kifpilot_documents"
            )
            result = await self._collection_manager.reset_collection(collection_name)
            return ResetCollectionResponse(**result)
        except Exception as e:
            logger.error("Reset collection failed", collection=collection_name, error=str(e))
            raise ResetError(f"Failed to reset collection: {str(e)}")

    async def verify_startup(self) -> None:
        logger.info("Verifying Vector Store on startup...")

        health = await self.health_check()

        if not health.chromadb_running:
            logger.warning(
                "ChromaDB is not accessible",
                persist_dir=health.persist_dir,
            )
        else:
            logger.info("ChromaDB is running", persist_dir=health.persist_dir)

        # Verify embedding model via Ollama
        try:
            from app.services.llm import ollama_service
            ollama_health = await ollama_service.health_check()
            if not ollama_health.embed_model_available:
                logger.warning(
                    "Embedding model not available in Ollama",
                    model=settings.OLLAMA_EMBED_MODEL,
                )
            else:
                logger.info("Embedding model available", model=settings.OLLAMA_EMBED_MODEL)
        except Exception as e:
            logger.warning("Could not verify Ollama embedding model", error=str(e))

    async def close(self) -> None:
        pass


vector_store_service = VectorStoreService()