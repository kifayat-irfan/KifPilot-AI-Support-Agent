"""Context Compression Service - Reduces redundant context while preserving information."""

from app.services.context_compression.schemas import (
    ContextCompressionConfig,
    CompressionResult,
    CompressionStats,
    ContextCompressionHealthResponse,
    CompressionRequest,
    CompressionResponse,
)

from app.services.context_compression.exceptions import (
    ContextCompressionError,
    CompressionError,
    DeduplicationError,
    ChunkMergingError,
    LowValueRemovalError,
    TokenBudgetExceededError,
    InvalidChunkError,
    InvalidConfigError,
    ChunkMergingError as ChunkMergingErrorAlias,
)

from app.services.context_compression.deduplicator import (
    ChunkDeduplicator,
    DeduplicationResult,
)

from app.services.context_compression.compressor import (
    ChunkCompressor,
    CompressionResult as CompressorCompressionResult,
)

from app.services.context_compression.selector import (
    ChunkSelector,
    SelectionResult,
)

# The ContextCompressionService is not implemented yet - it's a placeholder
# For now, we expose the lower-level components directly
__all__ = [
    # Schemas
    "ContextCompressionConfig",
    "CompressionResult",
    "CompressionStats",
    "ContextCompressionHealthResponse",
    "CompressionRequest",
    "CompressionResponse",
    # Exceptions
    "ContextCompressionError",
    "CompressionError",
    "DeduplicationError",
    "ChunkMergingError",
    "LowValueRemovalError",
    "TokenBudgetExceededError",
    "InvalidChunkError",
    "InvalidConfigError",
    # Deduplicator
    "ChunkDeduplicator",
    "DeduplicationResult",
    # Compressor
    "ChunkCompressor",
    # Selector
    "ChunkSelector",
    "SelectionResult",
]