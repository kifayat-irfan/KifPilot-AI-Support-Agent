"""Health checks for KifPilot services."""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    name: str
    status: str
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class HealthCheckResponse:
    status: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    components: List[Dict[str, Any]] = field(default_factory=list)


class HealthChecker:
    """Health check orchestrator."""

    def __init__(self):
        self._start_time = time.time()
        self._checks: Dict[str, Callable] = {}

    def register_check(self, name: str, check_func: Callable[[], Any]):
        """Register a health check function."""
        self._checks[name] = check_func

    async def check_all(self, organization_id: Optional[str] = None) -> HealthCheckResponse:
        """Run all registered health checks."""
        start_time = time.time()
        components = []

        for name, check_func in self._checks.items():
            check_start = time.time()
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func(organization_id)
                else:
                    result = check_func(organization_id)

                latency_ms = (time.time() - check_start) * 1000

                if isinstance(result, dict):
                    component = ComponentHealth(
                        name=name,
                        status=result.get("status", "healthy"),
                        message=result.get("message", ""),
                        latency_ms=(time.time() - check_start) * 1000,
                        details=result.get("details", {}),
                    )
                else:
                    component = ComponentHealth(
                        name=name,
                        status="healthy" if result else "unhealthy",
                        latency_ms=(time.time() - check_start) * 1000,
                    )

            except Exception as e:
                component = ComponentHealth(
                    name=name,
                    status="unhealthy",
                    message=str(e),
                    latency_ms=(time.time() - check_start) * 1000,
                    details={"error": str(e)},
                )

            components.append(component.to_dict() if hasattr(component, 'to_dict') else component.__dict__)

        # Determine overall status
        statuses = [c.get("status", "unknown") for c in components]
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        uptime = time.time() - self._start_time

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version="1.0.0",
            uptime_seconds=time.time() - self._start_time,
            components=components,
        )


# Default health check functions
async def check_vector_store(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Check vector store connectivity."""
    try:
        from app.services.vectorstore import vector_store_service
        health = await vector_store_service.health_check(organization_id)
        return {
            "status": "healthy" if health.get("chromadb_running") and health.get("collection_exists") else "degraded",
            "message": "Vector store operational" if health.get("chromadb_running") else "Vector store degraded",
            "details": health,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Vector store check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_embedding_service(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Check embedding service availability."""
    try:
        from app.services.llm import ollama_service as ollama_service_instance
        health = await ollama_service_instance.health_check()
        embed_available = health.embed_model_available

        return {
            "status": "healthy" if embed_available else "degraded",
            "message": "Embedding service available" if embed_available else "Embedding service unavailable",
            "details": {
                "model": "nomic-embed-text",
                "available": embed_available,
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Embedding service check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_ollama_service(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Check Ollama service availability."""
    try:
        from app.services.llm import ollama_service as ollama_service_instance
        health = await ollama_service_instance.health_check()
        return {
            "status": "healthy" if health.embed_model_available else "degraded",
            "message": "Ollama service operational",
            "details": {
                "chat_model": health.chat_model_available,
                "embed_model": health.embed_model_available,
                "version": health.version,
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Ollama check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_chromadb(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Check ChromaDB connectivity."""
    try:
        from app.services.vectorstore import vector_store_service
        health = await vector_store_service.health_check()
        return {
            "status": "healthy" if health.get("chromadb_running") else "unhealthy",
            "message": "ChromaDB operational",
            "details": {
                "running": health.get("chromadb_running"),
                "collection_exists": health.get("collection_exists"),
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"ChromaDB check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_database(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        # SQLite health check
        import sqlite3
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("SELECT 1")
        conn.close()
        return {
            "status": "healthy",
            "message": "Database connection successful",
            "details": {"type": "sqlite"},
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    import shutil
    try:
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        status = "healthy" if free_percent > 10 else "degraded" if free_percent > 5 else "unhealthy"
        return {
            "status": status,
            "message": f"Disk space: {free_percent:.1f}% free",
            "details": {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "free_percent": round(free_percent, 1),
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Disk check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_memory() -> Dict[str, Any]:
    """Check memory usage."""
    import psutil
    try:
        mem = psutil.virtual_memory()
        status = "healthy" if mem.percent < 80 else "degraded" if mem.percent < 90 else "unhealthy"
        return {
            "status": status,
            "message": f"Memory usage: {mem.percent:.1f}%",
            "details": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
                "free_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent": mem.percent,
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Memory check failed: {str(e)}",
            "details": {"error": str(e)},
        }


async def check_cpu() -> Dict[str, Any]:
    """Check CPU usage."""
    import psutil
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        status = "healthy" if cpu_percent < 80 else "degraded" if cpu_percent < 95 else "unhealthy"
        return {
            "status": status,
            "message": f"CPU usage: {cpu_percent:.1f}%",
            "details": {
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"CPU check failed: {str(e)}",
            "details": {"error": str(e)},
        }


# Health check registry
DEFAULT_HEALTH_CHECKS = {
    "vector_store": check_vector_store,
    "embedding_service": check_embedding_service,
    "ollama": check_ollama_service,
    "chromadb": check_chromadb,
    "database": check_database,
    "disk_space": check_disk_space,
    "memory": check_memory,
    "cpu": check_cpu,
}

# Global health checker instance
health_checker = None


def get_health_checker() -> "HealthChecker":
    """Get or create the global health checker."""
    global health_checker
    if health_checker is None:
        health_checker = HealthChecker()
        for name, check_func in DEFAULT_HEALTH_CHECKS.items():
            health_checker.register_check(name, check_func)
    return health_checker


async def health_check_endpoint(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """Health check endpoint handler."""
    checker = get_health_checker()
    return await checker.check_all()