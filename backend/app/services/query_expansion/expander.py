"""Query expansion logic combining normalization, rule-based expansion, and optional LLM expansion."""

import re
import time
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Lock

from app.core.config import get_settings
from app.core.logging import get_logger

from app.services.query_expansion.schemas import (
    QueryExpansionConfig,
    QueryExpansionResult,
    ExpansionCacheEntry,
)
from app.services.query_expansion.rules import (
    get_all_rules,
    get_rules_by_type,
    get_plural,
    get_singular,
    PLURALIZATION_RULES,
    SINGULAR_RULES,
)
from app.services.query_expansion.exceptions import (
    QueryExpansionError,
    NormalizationError,
    RuleExpansionError,
    LLMExpansionError,
    LLMTimeoutError,
    ExpansionCacheError,
    InvalidQueryError,
    MaxExpansionsExceededError,
)

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class ExpansionCache:
    """In-memory cache for query expansions."""
    _cache: Dict[str, ExpansionCacheEntry] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    _hits: int = 0
    _misses: int = 0
    
    def _make_key(self, query: str, config: QueryExpansionConfig) -> str:
        """Generate cache key from query and config."""
        config_str = json.dumps(config.model_dump(), sort_keys=True)
        content = f"{query}|{config_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def get(self, query: str, config: QueryExpansionConfig) -> Optional[QueryExpansionResult]:
        """Get cached expansion result."""
        with self._lock:
            key = self._make_key(query, config)
            entry = self._cache.get(key)
            if entry and entry.expires_at > datetime.utcnow():
                self._hits += 1
                return entry.result
            elif entry:
                # Expired, remove it
                del self._cache[key]
            self._misses += 1
            return None
    
    def set(self, query: str, config: QueryExpansionConfig, result: QueryExpansionResult, ttl_seconds: int) -> None:
        """Cache expansion result."""
        with self._lock:
            key = self._make_key(query, config)
            now = datetime.utcnow()
            self._cache[key] = ExpansionCacheEntry(
                query=query,
                result=result,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
            }


class QueryNormalizer:
    """Normalize user queries for consistent processing."""
    
    def __init__(self, config: QueryExpansionConfig):
        self.config = config
    
    def normalize(self, query: str) -> str:
        """Normalize a query according to config."""
        if not query or not query.strip():
            raise InvalidQueryError("Query cannot be empty")
        
        normalized = query.strip()
        
        # Preserve quoted phrases
        quoted_phrases = []
        if self.config.preserve_quoted_phrases:
            # Extract quoted phrases
            quoted_pattern = r'"([^"]*)"'
            quoted_phrases = re.findall(quoted_pattern, normalized)
            # Replace with placeholders
            for i, phrase in enumerate(quoted_phrases):
                normalized = normalized.replace(f'"{phrase}"', f"__QUOTED_{i}__")
        
        # Lowercase
        if self.config.lowercase:
            normalized = normalized.lower()
        
        # Normalize punctuation
        if self.config.normalize_punctuation:
            # Replace multiple punctuation with single
            normalized = re.sub(r'[.!?,;:]{2,}', ' ', normalized)
            # Replace special punctuation with spaces (except hyphens in words)
            normalized = re.sub(r'[^\w\s\-"\']', ' ', normalized)
            # Handle hyphens - keep them in compound words
            normalized = re.sub(r'\s+-\s+', '-', normalized)  # "word - word" -> "word-word"
            normalized = re.sub(r'(\w)-(\w)', r'\1\2', normalized)  # "word -word" -> "wordword" (but be careful)
        
        # Normalize whitespace
        if self.config.normalize_whitespace:
            normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Restore quoted phrases
        if self.config.preserve_quoted_phrases and quoted_phrases:
            for i, phrase in enumerate(quoted_phrases):
                normalized = normalized.replace(f"__QUOTED_{i}__", f'"{phrase}"')
        
        return normalized
    
    def extract_quoted_phrases(self, query: str) -> List[str]:
        """Extract quoted phrases from query."""
        return re.findall(r'"([^"]*)"', query)


