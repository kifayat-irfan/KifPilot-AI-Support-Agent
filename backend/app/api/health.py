from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import get_db_session
from app.monitoring import (
    get_metrics,
    get_content_type,
    health_check_endpoint,
    get_health_checker,
    check_vector_store,
    check_embedding_service,
    check_ollama_service,
    check_chromadb,
    check_database,
    check_disk_space,
    check_memory,
    check_cpu,
)

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
    }


@router.get("/database")
async def database_health_check(session: AsyncSession = Depends(get_db_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }


@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=get_content_type(),
    )


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with all components."""
    checker = get_health_checker()
    result = await checker.check_all()
    # Convert dataclass to dict
    return {
        "status": result.status,
        "timestamp": result.timestamp,
        "version": result.version,
        "uptime_seconds": result.uptime_seconds,
        "components": result.components,
    }


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks all critical dependencies."""
    checker = get_health_checker()
    result = await checker.check_all()
    
    # Ready if not unhealthy
    is_ready = result.status != "unhealthy"
    
    return {
        "ready": is_ready,
        "status": result.status,
        "checks": result.components,
    }


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe - basic service availability."""
    return {"alive": True}


# Individual component health checks for debugging
@router.get("/vector-store")
async def vector_store_check():
    """Check vector store connectivity."""
    return await check_vector_store()


@router.get("/embedding-service")
async def embedding_service_check():
    """Check embedding service availability."""
    return await check_embedding_service()


@router.get("/ollama")
async def ollama_check():
    """Check Ollama service availability."""
    return await check_ollama_service()


@router.get("/chromadb")
async def chromadb_check():
    """Check ChromaDB connectivity."""
    return await check_chromadb()


@router.get("/database-connection")
async def database_check():
    """Check database connectivity."""
    return await check_database()


@router.get("/disk-space")
async def disk_space_check():
    """Check available disk space."""
    return await check_disk_space()


@router.get("/memory")
async def memory_check():
    """Check memory usage."""
    return await check_memory()


@router.get("/cpu")
async def cpu_check():
    """Check CPU usage."""
    return await check_cpu()