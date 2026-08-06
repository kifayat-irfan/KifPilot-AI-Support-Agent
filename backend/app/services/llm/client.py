import asyncio
import logging
from typing import List, Optional, AsyncGenerator, Union
import ollama
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.exceptions import (
    OllamaConnectionError,
    OllamaTimeoutError,
    ModelNotFoundError,
    InvalidResponseError,
    EmptyPromptError,
)

settings = get_settings()
logger = get_logger(__name__)


class OllamaServiceClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self._async_client: Optional[ollama.AsyncClient] = None
        self._sync_client: Optional[ollama.Client] = None

    @property
    def async_client(self) -> ollama.AsyncClient:
        if self._async_client is None:
            self._async_client = ollama.AsyncClient(host=self.base_url, timeout=self.timeout)
        return self._async_client

    @property
    def sync_client(self) -> ollama.Client:
        if self._sync_client is None:
            self._sync_client = ollama.Client(host=self.base_url, timeout=self.timeout)
        return self._sync_client

    def _is_connection_error(self, exc: Exception) -> bool:
        error_msg = str(exc).lower()
        return any(
            keyword in error_msg
            for keyword in [
                "connection refused",
                "connection error",
                "connect call failed",
                "connection reset",
                "timeout",
                "timed out",
            ]
        )

    def _is_timeout_error(self, exc: Exception) -> bool:
        error_msg = str(exc).lower()
        return "timeout" in error_msg or "timed out" in error_msg

    def _is_model_not_found(self, exc: Exception) -> bool:
        error_msg = str(exc).lower()
        return "not found" in error_msg or "model not found" in error_msg

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _chat_with_retry(
        self,
        messages: List[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> Union[dict, AsyncGenerator]:
        try:
            return await asyncio.wait_for(
                self.async_client.chat(
                    model=model,
                    messages=messages,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    stream=stream,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as e:
            logger.error("Ollama chat timeout", model=model, error=str(e))
            raise OllamaTimeoutError(f"Chat request timed out after {self.timeout}s")
        except ollama.ResponseError as e:
            if self._is_model_not_found(e):
                raise ModelNotFoundError(model)
            logger.error("Ollama response error", model=model, error=str(e))
            raise InvalidResponseError(f"Ollama error: {str(e)}")
        except Exception as e:
            if self._is_connection_error(e):
                logger.error("Ollama connection error", model=model, error=str(e))
                raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}")
            logger.error("Ollama chat failed", model=model, error=str(e))
            raise InvalidResponseError(f"Chat failed: {str(e)}")

    async def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> Union[dict, AsyncGenerator]:
        if not messages:
            raise EmptyPromptError("Messages list cannot be empty")

        model = model or settings.OLLAMA_CHAT_MODEL

        logger.info("Sending chat request", model=model, message_count=len(messages), stream=stream)
        return await self._chat_with_retry(messages, model, temperature, max_tokens, stream)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _embed_with_retry(self, input: Union[str, List[str]], model: str) -> List[List[float]]:
        try:
            response = await asyncio.wait_for(
                self.async_client.embed(model=model, input=input),
                timeout=self.timeout,
            )
            return response.embeddings
        except asyncio.TimeoutError as e:
            logger.error("Ollama embed timeout", model=model, error=str(e))
            raise OllamaTimeoutError(f"Embedding request timed out after {self.timeout}s")
        except ollama.ResponseError as e:
            if self._is_model_not_found(e):
                raise ModelNotFoundError(model)
            logger.error("Ollama embed response error", model=model, error=str(e))
            raise InvalidResponseError(f"Ollama error: {str(e)}")
        except Exception as e:
            if self._is_connection_error(e):
                logger.error("Ollama connection error", model=model, error=str(e))
                raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}")
            logger.error("Ollama embed failed", model=model, error=str(e))
            raise InvalidResponseError(f"Embedding failed: {str(e)}")

    async def embed(
        self,
        input: Union[str, List[str]],
        model: Optional[str] = None,
    ) -> List[List[float]]:
        model = model or settings.OLLAMA_EMBED_MODEL

        if isinstance(input, str):
            input = [input]

        if not input or not any(input):
            raise EmptyPromptError("Input cannot be empty")

        logger.info("Generating embeddings", model=model, input_count=len(input))
        return await self._embed_with_retry(input, model)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def list_models(self) -> List[str]:
        try:
            response = await asyncio.wait_for(
                self.async_client.list(),
                timeout=self.timeout,
            )
            return [model.model for model in response.models]
        except asyncio.TimeoutError as e:
            logger.error("Ollama list models timeout", error=str(e))
            raise OllamaTimeoutError(f"List models timed out after {self.timeout}s")
        except Exception as e:
            if self._is_connection_error(e):
                logger.error("Ollama connection error", error=str(e))
                raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}")
            logger.error("Failed to list models", error=str(e))
            raise InvalidResponseError(f"Failed to list models: {str(e)}")

    async def check_model_exists(self, model: str) -> bool:
        try:
            models = await self.list_models()
            return model in models
        except Exception:
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def pull_model(self, model: str) -> bool:
        try:
            await asyncio.wait_for(
                self.async_client.pull(model),
                timeout=self.timeout * 5,
            )
            return True
        except asyncio.TimeoutError as e:
            logger.error("Ollama pull model timeout", model=model, error=str(e))
            raise OllamaTimeoutError(f"Pull model timed out")
        except Exception as e:
            logger.error("Failed to pull model", model=model, error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def health_check(self) -> bool:
        try:
            await asyncio.wait_for(
                self.async_client.ps(),
                timeout=10.0,
            )
            return True
        except asyncio.TimeoutError:
            return False
        except Exception:
            return False

    async def close(self) -> None:
        if self._async_client:
            try:
                await self._async_client.close()
            except Exception:
                pass
            self._async_client = None
        self._sync_client = None


ollama_service_client = OllamaServiceClient()