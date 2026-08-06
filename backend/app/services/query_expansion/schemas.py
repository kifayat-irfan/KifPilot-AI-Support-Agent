"""Schemas for Query Expansion."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class QueryExpansionConfig(BaseModel):
    """Configuration for Query Expansion."""
    model_config = ConfigDict(extra="forbid")

    # Enable/disable query expansion
    enabled: bool = Field(default=True, description="Enable query expansion")
    
    # Normalization settings
    normalize_whitespace: bool = Field(default=True, description="Normalize whitespace")
    normalize_punctuation: bool = Field(default=True, description="Normalize punctuation")
    preserve_quoted_phrases: bool = Field(default=True, description="Preserve quoted phrases")
    lowercase: bool = Field(default=True, description="Convert to lowercase")
    
    # Rule-based expansion settings
    use_synonyms: bool = Field(default=True, description="Use synonym expansion")
    use_pluralization: bool = Field(default=True, description="Generate singular/plural forms")
    use_abbreviations: bool = Field(default=True, description="Expand common abbreviations")
    use_technical_aliases: bool = Field(default=True, description="Use technical term aliases")
    use_acronyms: bool = Field(default=True, description="Expand common acronyms")
    
    # LLM-assisted expansion (optional)
    use_llm_expansion: bool = Field(default=False, description="Enable LLM-assisted expansion")
    max_llm_expansions: int = Field(default=3, ge=1, le=5, description="Max LLM-generated queries")
    llm_timeout_seconds: float = Field(default=3.0, ge=0.5, le=10.0, description="LLM expansion timeout")
    
    # General limits
    max_expanded_queries: int = Field(default=5, ge=1, le=10, description="Maximum total expanded queries")
    cache_enabled: bool = Field(default=True, description="Enable query expansion caching")
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="Cache TTL in seconds")


class ExpansionRule(BaseModel):
    """A single expansion rule."""
    model_config = ConfigDict(extra="forbid")

    pattern: str = Field(..., description="Pattern to match (regex or literal)")
    expansion: str = Field(..., description="Expanded form")
    rule_type: Literal["synonym", "pluralization", "abbreviation", "technical_alias", "acronym"] = Field(..., description="Type of rule")
    case_sensitive: bool = Field(default=False, description="Whether pattern matching is case sensitive")
    priority: int = Field(default=0, description="Rule priority (higher = applied first)")


class QueryExpansionRequest(BaseModel):
    """Request for query expansion."""
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="Original user query")
    config: Optional[QueryExpansionConfig] = Field(None, description="Optional expansion config override")
    max_expansions: Optional[int] = Field(None, ge=1, le=10, description="Override max expansions")


class QueryExpansionResult(BaseModel):
    """Result of query expansion."""
    model_config = ConfigDict(extra="forbid")

    original_query: str = Field(..., description="Original user query")
    normalized_query: str = Field(..., description="Normalized query")
    expanded_queries: List[str] = Field(..., description="Expanded query variations")
    expansion_methods: List[str] = Field(..., description="Methods used for expansion")
    expansion_time_ms: float = Field(..., description="Expansion time in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether result came from cache")


class QueryExpansionResponse(BaseModel):
    """Response from query expansion service."""
    model_config = ConfigDict(extra="forbid")

    result: QueryExpansionResult
    fallback: bool = Field(default=False, description="Whether fallback was used")


class ExpansionCacheEntry(BaseModel):
    """Cached expansion result."""
    model_config = ConfigDict(extra="forbid")

    query: str
    result: QueryExpansionResult
    created_at: datetime
    expires_at: datetime


class QueryExpansionHealthResponse(BaseModel):
    """Health check response for query expansion."""
    status: Literal["healthy", "unhealthy", "degraded"]
    cache_size: int = 0
    cache_hit_rate: float = 0.0
    llm_available: bool = False
    fallback_mode: bool = False
    error: Optional[str] = None