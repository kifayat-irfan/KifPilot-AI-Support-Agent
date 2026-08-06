import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Optional, Dict, Any
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.vectorstore.exceptions import (
    ChromaDBConnectionError,
    CollectionNotFoundError,
    CollectionAlreadyExistsError,
)

settings = get_settings()
logger = get_logger(__name__)


class ChromaDBServiceClient:
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection_name = "kifpilot_documents"

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )
                logger.info("ChromaDB client initialized", persist_dir=self.persist_dir)
            except Exception as e:
                logger.error("Failed to initialize ChromaDB client", error=str(e))
                raise ChromaDBConnectionError(f"Failed to initialize ChromaDB: {str(e)}")
        return self._client

    def get_or_create_collection(self, name: Optional[str] = None, metadata: Optional[Dict] = None):
        collection_name = name or self._collection_name
        try:
            return self.client.get_or_create_collection(name=collection_name, metadata=metadata)
        except Exception as e:
            logger.error("Failed to get or create collection", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to get or create collection: {str(e)}")

    def create_collection(self, name: str, metadata: Optional[Dict] = None):
        try:
            existing = self.client.list_collections()
            if any(c.name == name for c in existing):
                raise CollectionAlreadyExistsError(name)
            return self.client.create_collection(name=name, metadata=metadata)
        except CollectionAlreadyExistsError:
            raise
        except Exception as e:
            logger.error("Failed to create collection", collection=name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to create collection: {str(e)}")

    def delete_collection(self, name: str) -> bool:
        try:
            self.client.delete_collection(name=name)
            logger.info("Collection deleted", collection=name)
            return True
        except Exception as e:
            logger.error("Failed to delete collection", collection=name, error=str(e))
            raise CollectionNotFoundError(name)

    def reset(self) -> bool:
        try:
            self.client.reset()
            logger.info("ChromaDB reset completed")
            return True
        except Exception as e:
            logger.error("Failed to reset ChromaDB", error=str(e))
            raise ChromaDBConnectionError(f"Failed to reset ChromaDB: {str(e)}")

    def list_collections(self) -> List[Dict[str, Any]]:
        try:
            collections = self.client.list_collections()
            return [
                {
                    "name": c.name,
                    "count": c.count(),
                    "metadata": c.metadata,
                }
                for c in collections
            ]
        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            raise ChromaDBConnectionError(f"Failed to list collections: {str(e)}")

    def get_collection(self, name: str):
        try:
            return self.client.get_collection(name=name)
        except Exception as e:
            logger.error("Collection not found", collection=name, error=str(e))
            raise CollectionNotFoundError(name)

    def collection_exists(self, name: str) -> bool:
        try:
            collections = self.client.list_collections()
            return any(c.name == name for c in collections)
        except Exception:
            return False

    def get_collection_count(self, name: str) -> int:
        try:
            collection = self.client.get_collection(name=name)
            return collection.count()
        except Exception as e:
            logger.error("Failed to get collection count", collection=name, error=str(e))
            raise CollectionNotFoundError(name)

    def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> bool:
        try:
            collection = self.get_or_create_collection(collection_name)
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
            raise ChromaDBConnectionError(f"Failed to add documents: {str(e)}")

    def query(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            collection = self.get_collection(collection_name)
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
            raise ChromaDBConnectionError(f"Failed to query collection: {str(e)}")

    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        try:
            collection = self.get_collection(collection_name)
            collection.delete(ids=ids)
            logger.info("Documents deleted", collection=collection_name, count=len(ids))
            return True
        except Exception as e:
            logger.error("Failed to delete documents", collection=collection_name, error=str(e))
            raise ChromaDBConnectionError(f"Failed to delete documents: {str(e)}")


chromadb_service_client = ChromaDBServiceClient()