"""
Streaming Chat Service - Production-grade SSE streaming for RAG answers.

This module provides a production-grade streaming chat service that:
- Streams tokens in real-time using Server-Sent Events (SSE)
- Emits structured events: start, retrieval, token, citations, complete
- Handles client disconnection and timeouts gracefully
- Integrates with Retrieval Engine, RAG Engine, and Citation Engine
"""

from app.services.streaming.service import StreamingService, streaming_service
from app.services.streaming.events import SSEFormatter, SSEParser
from app.services.streaming.schemas import (
    StreamChatRequest,
    StreamStartEvent,
    StreamRetrievalEvent,
    StreamTokenEvent,
    StreamCitationsEvent,
    StreamCompleteEvent,
    StreamErrorEvent,
    StreamEvent,
    StreamHealthResponse,
    StreamChatResponse,
)
from app.services.streaming.exceptions import (
    StreamingError,
    RetrievalFailedError,
    NoContextFoundError,
    GenerationFailedError,
    OllamaUnavailableError,
    CitationGenerationError,
    StreamingTimeoutError,
    ClientDisconnectedError,
    GuardrailsError,
)

__all__ = [
    # Services
    "StreamingService",
    "streaming_service",
    "SSEFormatter",
    "SSEParser",
    # Schemas
    "StreamChatRequest",
    "StreamStartEvent",
    "StreamRetrievalEvent",
    "StreamTokenEvent",
    "StreamCitationsEvent",
    "StreamCompleteEvent",
    "StreamErrorEvent",
    "StreamEvent",
    "StreamHealthResponse",
    "StreamChatResponse",
    # Exceptions
    "StreamingError",
    "RetrievalFailedError",
    "NoContextFoundError",
    "GenerationFailedError",
    "OllamaUnavailableError",
    "CitationGenerationError",
    "StreamingTimeoutError",
    "ClientDisconnectedError",
    "GuardrailsError",
]