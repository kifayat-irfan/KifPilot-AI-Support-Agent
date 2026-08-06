from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.ollama import router as ollama_router
from app.api.vector import router as vector_router
from app.api.documents import router as documents_router
from app.api.retrieval import router as retrieval_router
from app.api.rag import router as rag_router
from app.api.citations import router as citations_router
from app.api.streaming import router as streaming_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(ollama_router)
api_router.include_router(vector_router)
api_router.include_router(documents_router)
api_router.include_router(retrieval_router)
api_router.include_router(rag_router)
api_router.include_router(citations_router)
api_router.include_router(streaming_router)