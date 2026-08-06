from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.database import init_database, close_database
from app.api.router import api_router
from app.presentation.middleware import RequestLoggingMiddleware, ErrorHandlingMiddleware
from app.services.llm import ollama_service
from app.services.vectorstore import vector_store_service
from app.monitoring import (
    MonitoringMiddleware,
    get_exporter_manager,
    update_infrastructure_metrics,
    setup_logging,
)
from app.security import (
    create_security_middleware_stack,
)
import asyncio

settings = get_settings()
logger = get_logger(__name__)

# Background task for infrastructure metrics
_metrics_task: asyncio.Task | None = None


async def _update_metrics_periodically():
    """Periodically update infrastructure metrics."""
    while True:
        try:
            update_infrastructure_metrics()
        except Exception as e:
            logger.error("Failed to update infrastructure metrics", error=str(e))
        await asyncio.sleep(30)  # Update every 30 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _metrics_task
    
    configure_logging()
    setup_logging(level=settings.LOG_LEVEL, json_format=settings.LOG_FORMAT == "json")
    logger.info("Starting up", app_name=settings.APP_NAME, env=settings.APP_ENV)
    await init_database()
    logger.info("Database initialized")
    
    # Verify Ollama service on startup
    await ollama_service.verify_startup()
    
    # Verify Vector Store on startup
    await vector_store_service.verify_startup()
    
    # Initialize exporters
    exporter_config = {
        "prometheus": {"enabled": True, "port": 9090, "path": "/metrics"},
    }
    if settings.APP_ENV == "production":
        exporter_config["otlp"] = {"enabled": True, "endpoint": "http://otel-collector:4317"}
        exporter_config["jaeger"] = {"enabled": True, "endpoint": "http://jaeger:14268/api/traces"}
    
    await get_exporter_manager(exporter_config)
    logger.info("Exporters initialized")
    
    # Start background metrics task
    _metrics_task = asyncio.create_task(_update_metrics_periodically())
    logger.info("Background metrics task started")
    
    yield
    
    # Cleanup
    if _metrics_task:
        _metrics_task.cancel()
        try:
            await _metrics_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down")
    await close_database()
    await ollama_service.close()
    await vector_store_service.close()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-ready AI Customer Support Agent",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MonitoringMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs" if settings.DEBUG else "disabled",
        }

    # Apply security middleware stack LAST (outermost)
    app = create_security_middleware_stack(app)

    return app


app = create_app()