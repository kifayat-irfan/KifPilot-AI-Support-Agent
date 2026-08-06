from fastapi import APIRouter
from app.presentation.api.v1.routes import (
    conversations,
    messages,
    knowledge_bases,
    documents,
    chat,
    search,
    auth,
    health,
    organizations,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(knowledge_bases.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(search.router)