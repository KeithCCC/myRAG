"""Text embedding generation using sentence-transformers."""

from typing import List, Optional, Callable
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path


class Embedder:
    """Generate text embeddings using sentence-transformers.
    
    Supports batch processing with progress tracking.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: Optional[Path] = None):
        """Initialize embedder with specified model.
        
        Args:
            model_name: Name of sentence-transformers model
            cache_dir: Optional directory for model cache
        """
        self.model_name = model_name
        self.cache_dir = str(cache_dir) if cache_dir else None
        self._model: Optional[SentenceTransformer] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, cache_folder=self.cache_dir)
        return self._model
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> np.ndarray:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once
            show_progress: Whether to show progress bar
            progress_callback: Optional callback function(current, total)
            
        Returns:
            2D numpy array of embeddings (num_texts x dimension)
        """
        if not texts:
            return np.array([])
        
        # Wrap progress callback if provided
        if progress_callback:
            def _callback(current, total):
                progress_callback(current, total)
        else:
            _callback = None
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        # Call progress callback at the end
        if progress_callback:
            progress_callback(len(texts), len(texts))
        
        return embeddings
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
    
    def similarity_batch(self, query_embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between query and multiple embeddings.
        
        Args:
            query_embedding: Query embedding vector (1D)
            embeddings: Multiple embedding vectors (2D array)
            
        Returns:
            Array of similarity scores
        """
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        embeddings_norm = embeddings / norms
        
        # Compute similarities
        similarities = np.dot(embeddings_norm, query_norm)
        
        return similarities
