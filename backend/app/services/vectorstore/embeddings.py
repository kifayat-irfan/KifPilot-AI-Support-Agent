from typing import List, Optional
from app.services.llm import ollama_service
from app.services.vectorstore.models import EmbeddingRequest, EmbeddingResponse
from app.services.vectorstore.exceptions import InvalidEmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    def __init__(self, ollama_service_instance=None):
        self._ollama_service = ollama_service_instance or ollama_service

    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        try:
            if not request.input or not any(request.input):
                raise InvalidEmbeddingError("Input cannot be empty")

            response = await self._ollama_service.generate_embeddings(request)

            if not response.embeddings or len(response.embeddings) != len(request.input):
                raise InvalidEmbeddingError("Embedding generation returned invalid results")

            logger.info("Embeddings generated successfully", count=len(response.embeddings))
            return response

        except InvalidEmbeddingError:
            raise
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise InvalidEmbeddingError(f"Embedding generation failed: {str(e)}")

    async def generate_single_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        try:
            request = EmbeddingRequest(input=[text], model=model)
            response = await self.generate_embeddings(request)
            return response.embeddings[0] if response.embeddings else []
        except Exception as e:
            logger.error("Single embedding generation failed", error=str(e))
            raise InvalidEmbeddingError(f"Single embedding generation failed: {str(e)}")

    async def generate_batch_embeddings(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        try:
            if not texts:
                raise InvalidEmbeddingError("Texts list cannot be empty")

            request = EmbeddingRequest(input=texts, model=model)
            response = await self.generate_embeddings(request)
            return response.embeddings
        except InvalidEmbeddingError:
            raise
        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise InvalidEmbeddingError(f"Batch embedding generation failed: {str(e)}")


embedding_generator = EmbeddingGenerator()