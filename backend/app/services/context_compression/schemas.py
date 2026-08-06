"""Schemas for Context Compression."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class ContextCompressionConfig(BaseModel):
    """Configuration for Context Compression."""
    model_config = ConfigDict(extra="forbid")

    # Enable/disable compression
    enabled: bool = Field(default=True, description="Enable context compression")
    
    # Deduplication settings
    deduplicate_enabled: bool = Field(default=True, description="Enable chunk deduplication")
    deduplication_threshold: float = Field(
        default=0.95, 
        ge=0.0, 
        le=1.0, 
        description="Similarity threshold for deduplication (0-1)"
    )
    
    # Chunk merging settings
    merge_enabled: bool = Field(default=True, description="Enable adjacent chunk merging")
    merge_same_document: bool = Field(default=True, description="Only merge chunks from same document")
    merge_max_distance: int = Field(
        default=2, 
        ge=1, 
        le=10, 
        description="Maximum chunk index gap to consider for merging"
    )
    
    # Low-value removal settings
    remove_low_value: bool = Field(default=True, description="Enable low-value text removal")
    remove_empty_lines: bool = Field(default=True, description="Remove empty lines")
    remove_repeated_headers: bool = Field(default=True, description="Remove repeated headers/footers")
    remove_boilerplate: bool = Field(default=True, description="Remove boilerplate navigation text")
    
    # Preservation settings (never remove these)
    preserve_tables: bool = Field(default=True, description="Preserve table structures")
    preserve_lists: bool = Field(default=True, description="Preserve list structures")
    preserve_code_blocks: bool = Field(default=True, description="Preserve code blocks")
    preserve_warnings: bool = Field(default=True, description="Preserve warnings/notices")
    preserve_notes: bool = Field(default=True, description="Preserve notes")
    preserve_headings: bool = Field(default=True, description="Preserve headings")
    preserve_page_numbers: bool = Field(default=True, description="Preserve page numbers")
    preserve_document_order: bool = Field(default=True, description="Preserve document order")
    
    # Token budget
    max_tokens: int = Field(
        default=8000, 
        ge=1000, 
        le=128000, 
        description="Maximum tokens in compressed context"
    )
    max_documents: int = Field(
        default=20, 
        ge=1, 
        le=100, 
        description="Maximum documents to include"
    )
    max_chunks: int = Field(
        default=50, 
        ge=1, 
        le=200, 
        description="Maximum chunks to include"
    )
    
    # Token estimation
    chars_per_token: float = Field(
        default=4.0, 
        ge=3.0, 
        le=5.0, 
        description="Estimated characters per token for budgeting"
    )
    
    # Similarity calculation
    similarity_method: Literal["jaccard", "cosine", "levenshtein"] = Field(
        default="jaccard", 
        description="Method for calculating chunk similarity"
    )


class CompressionResult(BaseModel):
    """Result of context compression."""
    model_config = ConfigDict(extra="allow")

    # Compressed context
    context: str = Field(..., description="Compressed context string")
    
    # Statistics
    original_chunks: int = Field(..., description="Number of original chunks")
    compressed_chunks: int = Field(..., description="Number of compressed chunks")
    original_tokens: int = Field(..., description="Estimated original token count")
    compressed_tokens: int = Field(..., description="Estimated compressed token count")
    compression_ratio: float = Field(..., description="Compression ratio (compressed/original)")
    tokens_saved: int = Field(..., description="Estimated tokens saved")
    
    # Breakdown
    deduplicated_count: int = Field(default=0, description="Number of duplicates removed")
    merged_count: int = Field(default=0, description="Number of chunks merged")
    low_value_removed_count: int = Field(default=0, description="Number of low-value segments removed")
    
    # Timing
    compression_time_ms: float = Field(..., description="Compression time in milliseconds")
    
    # Chunk details
    chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Compressed chunk details")


class CompressionStats(BaseModel):
    """Statistics for context compression."""
    model_config = ConfigDict(extra="forbid")

    original_chunks: int
    compressed_chunks: int
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    tokens_saved: int
    deduplicated_count: int
    merged_count: int
    low_value_removed_count: int
    compression_time_ms: float


class ContextCompressionHealthResponse(BaseModel):
    """Health check response for context compression."""
    status: Literal["healthy", "unhealthy", "degraded"]
    enabled: bool = False
    fallback_mode: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class CompressionRequest(BaseModel):
    """Request for context compression."""
    model_config = ConfigDict(extra="forbid")

    chunks: List[Dict[str, Any]] = Field(..., description="Chunks to compress")
    query: str = Field(default="", description="Original query for reference")
    config: Optional["ContextCompressionConfig"] = Field(None, description="Optional config override")


class CompressionResponse(BaseModel):
    """Response from context compression."""
    model_config = ConfigDict(extra="forbid")

    result: "CompressionResult"
    fallback: bool = False