class RuleBasedExpander:
    """Rule-based query expansion using predefined rules."""
    
    def __init__(self, config: QueryExpansionConfig):
        self.config = config
        self.rules = get_all_rules()
        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def expand(self, query: str) -> List[str]:
        """Expand query using rule-based approach."""
        if not self.config.use_synonyms and not self.config.use_abbreviations and \
           not self.config.use_technical_aliases and not self.config.use_acronyms:
            return []
        
        expanded = set()
        normalized_query = query.lower()
        
        # Filter rules based on config
        active_rules = self._filter_active_rules()
        
        for rule in active_rules:
            try:
                matches = self._apply_rule(normalized_query, rule)
                for match in matches:
                    expanded.add(match)
            except Exception as e:
                logger.warning(f"Rule {rule.rule_type} failed: {e}")
        
        return list(expanded)
    
    def _filter_active_rules(self) -> List:
        """Filter rules based on enabled config options."""
        active = []
        for rule in self.rules:
            if rule.rule_type == "synonym" and not self.config.use_synonyms:
                continue
            if rule.rule_type == "abbreviation" and not self.config.use_abbreviations:
                continue
            if rule.rule_type == "technical_alias" and not self.config.use_technical_aliases:
                continue
            if rule.rule_type == "acronym" and not self.config.use_acronyms:
                continue
            active.append(rule)
        return active
    
    def _apply_rule(self, query: str, rule: 'ExpansionRule') -> List[str]:
        """Apply a single expansion rule to the query."""
        results = []
        
        if not rule.case_sensitive:
            pattern = rule.pattern.lower()
            search_text = query.lower()
        else:
            pattern = rule.pattern
            search_text = query
        
        # Check if pattern matches
        if re.search(pattern, search_text):
            # Add the expansion as a new query variant
            results.append(rule.expansion)
            
            # Also create a query with the expanded term
            expanded_query = re.sub(pattern, rule.expansion, search_text, flags=re.IGNORECASE if not rule.case_sensitive else 0)
            if expanded_query != search_text:
                results.append(expanded_query)
        
        return results


class PluralizationExpander:
    """Generate singular/plural forms of query terms."""
    
    def __init__(self, config: QueryExpansionConfig):
        self.config = config
    
    def expand(self, query: str) -> List[str]:
        """Generate plural/singular variants of query terms."""
        if not self.config.use_pluralization:
            return []
        
        variants = set()
        words = query.split()
        
        for i, word in enumerate(words):
            # Try plural
            plural = get_plural(word)
            if plural and plural.lower() != word.lower():
                new_words = words.copy()
                new_words[i] = plural
                variants.add(' '.join(new_words))
            
            # Try singular
            singular = get_singular(word)
            if singular and singular.lower() != word.lower():
                new_words = words.copy()
                new_words[i] = singular
                variants.add(' '.join(new_words))
        
        return list(variants)


class QueryExpander:
    """Main query expansion orchestrator."""
    
    def __init__(self, config: Optional[QueryExpansionConfig] = None):
        self.config = config or QueryExpansionConfig()
        self.normalizer = QueryNormalizer(self.config)
        self.rule_expander = RuleBasedExpander(self.config)
        self.pluralization_expander = PluralizationExpander(self.config)
        self.cache = ExpansionCache()
        self._llm_expander = None  # Lazy loaded
    
    def expand(self, query: str, config: Optional[QueryExpansionConfig] = None) -> QueryExpansionResult:
        """Expand a query using all enabled methods."""
        start_time = time.time()
        
        # Use provided config or default
        effective_config = config or self.config
        
        if not query or not query.strip():
            raise InvalidQueryError("Query cannot be empty")
        
        # Check cache first
        if effective_config.cache_enabled:
            cached = self.cache.get(query, effective_config)
            if cached:
                cached.expansion_time_ms = (time.time() - start_time) * 1000
                return cached
        
        # Normalize
        normalized = self.normalizer.normalize(query)
        
        # Collect all expansions
        all_expansions = set()
        methods_used = []
        
        # 1. Add normalized query
        all_expansions.add(normalized)
        
        # 2. Rule-based expansion
        if effective_config.use_synonyms or effective_config.use_abbreviations or \
           effective_config.use_technical_aliases or effective_config.use_acronyms:
            rule_expansions = self.rule_expander.expand(normalized)
            all_expansions.update(rule_expansions)
            methods_used.append("rule_based")
        
        # 3. Pluralization expansion
        if effective_config.use_pluralization:
            plural_expansions = self.pluralization_expander.expand(normalized)
            all_expansions.update(plural_expansions)
            methods_used.append("pluralization")
        
        # 4. LLM expansion (optional)
        if effective_config.use_llm_expansion:
            try:
                llm_expansions = self._llm_expand(normalized, effective_config)
                all_expansions.update(llm_expansions)
                methods_used.append("llm")
            except LLMTimeoutError:
                logger.warning("LLM expansion timed out, skipping")
            except Exception as e:
                logger.warning(f"LLM expansion failed: {e}")
        
        # Limit total expansions
        max_expansions = effective_config.max_expanded_queries
        expanded_list = list(all_expansions)[:max_expansions]
        
        expansion_time_ms = (time.time() - start_time) * 1000
        
        result = QueryExpansionResult(
            original_query=query,
            normalized_query=normalized,
            expanded_queries=expanded_list,
            expansion_methods=methods_used,
            expansion_time_ms=expansion_time_ms,
            cache_hit=False,
        )
        
        # Cache result
        if effective_config.cache_enabled:
            self.cache.set(query, self.config, result, effective_config.cache_ttl_seconds)
        
        return result
    
    def _llm_expand(self, query: str, config: QueryExpansionConfig) -> List[str]:
        """Generate alternative queries using LLM (optional)."""
        # This is a placeholder - in production, integrate with actual LLM
        # For now, return empty list to indicate LLM expansion not available
        return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def clear_cache(self) -> None:
        """Clear the expansion cache."""
        self.cache.clear()


# Global singleton instance
query_expander = QueryExpander()