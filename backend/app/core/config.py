from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "KifPilot AI Support Agent"
    VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///E:/kifpilot-ai-support-agent/backend/data/kifpilot.db"

    # Vector Store
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen3.5:4b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars-long-enough"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Document Ingestion
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    UPLOAD_DIR: str = "./uploads"

    # Retrieval
    RETRIEVAL_MIN_SCORE: float = 0.3
    RETRIEVAL_MAX_CONTEXT: int = 8000

    # Hybrid Search
    HYBRID_RRF_K: int = 60

    # Cross-Encoder Re-ranker
    RERANKER_ENABLED: bool = False
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_MODEL_CACHE_DIR: Optional[str] = None
    RERANKER_MAX_CANDIDATES: int = 20
    RERANKER_MAX_RESULTS: int = 5
    RERANKER_TIMEOUT_SECONDS: float = 5.0
    RERANKER_BATCH_SIZE: int = 16
    RERANKER_MIN_RERANK_SCORE: float = 0.0

    # Query Expansion
    QUERY_EXPANSION_ENABLED: bool = True
    QUERY_EXPANSION_MAX_QUERIES: int = 5
    QUERY_EXPANSION_TIMEOUT_SECONDS: float = 2.0
    QUERY_EXPANSION_USE_LLM: bool = False
    QUERY_EXPANSION_LLM_MAX_EXPANSIONS: int = 3
    QUERY_EXPANSION_LLM_TIMEOUT_SECONDS: float = 3.0
    QUERY_EXPANSION_CACHE_ENABLED: bool = True
    QUERY_EXPANSION_CACHE_TTL_SECONDS: int = 3600

    # Context Compression
    CONTEXT_COMPRESSION_ENABLED: bool = True
    CONTEXT_COMPRESSION_MAX_TOKENS: int = 8000
    CONTEXT_COMPRESSION_MAX_DOCUMENTS: int = 20
    CONTEXT_COMPRESSION_MAX_CHUNKS: int = 50

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()