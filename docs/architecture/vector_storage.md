# Vector Storage

## Overview

ChromaDB-based vector storage with collection-per-KB isolation, metadata filtering, and persistence.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VECTOR STORAGE LAYER                                │
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐  │
│  │  VectorStore    │────▶│  ChromaDB       │────▶│  Persistent Storage │  │
│  │  Service        │     │  Client         │     │  (SQLite/ClickHouse)  │  │
│  └─────────────────┘     └─────────────────┘     └─────────────────────┘  │
│           │                       │                       │                │
│           ▼                       ▼                       ▼                │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐  │
│  │  Collections    │     │  HNSW Index     │     │  Metadata Filtering │  │
│  │  per KB per Org │     │  (hnsw:space)   │     │  (where clauses)    │  │
│  └─────────────────┘     └─────────────────┘     └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ChromaDB Client

```python
# services/vectorstore/client.py
class ChromaClient:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[chromadb.Client] = None
        self._collections: Dict[str, chromadb.Collection] = {}
    
    async def __aenter__(self):
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        return self
    
    async def __aexit__(self, *args):
        # ChromaDB handles persistence automatically
        pass
    
    async def get_or_create_collection(self, name: str, metadata: dict = None) -> chromadb.Collection:
        if name in self._collections:
            return self._collections[name]
        
        try:
            collection = self._client.get_collection(name)
        except Exception:
            collection = self._client.create_collection(
                name=name,
                metadata=metadata or {},
                embedding_function=None  # We provide embeddings
            )
        
        self._collections[name] = collection
        return collection
    
    async def get_collection(self, name: str) -> chromadb.Collection:
        if name in self._collections:
            return self._collections[name]
        collection = self._client.get_collection(name)
        self._collections[name] = collection
        return collection
    
    async def delete_collection(self, name: str):
        try:
            self._client.delete_collection(name)
            if name in self._collections:
                del self._collections[name]
        except Exception:
            pass  # Collection might not exist
    
    async def list_collections(self) -> List[CollectionInfo]:
        collections = self._client.list_collections()
        return [
            CollectionInfo(
                name=c.name,
                count=c.count(),
                metadata=c.metadata
            )
            for c in collections
        ]
    
    async def reset(self):
        """Dangerous: delete all collections"""
        self._client.reset()
        self._collections.clear()
```

## Vector Store Service

```python
# services/vectorstore/service.py
class VectorStoreService:
    def __init__(self, client: ChromaClient):
        self.client = client
    
    async def add_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> List[str]:
        """Add documents with embeddings to collection"""
        collection = await self.client.get_or_create_collection(collection_name)
        
        ids = [d.id for d in documents]
        embeddings = [d.embedding for d in documents]
        metadatas = [d.metadata for d in documents]
        texts = [d.text for d in documents]
        
        # ChromaDB expects lists
        await collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        return ids
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: dict = None,
        include_metadata: bool = True
    ) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        collection = await self.client.get_collection(collection_name)
        
        where_clause = filters or {}
        
        results = await collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"] if include_metadata else ["distances"]
        )
        
        return [
            VectorSearchResult(
                id=results["ids"][0][i],
                text=results["documents"][0][i] if include_metadata else "",
                metadata=results["metadatas"][0][i] if include_metadata else {},
                score=1.0 - results["distances"][0][i],  # Convert distance to similarity
                distance=results["distances"][0][i]
            )
            for i in range(len(results["ids"][0]))
        ]
    
    async def delete_document(self, collection_name: str, document_id: str):
        """Delete all chunks belonging to a document"""
        collection = await self.client.get_collection(collection_name)
        await collection.delete(where={"document_id": document_id})
    
    async def delete_collection(self, collection_name: str):
        await self.client.delete_collection(collection_name)
    
    async def get_collection_stats(self, collection_name: str) -> CollectionStats:
        collection = await self.client.get_collection(collection_name)
        count = collection.count()
        
        # Get sample to estimate dimensions
        sample = await collection.peek(limit=1)
        dimension = len(sample["embeddings"][0]) if sample["embeddings"] else 0
        
        return CollectionStats(
            name=collection_name,
            count=count,
            dimension=dimension,
            metadata=collection.metadata
        )
    
    async def update_metadata(self, collection_name: str, ids: List[str], metadatas: List[dict]):
        collection = await self.client.get_collection(collection_name)
        await collection.update(ids=ids, metadatas=metadatas)
```

## Vector Document Models

```python
# services/vectorstore/models.py
@dataclass
class VectorDocument:
    id: str
    embedding: List[float]
    text: str
    metadata: dict
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.metadata:
            self.metadata = {}

@dataclass
class VectorSearchResult:
    id: str
    text: str
    metadata: dict
    score: float  # 0-1 similarity
    distance: float  # 0-2 cosine distance

@dataclass
class CollectionInfo:
    name: str
    count: int
    metadata: dict

@dataclass
class CollectionStats:
    name: str
    count: int
    dimension: int
    metadata: dict
```

## Collection Naming & Organization

