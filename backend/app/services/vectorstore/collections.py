from typing import List, Dict, Any, Optional
from app.services.vectorstore.client import ChromaDBServiceClient, chromadb_service_client
from app.services.vectorstore.models import CollectionInfo, CollectionsListResponse, CollectionStatsResponse
from app.services.vectorstore.exceptions import (
    ChromaDBConnectionError,
    CollectionNotFoundError,
    CollectionAlreadyExistsError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class CollectionManager:
    DEFAULT_COLLECTION_NAME = "kifpilot_documents"

    def __init__(self, client: Optional[ChromaDBServiceClient] = None):
        self._client = client or chromadb_service_client

    async def list_collections(self) -> CollectionsListResponse:
        try:
            collections = self._client.list_collections()
            collection_infos = [
                CollectionInfo(name=c["name"], count=c["count"], metadata=c["metadata"])
                for c in collections
            ]
            return CollectionsListResponse(
                collections=collection_infos,
                total_collections=len(collection_infos),
            )
        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            raise ChromaDBConnectionError(f"Failed to list collections: {str(e)}")

    async def get_collection_stats(self, collection_name: str = DEFAULT_COLLECTION_NAME) -> CollectionStatsResponse:
        try:
            if not self._client.collection_exists(collection_name):
                raise CollectionNotFoundError(collection_name)

            count = self._client.get_collection_count(collection_name)
            collection = self._client.get_collection(collection_name)

            return CollectionStatsResponse(
                name=collection_name,
                count=count,
                metadata=collection.metadata,
            )
        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get collection stats", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to get collection stats: {str(e)}")

    async def create_collection(
        self, collection_name: str = DEFAULT_COLLECTION_NAME, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        try:
            if self._client.collection_exists(collection_name):
                logger.info("Collection already exists", collection=collection_name)
                return True

            self._client.create_collection(collection_name, metadata)
            logger.info("Collection created", collection=collection_name)
            return True
        except CollectionAlreadyExistsError:
            raise
        except Exception as e:
            logger.error("Failed to create collection", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to create collection: {str(e)}")

    async def delete_collection(self, collection_name: str) -> bool:
        try:
            if not self._client.collection_exists(collection_name):
                raise CollectionNotFoundError(collection_name)

            return self._client.delete_collection(collection_name)
        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete collection", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to delete collection: {str(e)}")

    async def reset_collection(self, collection_name: str = DEFAULT_COLLECTION_NAME) -> Dict[str, Any]:
        try:
            if self._client.collection_exists(collection_name):
                self._client.delete_collection(collection_name)
                logger.info("Collection deleted for reset", collection=collection_name)

            self._client.create_collection(collection_name)
            logger.info("Collection reset completed", collection=collection_name)

            return {
                "success": True,
                "collection_name": collection_name,
                "message": f"Collection '{collection_name}' has been reset",
            }
        except Exception as e:
            logger.error("Failed to reset collection", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to reset collection: {str(e)}")


collection_manager = CollectionManager()