from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    document_id: str
    document_name: str
    company: str
    file_type: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: str
    chunk_index: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    organization_id: Optional[str] = None


class EmbeddingRequest(BaseModel):
    input: List[str] = Field(..., min_length=1)
    model: Optional[str] = None


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: str


class CollectionInfo(BaseModel):
    name: str
    count: int
    metadata: Optional[Dict[str, Any]] = None


class CollectionsListResponse(BaseModel):
    collections: List[CollectionInfo]
    total_collections: int


class CollectionStatsResponse(BaseModel):
    name: str
    count: int
    metadata: Optional[Dict[str, Any]] = None


class InsertEmbeddingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_name: Optional[str] = Field(None, description="Collection name (auto-generated from organization_id if not provided)")
    organization_id: Optional[str] = Field(None, description="Organization ID (used to auto-generate collection name)")
    documents: List[str] = Field(..., min_length=1)
    embeddings: List[List[float]] = Field(..., min_length=1)
    metadatas: List[ChunkMetadata] = Field(..., min_length=1)
    ids: Optional[List[str]] = None


class InsertEmbeddingsResponse(BaseModel):
    success: bool
    inserted_count: int
    collection_name: str


class SimilaritySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_name: Optional[str] = Field(None, description="Collection name (auto-generated from organization_id if not provided)")
    organization_id: Optional[str] = Field(None, description="Organization ID (used to auto-generate collection name and filter results)")
    query_embedding: List[float] = Field(..., min_length=1)
    n_results: int = Field(default=5, ge=1, le=50)
    where: Optional[Dict[str, Any]] = None
    where_document: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    id: str
    document: str
    metadata: Dict[str, Any]
    distance: float
    score: float


class SimilaritySearchResponse(BaseModel):
    results: List[SearchResult]
    query_time_ms: float
    collection_name: str


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_name: Optional[str] = Field(None, description="Collection name (auto-generated from organization_id if not provided)")
    organization_id: Optional[str] = Field(None, description="Organization ID (used to auto-generate collection name)")
    ids: List[str] = Field(..., min_length=1)


class DeleteResponse(BaseModel):
    success: bool
    deleted_count: int
    collection_name: str


class ResetCollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_name: Optional[str] = Field(None, description="Collection name (auto-generated from organization_id if not provided)")
    organization_id: Optional[str] = Field(None, description="Organization ID (used to auto-generate collection name)")


class ResetCollectionResponse(BaseModel):
    success: bool
    collection_name: str
    message: str


class ChromaDBHealthResponse(BaseModel):
    status: str
    chromadb_running: bool
    collection_exists: bool
    collection_name: str
    document_count: int
    persist_dir: str
    error: Optional[str] = None