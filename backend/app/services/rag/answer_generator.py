import time
from typing import List, Optional
from app.services.llm import ollama_service
from app.services.llm.models import ChatCompletionRequest, ChatMessage, ModelRole
from app.services.rag.schemas import RAGSource
from app.services.rag.prompt_builder import PromptBuilder
from app.services.rag.exceptions import GenerationFailedError, OllamaUnavailableError
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AnswerGenerator:
    """Generates answers using Ollama with strict temperature settings."""

    DEFAULT_TEMPERATURE = 0.0
    DEFAULT_TOP_P = 1.0
    DEFAULT_MAX_TOKENS = 2048

    def __init__(self, ollama=None):
        self._ollama = ollama or ollama_service
        self._last_token_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    async def generate(
        self,
        question: str,
        context: str,
        sources: List[RAGSource],
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        Generate answer using Ollama with strict settings.
        
        Args:
            question: User's question
            context: Retrieved context
            sources: Source documents
            temperature: Sampling temperature (default 0.0)
            top_p: Top-p sampling (default 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated answer string
        """
        temp = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        p = top_p if top_p is not None else self.DEFAULT_TOP_P
        max_t = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS

        # Build prompt with sources
        messages = PromptBuilder.build_prompt_with_sources(question, context, sources)

        request = ChatCompletionRequest(
            messages=[ChatMessage(role=ModelRole(m["role"]), content=m["content"]) for m in messages],
            model=settings.OLLAMA_CHAT_MODEL,
            temperature=temp,
            top_p=p,
            max_tokens=max_t,
            stream=False,
        )

        try:
            logger.info(
                "Generating answer",
                question=question[:100],
                context_chars=len(context),
                sources_count=len(sources),
                temperature=temp,
            )

            response = await self._ollama.chat_completion(request)
            
            answer = response.message.content.strip()
            
            # Track token usage
            self._last_token_usage = {
                "prompt_tokens": getattr(response, 'prompt_eval_count', 0),
                "completion_tokens": getattr(response, 'eval_count', 0),
            }

            logger.info(
                "Answer generated",
                question=question[:100],
                answer_length=len(answer),
                total_duration=response.total_duration,
                prompt_tokens=self._last_token_usage["prompt_tokens"],
                completion_tokens=self._last_token_usage["completion_tokens"],
            )

            return answer

        except Exception as e:
            logger.error("Answer generation failed", error=str(e), question=question[:100])
            
            # Check if it's an Ollama availability issue
            error_str = str(e).lower()
            if "connection" in error_str or "unavailable" in error_str or "not found" in error_str:
                raise OllamaUnavailableError()
            
            raise GenerationFailedError(str(e))

    async def health_check(self) -> bool:
        """Check if Ollama is available for answer generation."""
        try:
            health = await self._ollama.health_check()
            return health.ollama_running and health.chat_model_available
        except Exception:
            return False