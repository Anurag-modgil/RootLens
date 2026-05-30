import logging
from typing import List
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("rootlens.embeddings")

class LogEmbeddingService:
    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LogEmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        # Ensure model is initialized only once
        if self._model is None:
            self.model_name = model_name
            # Auto-detect the best available execution device
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
            
            logger.info(f"Initializing embedding model '{self.model_name}' on device '{self.device}'...")
            try:
                self._model = SentenceTransformer(self.model_name, device=self.device)
                logger.info(f"Model '{self.model_name}' initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model '{self.model_name}': {str(e)}")
                raise RuntimeError(f"Embedding service initialization failure: {str(e)}")

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single log message.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string.")
        
        try:
            vector = self._model.encode(text, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {str(e)}")
            raise RuntimeError(f"Embedding generation failed: {str(e)}")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for a list of log messages in a batch.
        """
        if not isinstance(texts, list):
            raise ValueError("Input texts must be a list of strings.")
        if not texts:
            return []

        # Validate that all elements are strings
        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError(f"All elements in the batch must be strings. Found type '{type(text)}' at index {i}.")

        try:
            vectors = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return vectors.tolist()
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise RuntimeError(f"Batch embedding generation failed: {str(e)}")
