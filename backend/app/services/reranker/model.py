"""Cross-Encoder model loading and inference."""

import os
import time
import logging
from typing import List, Optional, Tuple
from threading import Lock

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class CrossEncoderModel:
    """Wrapper for Cross-Encoder model with lazy loading and caching."""
    
    _instance: Optional["CrossEncoderModel"] = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """Initialize the Cross-Encoder model.
        
        Args:
            model_name: HuggingFace model name or local path
            cache_dir: Directory to cache model downloads
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto)
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._device = device or self._get_default_device()
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._load_error: Optional[str] = None
        self._load_time: Optional[float] = None
        self._initialized = True
        
        logger.info(f"CrossEncoderModel initialized with model: {model_name}, device: {self._device}")
    
    def _get_default_device(self) -> str:
        """Determine the best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
    
    def load(self) -> bool:
        """Load the model and tokenizer.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if self._loaded:
            return True
            
        start_time = time.time()
        
        try:
            # Import inside method to avoid import errors if dependencies missing
            from sentence_transformers import CrossEncoder
            import torch
            
            logger.info(f"Loading Cross-Encoder model: {self._model_name} on {self._device}")
            
            # Load model with device placement
            self._model = CrossEncoder(
                self._model_name,
                cache_folder=self._cache_dir,
                device=self._device,
                max_length=512,  # Default max length
            )
            
            # Verify model is on correct device
            if hasattr(self._model, 'model') and hasattr(self._model.model, 'device'):
                actual_device = str(self._model.model.device)
                logger.info(f"Model loaded on device: {actual_device}")
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._load_error = None
            
            logger.info(f"Cross-Encoder model loaded successfully in {self._load_time:.2f}s")
            return True
            
        except ImportError as e:
            self._load_error = f"Required dependencies not installed: {e}"
            logger.error(f"Failed to load Cross-Encoder model: {self._load_error}")
            return False
            
        except Exception as e:
            self._load_error = f"Failed to load model: {type(e).__name__}: {str(e)}"
            logger.error(f"Failed to load Cross-Encoder model: {self._load_error}", exc_info=True)
            return False
    
    def predict(self, pairs: List[Tuple[str, str]], batch_size: int = 16) -> List[float]:
        """Predict relevance scores for query-document pairs.
        
        Args:
            pairs: List of (query, document) tuples
            batch_size: Batch size for inference
            
        Returns:
            List of relevance scores (0-1)
            
        Raises:
            ModelNotLoadedError: If model is not loaded
            RerankingError: If prediction fails
        """
        if not self._loaded:
            if not self.load():
                from app.services.reranker.exceptions import ModelNotLoadedError
                raise ModelNotLoadedError(f"Model failed to load: {self._load_error}")
        
        if not pairs:
            return []
        
        try:
            start_time = time.time()
            
            # Run inference
            scores = self._model.predict(
                pairs,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                apply_softmax=True,  # Apply softmax to get probabilities
            )
            
            inference_time = time.time() - start_time
            logger.debug(f"Cross-Encoder inference: {len(pairs)} pairs in {inference_time*1000:.1f}ms")
            
            # Ensure scores are in [0, 1] range
            scores = [max(0.0, min(1.0, float(score))) for score in scores]
            
            return scores
            
        except Exception as e:
            from app.services.reranker.exceptions import RerankingError
            logger.error(f"Cross-Encoder prediction failed: {e}", exc_info=True)
            raise RerankingError(f"Prediction failed: {type(e).__name__}: {str(e)}")
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "model_name": self._model_name,
            "device": self._device,
            "loaded": self._loaded,
            "load_time_seconds": self._load_time,
            "load_error": self._load_error,
        }
    
    def unload(self) -> None:
        """Unload the model to free memory."""
        if self._model is not None:
            import torch
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            self._loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Cross-Encoder model unloaded")


# Convenience function to get singleton instance
def get_cross_encoder_model(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    cache_dir: Optional[str] = None,
    device: Optional[str] = None,
) -> CrossEncoderModel:
    """Get or create the singleton CrossEncoderModel instance."""
    return CrossEncoderModel(model_name=model_name, cache_dir=cache_dir, device=device)