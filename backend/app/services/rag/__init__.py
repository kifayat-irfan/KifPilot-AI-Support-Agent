"""
RAG Answer Generation Engine - Grounded AI answers using retrieved document context.

This module provides a production-grade RAG engine that:
- Enforces strict guardrails (no hallucination, no outside knowledge)
- Retrieves relevant context using the retrieval engine
- Builds prompts with system instructions to only use provided context
- Generates answers with Ollama at temperature 0.0
- Calculates confidence scores based on retrieval quality
"""

from app.services.rag.service import RAGService, rag_service
from app.services.rag.answer_generator import AnswerGenerator
from app.services.rag.prompt_builder import PromptBuilder
from app.services.rag.guardrails import Guardrails
from app.services.rag.schemas import (
    RAGAskRequest,
    RAGAskResponse,
    RAGSource,
    RAGHealthResponse,
)
from app.services.rag.exceptions import (
    RAGError,
    EmptyQuestionError,
    PromptInjectionError,
    QuestionTooLongError,
    RetrievalFailedError,
    NoContextFoundError,
    GenerationFailedError,
    OllamaUnavailableError,
)

__all__ = [
    # Services
    "RAGService",
    "rag_service",
    "AnswerGenerator",
    "PromptBuilder",
    "Guardrails",
    # Schemas
    "RAGAskRequest",
    "RAGAskResponse",
    "RAGSource",
    "RAGHealthResponse",
    # Exceptions
    "RAGError",
    "EmptyQuestionError",
    "PromptInjectionError",
    "QuestionTooLongError",
    "RetrievalFailedError",
    "NoContextFoundError",
    "GenerationFailedError",
    "OllamaUnavailableError",
]