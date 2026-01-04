"""Tests for the Embedder module."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.indexing.embedder import Embedder


class TestEmbedder:
    """Test embedding generation."""
    
    @pytest.fixture
    def embedder(self):
        """Create embedder instance."""
        return Embedder(model_name='all-MiniLM-L6-v2')
    
    def test_embedder_initialization(self, embedder):
        """Test embedder initializes correctly."""
        assert embedder.model_name == 'all-MiniLM-L6-v2'
        assert embedder._model is None  # Lazy loading
    
    def test_dimension(self, embedder):
        """Test embedding dimension."""
        dim = embedder.dimension
        assert dim == 384  # all-MiniLM-L6-v2 dimension
        assert embedder._model is not None  # Model loaded
    
    def test_embed_single_text(self, embedder):
        """Test embedding a single text."""
        text = "This is a test sentence."
        embedding = embedder.embed(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert not np.all(embedding == 0)
    
    def test_embed_empty_text(self, embedder):
        """Test embedding empty text."""
        embedding = embedder.embed("")
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_embed_japanese_text(self, embedder):
        """Test embedding Japanese text."""
        text = "これはテストです。"
        embedding = embedder.embed(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert not np.all(embedding == 0)
    
    def test_embed_batch(self, embedder):
        """Test batch embedding."""
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence."
        ]
        
        embeddings = embedder.embed_batch(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
        assert not np.all(embeddings == 0)
    
    def test_embed_batch_empty_list(self, embedder):
        """Test batch embedding with empty list."""
        embeddings = embedder.embed_batch([])
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (0,)
    
    def test_embed_batch_with_progress(self, embedder):
        """Test batch embedding with progress callback."""
        texts = ["Text " + str(i) for i in range(10)]
        progress_calls = []
        
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        embeddings = embedder.embed_batch(
            texts,
            batch_size=5,
            progress_callback=progress_callback
        )
        
        assert embeddings.shape == (10, 384)
        assert len(progress_calls) > 0
        assert progress_calls[-1] == (10, 10)  # Final call
    
    def test_similarity(self, embedder):
        """Test similarity calculation between two embeddings."""
        text1 = "The cat sits on the mat."
        text2 = "A cat is sitting on the mat."
        text3 = "The weather is nice today."
        
        emb1 = embedder.embed(text1)
        emb2 = embedder.embed(text2)
        emb3 = embedder.embed(text3)
        
        # Similar texts should have high similarity
        sim_12 = embedder.similarity(emb1, emb2)
        assert 0.7 < sim_12 <= 1.0
        
        # Different texts should have lower similarity
        sim_13 = embedder.similarity(emb1, emb3)
        assert sim_13 < sim_12
    
    def test_similarity_identical(self, embedder):
        """Test similarity of identical embeddings."""
        text = "Test sentence."
        emb = embedder.embed(text)
        
        sim = embedder.similarity(emb, emb)
        assert 0.99 < sim <= 1.0  # Should be very close to 1
    
    def test_similarity_batch(self, embedder):
        """Test batch similarity calculation."""
        query = "Machine learning algorithms"
        texts = [
            "Deep learning neural networks",
            "Machine learning models",
            "The weather is sunny",
            "Artificial intelligence systems"
        ]
        
        query_emb = embedder.embed(query)
        embeddings = embedder.embed_batch(texts)
        
        similarities = embedder.similarity_batch(query_emb, embeddings)
        
        assert isinstance(similarities, np.ndarray)
        assert similarities.shape == (4,)
        assert all(0 <= s <= 1 for s in similarities)
        
        # ML-related texts should have higher similarity
        assert similarities[1] > similarities[2]  # "Machine learning" vs "weather"
    
    def test_similarity_zero_vector(self, embedder):
        """Test similarity with zero vector."""
        text = "Test sentence."
        emb = embedder.embed(text)
        zero_emb = np.zeros(384)
        
        sim = embedder.similarity(emb, zero_emb)
        assert sim == 0.0
    
    def test_cache_dir(self):
        """Test embedder with custom cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "models"
            embedder = Embedder(cache_dir=cache_path)
            
            # Trigger model loading
            _ = embedder.dimension
            
            # Check cache directory was used (model files should be there)
            assert cache_path.exists()
    
    def test_consistency(self, embedder):
        """Test that same text produces same embedding."""
        text = "Consistency test."
        
        emb1 = embedder.embed(text)
        emb2 = embedder.embed(text)
        
        assert np.allclose(emb1, emb2)
    
    def test_batch_consistency(self, embedder):
        """Test batch and single embeddings are consistent."""
        text = "Test sentence for consistency."
        
        single_emb = embedder.embed(text)
        batch_emb = embedder.embed_batch([text])
        
        assert np.allclose(single_emb, batch_emb[0])
    
    def test_different_texts_different_embeddings(self, embedder):
        """Test that different texts produce different embeddings."""
        text1 = "This is the first sentence."
        text2 = "This is a completely different sentence."
        
        emb1 = embedder.embed(text1)
        emb2 = embedder.embed(text2)
        
        assert not np.allclose(emb1, emb2)
    
    def test_long_text(self, embedder):
        """Test embedding very long text."""
        # Create a long text (sentence-transformers has max length ~512 tokens)
        text = "This is a test. " * 200
        
        embedding = embedder.embed(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert not np.all(embedding == 0)
