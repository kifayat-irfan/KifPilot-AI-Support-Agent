"""Rate limiting for KifPilot."""

import time
import asyncio
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimitTier(str, Enum):
    """Rate limit tiers for different user types."""
    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    ADMIN = "admin"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10


TIER_CONFIGS: Dict[RateLimitTier, RateLimitConfig] = {
    RateLimitTier.ANONYMOUS: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        burst_limit=3,
    ),
    RateLimitTier.AUTHENTICATED: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
        burst_limit=10,
    ),
    RateLimitTier.ADMIN: RateLimitConfig(
        requests_per_minute=200,
        requests_per_hour=5000,
        requests_per_day=50000,
        burst_limit=50,
    ),
}

SPECIAL_ENDPOINTS = {
    "/api/v1/auth/login": RateLimitConfig(requests_per_minute=5, requests_per_hour=20, requests_per_day=100, burst_limit=2),
    "/api/v1/auth/register": RateLimitConfig(requests_per_minute=3, requests_per_hour=10, requests_per_day=50, burst_limit=1),
    "/api/v1/documents/upload": RateLimitConfig(requests_per_minute=5, requests_per_hour=50, requests_per_day=200, burst_limit=2),
    "/api/v1/chat/stream": RateLimitConfig(requests_per_minute=10, requests_per_hour=100, requests_per_day=500, burst_limit=3),
}


class RateLimitBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
    
    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def get_retry_after(self) -> float:
        self._refill()
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) / self.refill_rate


class RateLimiter:
    """Rate limiter with multiple tiers and time windows."""
    
    def __init__(self):
        self._buckets: Dict[str, Dict[str, RateLimitBucket]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        logger.info("Rate limiter started")
    
    async def stop(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Rate limiter stopped")
    
    def _get_tier(self, user_id: Optional[str], is_admin: bool = False) -> RateLimitTier:
        if user_id is None:
            return RateLimitTier.ANONYMOUS
        if is_admin:
            return RateLimitTier.ADMIN
        return RateLimitTier.AUTHENTICATED
    
    def _get_config(self, tier: RateLimitTier, endpoint: str) -> RateLimitConfig:
        if endpoint in SPECIAL_ENDPOINTS:
            return SPECIAL_ENDPOINTS[endpoint]
        return TIER_CONFIGS[tier]
    
    def _get_bucket_key(self, identifier: str, window: str) -> str:
        current_window = int(time.time() / self._get_window_seconds(window))
        return f"{identifier}:{window}:{current_window}"
    
    def _get_window_seconds(self, window: str) -> int:
        return {"minute": 60, "hour": 3600, "day": 86400}[window]
    
    def _get_refill_rate(self, limit: int, window: str) -> float:
        return limit / self._get_window_seconds(window)
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        user_id: Optional[str] = None,
        is_admin: bool = False,
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limits.
        
        Returns:
            Tuple of (allowed, headers_dict)
        """
        tier = self._get_tier(user_id, is_admin)
        config = self._get_config(tier, endpoint)
        
        headers = {}
        async with self._lock:
            for window, limit in [
                ("minute", config.requests_per_minute),
                ("hour", config.requests_per_hour),
                ("day", config.requests_per_day),
            ]:
                bucket_key = self._get_bucket_key(identifier, window)
                
                if bucket_key not in self._buckets[identifier]:
                    refill_rate = self._get_refill_rate(limit, window)
                    self._buckets[identifier][bucket_key] = RateLimitBucket(limit, refill_rate)
                
                bucket = self._buckets[identifier][bucket_key]
                
                if not bucket.consume(1):
                    retry_after = bucket.get_retry_after()
                    headers = {
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                        "Retry-After": str(int(retry_after) + 1),
                    }
                    return False, headers
                
                headers[f"X-RateLimit-Limit-{window.title()}"] = str(limit)
                headers[f"X-RateLimit-Remaining-{window.title()}"] = str(int(bucket.tokens))
        
        headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        headers["X-RateLimit-Remaining"] = str(int(
            min(
                self._buckets[identifier].get(self._get_bucket_key(identifier, "minute"), RateLimitBucket(0, 0)).tokens,
                config.requests_per_minute
            )
        ))
        
        return True, headers
    
    async def _cleanup_expired(self):
        """Clean up expired buckets periodically."""
        while True:
            try:
                await asyncio.sleep(300)
                current_time = time.time()
                async with self._lock:
                    for identifier in list(self._buckets.keys()):
                        for bucket_key in list(self._buckets[identifier].keys()):
                            parts = bucket_key.split(":")
                            if len(parts) == 3:
                                window = parts[1]
                                window_start = int(parts[2]) * self._get_window_seconds(window)
                                if current_time - window_start > self._get_window_seconds(window) * 2:
                                    del self._buckets[identifier][bucket_key]
                        if not self._buckets[identifier]:
                            del self._buckets[identifier]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Rate limiter cleanup failed", error=str(e))


_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        await _rate_limiter.start()
    return _rate_limiter


async def rate_limit_dependency(
    request: "Request",
    user_id: Optional[str] = None,
    is_admin: bool = False,
):
    """FastAPI dependency for rate limiting."""
    from fastapi import HTTPException, Request
    
    limiter = await get_rate_limiter()
    identifier = request.client.host if request.client else "unknown"
    if user_id:
        identifier = f"user:{user_id}"
    
    endpoint = request.url.path
    allowed, headers = await limiter.check_rate_limit(identifier, endpoint, user_id, is_admin)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers=headers,
        )
    
    request.state.rate_limit_headers = headers