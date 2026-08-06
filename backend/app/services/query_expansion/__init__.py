"""Query Expansion Service - Expands user queries before search for improved retrieval."""

from app.services.query_expansion.schemas import (
    QueryExpansionConfig,
    ExpansionRule,
    QueryExpansionRequest,
    QueryExpansionResult,
    QueryExpansionResponse,
    ExpansionCacheEntry,
    QueryExpansionHealthResponse,
)

from app.services.query_expansion.exceptions import (
    QueryExpansionError,
    ExpansionError,
    NormalizationError,
    RuleExpansionError,
    LLMExpansionError,
    LLMTimeoutError,
    ExpansionCacheError,
    InvalidQueryError,
    MaxExpansionsExceededError,
)

from app.services.query_expansion.rules import (
    get_all_rules,
    get_rules_by_type,
    get_plural,
    get_singular,
    PLURALIZATION_RULES,
    SINGULAR_RULES,
    SYNONYM_RULES,
    ABBREVIATION_RULES,
    TECHNICAL_ALIAS_RULES,
    ACRONYM_RULES,
)

from app.services.query_expansion.expander import (
    QueryExpander,
    QueryNormalizer,
    RuleBasedExpander,
    PluralizationExpander,
    query_expander,
)

from app.services.query_expansion.service import (
    QueryExpansionService,
    query_expansion_service,
)

__all__ = [
    # Config
    "QueryExpansionConfig",
    # Schemas
    "ExpansionRule",
    "QueryExpansionRequest",
    "QueryExpansionResult",
    "QueryExpansionResponse",
    "ExpansionCacheEntry",
    "QueryExpansionHealthResponse",
    # Exceptions
    "QueryExpansionError",
    "ExpansionError",
    "NormalizationError",
    "RuleExpansionError",
    "LLMExpansionError",
    "LLMTimeoutError",
    "ExpansionCacheError",
    "InvalidQueryError",
    "MaxExpansionsExceededError",
    # Rules
    "get_all_rules",
    "get_rules_by_type",
    "get_plural",
    "get_singular",
    "PLURALIZATION_RULES",
    "SINGULAR_RULES",
    "SYNONYM_RULES",
    "ABBREVIATION_RULES",
    "TECHNICAL_ALIAS_RULES",
    "ACRONYM_RULES",
    # Expander
    "QueryExpander",
    "QueryNormalizer",
    "RuleBasedExpander",
    "PluralizationExpander",
    "query_expander",
    # Service
    "QueryExpansionService",
    "query_expansion_service",
]