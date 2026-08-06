from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID


class VectorStoreRepository(ABC):
    @abstractmethod
    async def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
    ) -> bool:
        pass

    @abstractmethod
    async def query(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        pass

    @abstractmethod
    async def delete_documents(
        self, collection_name: str, ids: List[str]
    ) -> bool:
        pass

    @abstractmethod
    async def get_collection_count(self, collection_name: str) -> int:
        pass

    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        pass