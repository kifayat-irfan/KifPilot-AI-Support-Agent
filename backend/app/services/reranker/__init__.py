"""Cross-Encoder Re-ranker Service - Re-ranks hybrid search results for improved precision."""

from app.services.reranker.schemas import (
    RerankerConfig,
    RerankerCandidate,
    RerankedResult,
    RerankerRequest,
    RerankerResponse,
    RerankerHealthResponse,
)

from app.services.reranker.exceptions import (
    RerankerError,
    ModelNotLoadedError,
    ModelLoadError,
    RerankingError,
    RerankerTimeoutError,
    InvalidCandidateError,
    EmptyCandidatesError,
    RerankerUnavailableError,
)

from app.services.reranker.model import CrossEncoderModel, get_cross_encoder_model
from app.services.reranker.ranking import Reranker, reranker
from app.services.reranker.service import RerankerService, reranker_service

__all__ = [
    # Config
    "RerankerConfig",
    # Schemas
    "RerankerCandidate",
    "RerankedResult",
    "RerankerRequest",
    "RerankerResponse",
    "RerankerHealthResponse",
    # Exceptions
    "RerankerError",
    "ModelNotLoadedError",
    "ModelLoadError",
    "RerankingError",
    "RerankerTimeoutError",
    "InvalidCandidateError",
    "EmptyCandidatesError",
    "RerankerUnavailableError",
    # Model
    "CrossEncoderModel",
    "get_cross_encoder_model",
    # Ranking
    "Reranker",
    "reranker",
    # Service
    "RerankerService",
    "reranker_service",
]