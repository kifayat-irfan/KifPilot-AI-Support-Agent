from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4


@dataclass
class ParsedPage:
    page_number: int
    text: str
    headings: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedDocument:
    pages: List[ParsedPage]
    total_pages: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    headings: List[Dict[str, Any]] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DocumentChunk:
    chunk_id: str
    chunk_index: int
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    heading: Optional[str] = None
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_chunk_metadata(self, document_id: str, document_name: str, company: str, file_type: str) -> Dict[str, Any]:
        return {
            "document_id": document_id,
            "document_name": document_name,
            "company": company,
            "file_type": file_type,
            "page": self.page,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "created_at": datetime.utcnow(),
        }


@dataclass
class DocumentMetadata:
    document_id: str
    filename: str
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    company: str = "default"
    page_count: int = 0
    chunk_count: int = 0
    embeddings_created: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)