from typing import List, Optional, Dict, Any
from uuid import UUID
from app.infrastructure.vector_store.client import chroma_client
from app.infrastructure.vector_store.repository import VectorStoreRepository
from app.core.exceptions import VectorStoreException
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChromaVectorStoreRepository(VectorStoreRepository):
    def __init__(self):
        self._client = chroma_client

    async def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
    ) -> bool:
        try:
            collection = self._client.get_or_create_collection(collection_name)
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("Documents added to collection", collection=collection_name, count=len(ids))
            return True
        except Exception as e:
            logger.error("Failed to add documents", collection=collection_name, error=str(e))
            raise VectorStoreException(f"Failed to add documents: {str(e)}")

    async def query(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        try:
            collection = self._client.get_or_create_collection(collection_name)
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document,
            )
            logger.debug("Query executed", collection=collection_name, results=len(results.get("ids", [[]])[0]))
            return results
        except Exception as e:
            logger.error("Failed to query collection", collection=collection_name, error=str(e))
            raise VectorStoreException(f"Failed to query collection: {str(e)}")

    async def delete_documents(
        self, collection_name: str, ids: List[str]
    ) -> bool:
        try:
            collection = self._client.get_or_create_collection(collection_name)
            collection.delete(ids=ids)
            logger.info("Documents deleted", collection=collection_name, count=len(ids))
            return True
        except Exception as e:
            logger.error("Failed to delete documents", collection=collection_name, error=str(e))
            raise VectorStoreException(f"Failed to delete documents: {str(e)}")

    async def get_collection_count(self, collection_name: str) -> int:
        try:
            collection = self._client.get_or_create_collection(collection_name)
            return collection.count()
        except Exception as e:
            logger.error("Failed to get collection count", collection=collection_name, error=str(e))
            raise VectorStoreException(f"Failed to get collection count: {str(e)}")

    async def collection_exists(self, collection_name: str) -> bool:
        try:
            client = self._client.get_client()
            collections = client.list_collections()
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error("Failed to check collection existence", collection=collection_name, error=str(e))
            return False