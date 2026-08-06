"""BM25 keyword search implementation with incremental updates."""

import os
import pickle
import logging
import time
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
from threading import RLock

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.hybrid_search.exceptions import (
    BM25IndexError,
    BM25IndexNotFoundError,
    BM25IndexBuildError,
    BM25IndexUpdateError,
    BM25SearchError,
)
from app.services.vectorstore import vector_store_service
from app.services.vectorstore.models import SearchResult

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class BM25Document:
    """Document stored in BM25 index."""
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    metadata: Dict[str, Any]
    tokenized_text: List[str] = field(default_factory=list)


@dataclass
class BM25IndexState:
    """State of the BM25 index for persistence."""
    documents: Dict[str, BM25Document]
    doc_freqs: Dict[str, int]
    doc_lengths: Dict[str, int]
    avg_doc_length: float
    total_docs: int
    last_updated: float
    version: int = 1


class BM25Indexer:
    """BM25 keyword search index with incremental updates."""

    def __init__(
        self,
        index_path: Optional[str] = None,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ):
        """
        Initialize BM25 indexer.
        
        Args:
            index_path: Path to save/load index (default from settings)
            k1: Term frequency saturation parameter (default 1.5)
            b: Document length normalization parameter (default 0.75)
            epsilon: Score floor for negative IDF (default 0.25)
        """
        self._k1 = k1
        self._b = b
        self._epsilon = epsilon
        
        # Index path
        if index_path:
            self._index_path = Path(index_path)
        else:
            self._index_path = Path(getattr(settings, 'BM25_INDEX_PATH', './data/bm25_index.pkl'))
        
        # Ensure index directory exists
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Index state
        self._documents: Dict[str, BM25Document] = {}
        self._doc_freqs: Dict[str, int] = defaultdict(int)
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length: float = 0.0
        self._total_docs: int = 0
        self._last_updated: float = 0.0
        self._version: int = 1
        
        # Thread safety
        self._lock = RLock()
        
        # Initialize tokenizer
        self._init_tokenizer()
        
        # Try to load existing index
        self._load_index()

    def _init_tokenizer(self):
        """Initialize text tokenizer."""
        try:
            import nltk
            # Ensure required NLTK data is downloaded
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            try:
                nltk.data.find('tokenizers/punkt_tab')
            except LookupError:
                nltk.download('punkt_tab', quiet=True)
            self._tokenizer = nltk.word_tokenize
        except Exception:
            # Fallback to simple tokenization
            import re
            self._tokenizer = lambda text: re.findall(r'\b\w+\b', text.lower())

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        if not text:
            return []
        try:
            tokens = self._tokenizer(text)
            # Filter out very short tokens and stopwords
            return [t.lower() for t in tokens if len(t) > 2]
        except Exception:
            # Fallback
            import re
            return [t.lower() for t in re.findall(r'\b\w+\b', text.lower()) if len(t) > 2]

    def _calculate_avg_doc_length(self) -> float:
        """Calculate average document length."""
        if not self._doc_lengths:
            return 0.0
        return sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def add_document(
        self,
        chunk_id: str,
        document_id: str,
        document_name: str,
        text: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Add or update a document in the index.
        
        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document identifier
            document_name: Document filename
            text: Chunk text content
            metadata: Additional metadata
        """
        with self._lock:
            # Tokenize text
            tokenized = self._tokenize(text)
            
            # Remove old document if exists
            if chunk_id in self._documents:
                self._remove_from_index(chunk_id)
            
            # Create document
            doc = BM25Document(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name=document_name,
                text=text,
                metadata=metadata,
                tokenized_text=tokenized,
            )
            
            # Update index
            self._documents[chunk_id] = doc
            doc_length = len(tokenized)
            self._doc_lengths[chunk_id] = doc_length
            
            # Update document frequencies
            unique_terms = set(tokenized)
            for term in unique_terms:
                self._doc_freqs[term] += 1
            
            self._total_docs = len(self._documents)
            self._avg_doc_length = self._calculate_avg_doc_length()
            self._last_updated = time.time()
            self._version += 1
            
            logger.debug(f"Added document to BM25 index: {chunk_id}")

    def remove_document(self, chunk_id: str) -> bool:
        """
        Remove a document from the index.
        
        Args:
            chunk_id: Chunk identifier to remove
            
        Returns:
            True if document was removed, False if not found
        """
        with self._lock:
            if chunk_id not in self._documents:
                return False
            
            self._remove_from_index(chunk_id)
            self._total_docs = len(self._documents)
            self._avg_doc_length = self._calculate_avg_doc_length()
            self._last_updated = time.time()
            self._version += 1
            
            logger.debug(f"Removed document from BM25 index: {chunk_id}")
            return True

    def _remove_from_index(self, chunk_id: str) -> None:
        """Internal method to remove document from index structures."""
        doc = self._documents.pop(chunk_id, None)
        if not doc:
            return
        
        # Update document frequencies
        unique_terms = set(doc.tokenized_text)
        for term in unique_terms:
            self._doc_freqs[term] -= 1
            if self._doc_freqs[term] <= 0:
                del self._doc_freqs[term]
        
        self._doc_lengths.pop(chunk_id, None)

    def search(
        self,
        query: str,
        top_k: int = 10,
        minimum_score: float = 0.0,
        filter_document_ids: Optional[List[str]] = None,
    ) -> List[Tuple[BM25Document, float]]:
        """
        Search the BM25 index.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            minimum_score: Minimum BM25 score threshold
            filter_document_ids: Optional list of document IDs to filter by
            
        Returns:
            List of (document, score) tuples
        """
        with self._lock:
            if not self._documents:
                return []
            
            # Tokenize query
            query_terms = self._tokenize(query)
            if not query_terms:
                return []
            
            # Calculate IDF for each query term
            idf = {}
            N = self._total_docs
            for term in query_terms:
                df = self._doc_freqs.get(term, 0)
                if df > 0:
                    # IDF with smoothing (Robertson-Spärck Jones)
                    idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                else:
                    idf[term] = 0.0
            
            # Score all documents
            scored_docs = []
            for chunk_id, doc in self._documents.items():
                # Apply document ID filter if provided
                if filter_document_ids and doc.document_id not in filter_document_ids:
                    continue
                
                score = self._calculate_bm25_score(doc, query_terms, idf)
                
                if score >= minimum_score:
                    scored_docs.append((doc, score))
            
            # Sort by score descending
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            return scored_docs[:top_k]

    def _calculate_bm25_score(
        self,
        doc: BM25Document,
        query_terms: List[str],
        idf: Dict[str, float],
    ) -> float:
        """Calculate BM25 score for a document."""
        doc_length = self._doc_lengths.get(doc.chunk_id, len(doc.tokenized_text))
        
        score = 0.0
        term_counts = Counter(doc.tokenized_text)
        
        for term in query_terms:
            tf = term_counts.get(term, 0)
            if tf == 0:
                continue
            
            idf_value = idf.get(term, 0.0)
            if idf_value <= 0:
                continue
            
            # BM25 formula
            numerator = tf * (self._k1 + 1)
            denominator = tf + self._k1 * (1 - self._b + self._b * doc_length / self._avg_doc_length)
            score += idf_value * numerator / denominator
        
        # Apply score floor
        return max(score, self._epsilon)

    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            return {
                "total_documents": self._total_docs,
                "total_terms": len(self._doc_freqs),
                "avg_doc_length": round(self._avg_doc_length, 2),
                "last_updated": self._last_updated,
                "version": self._version,
                "index_path": str(self._index_path),
            }

    def save_index(self) -> None:
        """Save index to disk."""
        with self._lock:
            state = BM25IndexState(
                documents=self._documents,
                doc_freqs=dict(self._doc_freqs),
                doc_lengths=dict(self._doc_lengths),
                avg_doc_length=self._avg_doc_length,
                total_docs=self._total_docs,
                last_updated=self._last_updated,
                version=self._version,
            )
            
            try:
                with open(self._index_path, 'wb') as f:
                    pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
                logger.info(f"BM25 index saved to {self._index_path}")
            except Exception as e:
                raise BM25IndexError(f"Failed to save BM25 index: {str(e)}")

    def _load_index(self) -> None:
        """Load index from disk."""
        if not self._index_path.exists():
            logger.info("No existing BM25 index found, starting fresh")
            return
        
        try:
            with open(self._index_path, 'rb') as f:
                state = pickle.load(f)
            
            if not isinstance(state, BM25IndexState):
                logger.warning("Invalid index format, starting fresh")
                return
            
            self._documents = state.documents
            self._doc_freqs = defaultdict(int, state.doc_freqs)
            self._doc_lengths = state.doc_lengths
            self._avg_doc_length = state.avg_doc_length
            self._total_docs = state.total_docs
            self._last_updated = state.last_updated
            self._version = state.version
            
            logger.info(f"BM25 index loaded: {self._total_docs} documents, {len(self._doc_freqs)} terms")
        except Exception as e:
            logger.warning(f"Failed to load BM25 index: {e}, starting fresh")

    async def rebuild_index(
        self,
        vector_store=None,
        organization_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> int:
        """
        Rebuild index from vector store.
        
        Args:
            vector_store: Vector store service (uses default if not provided)
            organization_id: Optional organization ID to filter chunks
            batch_size: Number of chunks to process per batch
            
        Returns:
            Number of chunks indexed
        """
        vector_store = vector_store or vector_store_service
        
        with self._lock:
            # Clear existing index
            self._documents.clear()
            self._doc_freqs.clear()
            self._doc_lengths.clear()
            self._total_docs = 0
            self._avg_doc_length = 0.0
            self._version += 1
        
        indexed_count = 0
        offset = 0
        
        while True:
            try:
                # Use vector store to get chunks (this is a workaround since
                # we don't have a direct API to list all chunks)
                # In practice, you might want a dedicated method in vector store
                
                # For now, we'll use a search with empty query to get chunks
                # This is a workaround - ideally vector store would have a list_all_chunks method
                from app.services.vectorstore.models import SimilaritySearchRequest
                import numpy as np
                
                # Generate a dummy embedding to get all chunks
                dummy_embedding = np.zeros(768).tolist()  # Adjust dimension as needed
                
                search_request = SimilaritySearchRequest(
                    organization_id=organization_id,
                    query_embedding=dummy_embedding,
                    n_results=batch_size,
                    where=None,
                )
                
                response = await vector_store.similarity_search(search_request)
                
                if not response.results:
                    break
                
                for result in response.results:
                    metadata = result.metadata or {}
                    self.add_document(
                        chunk_id=result.id,
                        document_id=metadata.get("document_id", ""),
                        document_name=metadata.get("document_name", "Unknown"),
                        text=result.document,
                        metadata=metadata,
                    )
                    indexed_count += 1
                
                if len(response.results) < batch_size:
                    break
                    
                offset += batch_size
                
            except Exception as e:
                logger.error(f"Error during index rebuild: {e}")
                break
        
        # Save after rebuild
        self.save_index()
        logger.info(f"BM25 index rebuilt with {indexed_count} documents")
        return indexed_count


# Singleton instance
bm25_indexer = BM25Indexer()