"""Tests for the FAISS Index Store module."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.indexing.index_store import FAISSIndexStore


class TestFAISSIndexStore:
    """Test FAISS index management."""
    
    @pytest.fixture
    def dimension(self):
        """Embedding dimension for testing."""
        return 384
    
    @pytest.fixture
    def index_store(self, dimension):
        """Create index store instance."""
        return FAISSIndexStore(dimension=dimension, index_type='Flat')
    
    @pytest.fixture
    def sample_embeddings(self, dimension):
        """Create sample embeddings."""
        return np.random.rand(10, dimension).astype('float32')
    
    @pytest.fixture
    def sample_chunk_ids(self):
        """Create sample chunk IDs."""
        return [f"chunk_{i}" for i in range(10)]
    
    def test_initialization(self, index_store):
        """Test index store initializes correctly."""
        assert index_store.dimension == 384
        assert index_store.index_type == 'Flat'
        assert index_store.index is None
        assert len(index_store.chunk_id_map) == 0
    
    def test_create_flat_index(self, index_store):
        """Test creating a Flat index."""
        index_store.create_index()
        assert index_store.index is not None
        assert index_store.index.ntotal == 0
    
    def test_create_hnsw_index(self, dimension):
        """Test creating an HNSW index."""
        store = FAISSIndexStore(dimension=dimension, index_type='HNSW')
        store.create_index()
        assert store.index is not None
    
    def test_create_invalid_index_type(self, dimension):
        """Test creating index with invalid type."""
        store = FAISSIndexStore(dimension=dimension, index_type='InvalidType')
        with pytest.raises(ValueError, match="Unknown index type"):
            store.create_index()
    
    def test_add_vectors(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test adding vectors to index."""
        index_store.add(sample_chunk_ids, sample_embeddings)
        
        assert index_store.size == 10
        assert len(index_store.chunk_id_map) == 10
        assert len(index_store.reverse_map) == 10
    
    def test_add_single_vector(self, index_store):
        """Test adding a single vector."""
        chunk_id = "chunk_0"
        embedding = np.random.rand(384).astype('float32')
        
        index_store.add([chunk_id], embedding.reshape(1, -1))
        
        assert index_store.size == 1
        assert chunk_id in index_store.reverse_map
    
    def test_add_empty_list(self, index_store):
        """Test adding empty list of vectors."""
        index_store.add([], np.array([]))
        assert index_store.size == 0
    
    def test_add_multiple_batches(self, index_store, dimension):
        """Test adding vectors in multiple batches."""
        # First batch
        ids1 = ["chunk_0", "chunk_1", "chunk_2"]
        emb1 = np.random.rand(3, dimension).astype('float32')
        index_store.add(ids1, emb1)
        
        # Second batch
        ids2 = ["chunk_3", "chunk_4"]
        emb2 = np.random.rand(2, dimension).astype('float32')
        index_store.add(ids2, emb2)
        
        assert index_store.size == 5
        assert all(cid in index_store.reverse_map for cid in ids1 + ids2)
    
    def test_search(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test searching for similar vectors."""
        index_store.add(sample_chunk_ids, sample_embeddings)
        
        # Search with first embedding
        query = sample_embeddings[0]
        results = index_store.search(query, k=5)
        
        assert len(results) == 5
        assert all(isinstance(r, tuple) for r in results)
        assert all(len(r) == 2 for r in results)
        
        # First result should be the query itself
        assert results[0][0] == "chunk_0"
        assert results[0][1] >= 0.95  # High similarity to itself
    
    def test_search_empty_index(self, index_store):
        """Test searching in empty index."""
        query = np.random.rand(384).astype('float32')
        results = index_store.search(query, k=10)
        
        assert len(results) == 0
    
    def test_search_k_larger_than_index(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test searching with k larger than index size."""
        # Add only 3 vectors
        index_store.add(sample_chunk_ids[:3], sample_embeddings[:3])
        
        query = sample_embeddings[0]
        results = index_store.search(query, k=10)
        
        # Should return only 3 results
        assert len(results) == 3
    
    def test_has_chunk(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test checking if chunk exists in index."""
        index_store.add(sample_chunk_ids, sample_embeddings)
        
        assert index_store.has_chunk("chunk_0")
        assert index_store.has_chunk("chunk_5")
        assert not index_store.has_chunk("nonexistent")
    
    def test_save_and_load(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test saving and loading index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            map_path = Path(tmpdir) / "test.map"
            
            # Add vectors and save
            index_store.add(sample_chunk_ids, sample_embeddings)
            index_store.save(index_path, map_path)
            
            assert index_path.exists()
            assert map_path.exists()
            
            # Load into new instance
            new_store = FAISSIndexStore(dimension=384, index_type='Flat')
            new_store.load(index_path, map_path)
            
            assert new_store.size == 10
            assert len(new_store.chunk_id_map) == 10
            assert new_store.dimension == 384
            
            # Search should work
            query = sample_embeddings[0]
            results = new_store.search(query, k=5)
            assert len(results) == 5
            assert results[0][0] == "chunk_0"
    
    def test_load_nonexistent_index(self, index_store):
        """Test loading nonexistent index files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "nonexistent.index"
            map_path = Path(tmpdir) / "nonexistent.map"
            
            # Should create empty index
            index_store.load(index_path, map_path)
            assert index_store.size == 0
            assert index_store.index is not None
    
    def test_clear(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test clearing the index."""
        index_store.add(sample_chunk_ids, sample_embeddings)
        assert index_store.size == 10
        
        index_store.clear()
        
        assert index_store.index is None
        assert index_store.size == 0
        assert len(index_store.chunk_id_map) == 0
        assert len(index_store.reverse_map) == 0
    
    def test_remove_vectors(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test removing vectors from index."""
        index_store.add(sample_chunk_ids, sample_embeddings)
        
        # Remove some chunks
        to_remove = ["chunk_0", "chunk_5", "chunk_9"]
        index_store.remove(to_remove)
        
        assert index_store.size == 7
        assert not index_store.has_chunk("chunk_0")
        assert not index_store.has_chunk("chunk_5")
        assert index_store.has_chunk("chunk_1")
        assert index_store.has_chunk("chunk_2")
    
    def test_remove_nonexistent(self, index_store, sample_chunk_ids, sample_embeddings):
        """Test removing nonexistent chunks."""
        index_store.add(sample_chunk_ids, sample_embeddings)
        
        initial_size = index_store.size
        index_store.remove(["nonexistent_1", "nonexistent_2"])
        
        # Size should remain the same
        assert index_store.size == initial_size
    
    def test_size_property(self, index_store):
        """Test size property."""
        assert index_store.size == 0
        
        # Add some vectors
        ids = ["chunk_0", "chunk_1", "chunk_2"]
        emb = np.random.rand(3, 384).astype('float32')
        index_store.add(ids, emb)
        
        assert index_store.size == 3
    
    def test_normalization(self, index_store):
        """Test that vectors are normalized for cosine similarity."""
        # Create unnormalized vectors
        chunk_ids = ["chunk_0", "chunk_1"]
        embeddings = np.array([
            [1.0, 2.0, 3.0] + [0.0] * 381,
            [4.0, 5.0, 6.0] + [0.0] * 381
        ], dtype='float32')
        
        index_store.add(chunk_ids, embeddings)
        
        # Search should work with normalized vectors
        query = embeddings[0]
        results = index_store.search(query, k=2)
        
        assert len(results) == 2
        # Score should be close to 1 for the same vector
        assert results[0][1] >= 0.95
    
    def test_search_returns_sorted_results(self, index_store):
        """Test that search results are sorted by score."""
        # Create vectors with known similarities
        chunk_ids = ["chunk_0", "chunk_1", "chunk_2"]
        embeddings = np.array([
            [1.0, 0.0, 0.0] + [0.0] * 381,
            [0.9, 0.1, 0.0] + [0.0] * 381,  # Similar to first
            [0.0, 1.0, 0.0] + [0.0] * 381   # Different from first
        ], dtype='float32')
        
        index_store.add(chunk_ids, embeddings)
        
        query = embeddings[0]
        results = index_store.search(query, k=3)
        
        # Results should be sorted by score (descending)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
        
        # First two should be chunk_0 and chunk_1
        assert results[0][0] == "chunk_0"
        assert results[1][0] == "chunk_1"