```python
# services/vectorstore/service.py
class VectorStoreService:
    def _get_collection_name(self, kb_id: str, org_id: str) -> str:
        """Generate unique collection name: org_{org_id}_kb_{kb_id}"""
        return f"org_{org_id}_kb_{kb_id}"
    
    async def create_kb_collection(self, kb_id: str, org_id: str) -> str:
        name = self._get_collection_name(kb_id, org_id)
        collection = await self.client.get_or_create_collection(
            name=name,
            metadata={
                "organization_id": org_id,
                "knowledge_base_id": kb_id,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
        )
        return collection.name
    
    async def delete_kb_collection(self, kb_id: str, org_id: str):
        name = self._get_collection_name(kb_id, org_id)
        await self.client.delete_collection(name)
    
    async def list_org_collections(self, org_id: str) -> List[CollectionInfo]:
        all_collections = await self.client.list_collections()
        return [c for c in all_collections if c.metadata.get("organization_id") == org_id]
```

## Metadata Schema

```python
# Standard metadata for all vector chunks
CHUNK_METADATA_SCHEMA = {
    "chunk_id": "uuid",           # Unique chunk identifier
    "document_id": "uuid",        # Parent document ID
    "chunk_index": "int",         # Order in document
    "page": "int",                # Page number (if applicable)
    "section": "string",          # Section heading
    "heading": "string",          # Current heading
    "token_count": "int",         # Approximate tokens
    "document_id": "uuid",        # For filtering
    "knowledge_base_id": "uuid",  # For filtering
    "organization_id": "uuid",    # For multi-tenant isolation
    "created_at": "iso_datetime", # Creation timestamp
    "content_hash": "string",     # For deduplication
}

# Example metadata
example_metadata = {
    "chunk_id": "abc-123",
    "document_id": "doc-456",
    "chunk_index": 3,
    "page": 2,
    "section": "Introduction",
    "heading": "Overview",
    "token_count": 256,
    "knowledge_base_id": "kb-789",
    "organization_id": "org-101",
    "created_at": "2026-01-15T10:30:00Z",
    "content_hash": "sha256..."
}
```

## HNSW Index Configuration

```python
# ChromaDB uses HNSW (Hierarchical Navigable Small World) by default
# Configuration via collection metadata

HNSW_CONFIG = {
    "hnsw:space": "cosine",        # Distance metric: cosine, l2, ip
    "hnsw:construction_ef": 200,   # Construction parameter (higher = better recall, slower build)
    "hnsw:search_ef": 100,         # Search parameter (higher = better recall, slower search)
    "hnsw:M": 16,                  # Max connections per layer
    "hnsw:num_threads": 4          # Parallel index construction
}

# Create collection with custom HNSW settings
async def create_collection_with_hnsw(self, name: str, config: dict = None) -> chromadb.Collection:
    hnsw_settings = {**HNSW_CONFIG, **(config or {})}
    metadata = {"hnsw:space": "cosine"}
    metadata.update({k: str(v) for k, v in hnsw_settings.items() if k != "hnsw:space"})
    
    return await self.client.get_or_create_collection(name, metadata=metadata)
```

## Persistence & Backup

```python
# services/vectorstore/service.py
class VectorStoreService:
    async def backup_collection(self, collection_name: str, backup_path: str):
        """Export collection to JSON for backup"""
        collection = await self.client.get_collection(collection_name)
        
        # Get all data in batches
        all_ids = []
        all_embeddings = []
        all_metadatas = []
        all_documents = []
        
        batch_size = 1000
        offset = 0
        
        while True:
            results = await collection.get(
                limit=batch_size,
                offset=offset,
                include=["embeddings", "metadatas", "documents"]
            )
            
            if not results["ids"]:
                break
            
            all_ids.extend(results["ids"])
            all_embeddings.extend(results["embeddings"])
            all_metadatas.extend(results["metadatas"])
            all_documents.extend(results["documents"])
            
            offset += batch_size
            if len(results["ids"]) < batch_size:
                break
        
        # Save to JSON
        backup_data = {
            "collection_name": collection_name,
            "metadata": collection.metadata,
            "count": len(all_ids),
            "ids": all_ids,
            "embeddings": all_embeddings,
            "metadatas": all_metadatas,
            "documents": all_documents
        }
        
        Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
        with open(backup_path, "w") as f:
            json.dump(backup_data, f)
    
    async def restore_collection(self, backup_path: str, new_name: str = None):
        """Restore collection from backup"""
        with open(backup_path, "r") as f:
            backup_data = json.load(f)
        
        name = new_name or backup_data["collection_name"]
        collection = await self.client.get_or_create_collection(
            name=name,
            metadata=backup_data["metadata"]
        )
        
        # Restore in batches
        batch_size = 1000
        for i in range(0, len(backup_data["ids"]), batch_size):
            end = min(i + batch_size, len(backup_data["ids"]))
            await collection.add(
                ids=backup_data["ids"][i:end],
                embeddings=backup_data["embeddings"][i:end],
                metadatas=backup_data["metadatas"][i:end],
                documents=backup_data["documents"][i:end]
            )
```

## Monitoring

```python
# Metrics
vector_search_time = Histogram(
    "vector_search_seconds",
    "Vector search time",
    ["collection"]
)

vector_add_time = Histogram(
    "vector_add_seconds",
    "Vector add time",
    ["collection"]
)

vector_collection_count = Gauge(
    "vector_collection_count",
    "Number of collections"
)

vector_document_count = Gauge(
    "vector_document_count",
    "Number of vectors per collection",
    ["collection"]
)

# In service
async def search(self, collection_name: str, ...) -> List[VectorSearchResult]:
    start = time.perf_counter()
    try:
        results = await self._search(collection_name, ...)
        vector_search_time.labels(collection=collection_name).observe(
            time.perf_counter() - start
        )
        return results
    except Exception as e:
        vector_search_errors.labels(collection=collection_name, error=type(e).__name__).inc()
        raise
```