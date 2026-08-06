from typing import List, Optional, AsyncGenerator
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.client import OllamaServiceClient, ollama_service_client
from app.services.llm.models import (
    ChatMessage,
    ModelRole,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamChunk,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelInfo,
    ModelsListResponse,
    OllamaHealthResponse,
)
from app.services.llm.exceptions import (
    OllamaConnectionError,
    OllamaTimeoutError,
    ModelNotFoundError,
    InvalidResponseError,
    EmptyPromptError,
)
from app.monitoring import (
    ollama_generation_duration,
    ollama_embedding_duration,
    ollama_models_loaded,
    record_ai_tokens,
)

settings = get_settings()
logger = get_logger(__name__)


class OllamaService:
    def __init__(self, client: Optional[OllamaServiceClient] = None):
        self._client = client or ollama_service_client

    async def health_check(self) -> OllamaHealthResponse:
        base_url = settings.OLLAMA_BASE_URL
        chat_model = settings.OLLAMA_CHAT_MODEL
        embed_model = settings.OLLAMA_EMBED_MODEL

        ollama_running = False
        chat_model_available = False
        embed_model_available = False
        error = None

        try:
            ollama_running = await self._client.health_check()
        except Exception as e:
            error = str(e)
            logger.warning("Ollama health check failed", error=error)

        if ollama_running:
            try:
                chat_model_available = await self._client.check_model_exists(chat_model)
                embed_model_available = await self._client.check_model_exists(embed_model)
            except Exception as e:
                error = str(e)
                logger.warning("Model availability check failed", error=error)

        overall_status = "healthy" if (ollama_running and chat_model_available and embed_model_available) else "unhealthy"

        return OllamaHealthResponse(
            status=overall_status,
            ollama_running=ollama_running,
            chat_model_available=chat_model_available,
            embed_model_available=embed_model_available,
            base_url=base_url,
            chat_model=chat_model,
            embed_model=embed_model,
            error=error,
        )

    async def list_models(self) -> ModelsListResponse:
        try:
            model_names = await self._client.list_models()
            models = [
                ModelInfo(name=name) for name in model_names
            ]
            return ModelsListResponse(models=models)
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            raise

    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        import time
        start_time = time.time()
        try:
            messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]
            
            response = await self._client.chat(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
            )

            duration = time.time() - start_time
            
            # Record metrics
            try:
                ollama_generation_duration.labels(model=request.model or settings.OLLAMA_CHAT_MODEL, stream="false").observe(duration)
                if response.get("prompt_eval_count") and response.get("eval_count"):
                    record_ai_tokens(
                        request.model or settings.OLLAMA_CHAT_MODEL,
                        response.get("prompt_eval_count", 0),
                        response.get("eval_count", 0)
                    )
            except Exception as e:
                logger.warning(f"Failed to record Ollama chat metrics: {e}")

            if isinstance(response, dict):
                message_data = response.get("message", {})
                return ChatCompletionResponse(
                    model=response.get("model", request.model or settings.OLLAMA_CHAT_MODEL),
                    message=ChatMessage(
                        role=ModelRole(message_data.get("role", "assistant")),
                        content=message_data.get("content", ""),
                    ),
                    done=response.get("done", True),
                    total_duration=response.get("total_duration"),
                    load_duration=response.get("load_duration"),
                    prompt_eval_count=response.get("prompt_eval_count"),
                    prompt_eval_duration=response.get("prompt_eval_duration"),
                    eval_count=response.get("eval_count"),
                    eval_duration=response.get("eval_duration"),
                )
            else:
                raise InvalidResponseError("Expected dict response for non-streaming chat")
        except (OllamaConnectionError, OllamaTimeoutError, ModelNotFoundError, EmptyPromptError):
            raise
        except Exception as e:
            logger.error("Chat completion failed", error=str(e))
            raise InvalidResponseError(f"Chat completion failed: {str(e)}")

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[ChatStreamChunk, None]:
        import time
        start_time = time.time()
        total_prompt_tokens = 0
        total_completion_tokens = 0
        try:
            messages = [{"role": msg.role.value, "content": msg.content} for msg in request.messages]
            
            stream = await self._client.chat(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if isinstance(chunk, dict):
                    # Track token counts
                    if chunk.get("prompt_eval_count"):
                        total_prompt_tokens = chunk.get("prompt_eval_count")
                    if chunk.get("eval_count"):
                        total_completion_tokens = chunk.get("eval_count")
                    
                    message_data = chunk.get("message", {})
                    yield ChatStreamChunk(
                        model=chunk.get("model", request.model or settings.OLLAMA_CHAT_MODEL),
                        message=ChatMessage(
                            role=ModelRole(message_data.get("role", "assistant")),
                            content=message_data.get("content", ""),
                        ),
                        done=chunk.get("done", False),
                        total_duration=chunk.get("total_duration"),
                        load_duration=chunk.get("load_duration"),
                        prompt_eval_count=chunk.get("prompt_eval_count"),
                        prompt_eval_duration=chunk.get("prompt_eval_duration"),
                        eval_count=chunk.get("eval_count"),
                        eval_duration=chunk.get("eval_duration"),
                    )
                    
                    # Record metrics on completion
                    if chunk.get("done"):
                        duration = time.time() - start_time
                        try:
                            ollama_generation_duration.labels(model=request.model or settings.OLLAMA_CHAT_MODEL, stream="true").observe(duration)
                            if total_prompt_tokens > 0 or total_completion_tokens > 0:
                                record_ai_tokens(
                                    request.model or settings.OLLAMA_CHAT_MODEL,
                                    total_prompt_tokens,
                                    total_completion_tokens
                                )
                        except Exception as e:
                            logger.warning(f"Failed to record Ollama stream metrics: {e}")
                else:
                    logger.warning("Unexpected stream chunk type", chunk_type=type(chunk))
        except (OllamaConnectionError, OllamaTimeoutError, ModelNotFoundError, EmptyPromptError):
            raise
        except Exception as e:
            logger.error("Chat stream failed", error=str(e))
            raise InvalidResponseError(f"Chat stream failed: {str(e)}")

    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        import time
        start_time = time.time()
        try:
            model = request.model or settings.OLLAMA_EMBED_MODEL
            embeddings = await self._client.embed(input=request.input, model=model)
            
            duration = time.time() - start_time
            
            # Record metrics
            try:
                ollama_embedding_duration.labels(model=model).observe(duration)
            except Exception as e:
                logger.warning(f"Failed to record Ollama embedding metrics: {e}")
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
            )
        except (OllamaConnectionError, OllamaTimeoutError, ModelNotFoundError, EmptyPromptError):
            raise
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise InvalidResponseError(f"Embedding generation failed: {str(e)}")

    async def verify_startup(self) -> None:
        logger.info("Verifying Ollama service on startup...")
        
        health = await self.health_check()
        
        if not health.ollama_running:
            logger.warning(
                "Ollama service is not running",
                base_url=health.base_url,
            )
        else:
            logger.info("Ollama service is running", base_url=health.base_url)

        if not health.chat_model_available:
            logger.warning(
                "Chat model not available",
                model=health.chat_model,
            )
        else:
            logger.info("Chat model is available", model=health.chat_model)

        if not health.embed_model_available:
            logger.warning(
                "Embedding model not available",
                model=health.embed_model,
            )
        else:
            logger.info("Embedding model is available", model=health.embed_model)

    async def close(self) -> None:
        await self._client.close()


ollama_service = OllamaService()