"""Tests for the Retriever module."""

import pytest
import numpy as np
from datetime import datetime
from pathlib import Path
import tempfile

from src.search.retriever import Retriever, SearchResult
from src.core.database import Database
from src.core.models import Document, Chunk
from src.indexing.embedder import Embedder
from src.indexing.index_store import FAISSIndexStore


@pytest.fixture
def test_db():
    """Create a test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    db.close()
    db_path.unlink()


@pytest.fixture
def sample_documents(test_db):
    """Create sample documents."""
    docs = []
    for i in range(3):
        doc = Document(
            id=f"doc_{i}",
            path=f"/test/doc_{i}.txt",
            name=f"doc_{i}.txt",
            status="indexed",
            size=1000,
            modified=datetime.now(),
            indexed_at=datetime.now()
        )
        test_db.add_document(doc)
        docs.append(doc)
    
    return docs


@pytest.fixture
def sample_chunks(test_db, sample_documents):
    """Create sample chunks."""
    chunks = []
    texts = [
        "Machine learning is a subset of artificial intelligence",
        "Deep learning uses neural networks",
        "Python is a popular programming language",
        "Natural language processing handles text",
        "Computer vision processes images",
        "The weather is sunny today"
    ]
    
    for i, text in enumerate(texts):
        doc_id = sample_documents[i % 3].id
        chunk = Chunk(
            id=f"chunk_{i}",
            document_id=doc_id,
            text=text,
            tokenized_text=text.lower(),
            char_count=len(text),
            position=i,
            page_number=1,
            start_offset=0,
            end_offset=len(text)
        )
        test_db.add_chunk(chunk)
        chunks.append(chunk)
    
    return chunks


@pytest.fixture
def embedder():
    """Create embedder instance."""
    return Embedder(model_name='all-MiniLM-L6-v2')


@pytest.fixture
def index_store(embedder):
    """Create FAISS index store."""
    return FAISSIndexStore(dimension=embedder.dimension, index_type='Flat')


@pytest.fixture
def indexed_store(index_store, embedder, sample_chunks):
    """Create index store with sample data."""
    # Generate embeddings
    texts = [chunk.text for chunk in sample_chunks]
    embeddings = embedder.embed_batch(texts)
    
    # Add to index
    chunk_ids = [chunk.id for chunk in sample_chunks]
    index_store.add(chunk_ids, embeddings)
    
    return index_store


@pytest.fixture
def retriever(test_db, embedder, indexed_store):
    """Create retriever instance."""
    return Retriever(db=test_db, embedder=embedder, index_store=indexed_store)


class TestRetriever:
    """Test retrieval functionality."""
    
    def test_initialization(self, test_db):
        """Test retriever initializes correctly."""
        retriever = Retriever(db=test_db)
        assert retriever.db == test_db
        assert retriever.embedder is None
        assert retriever.index_store is None
    
    def test_keyword_search(self, retriever):
        """Test keyword search."""
        results = retriever.keyword_search("machine learning", limit=5)
        
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].chunk.text is not None
        assert results[0].score >= 0
    
    def test_keyword_search_empty_query(self, retriever):
        """Test keyword search with empty query."""
        results = retriever.keyword_search("", limit=5)
        assert len(results) == 0
    
    def test_keyword_search_no_results(self, retriever):
        """Test keyword search with no matches."""
        results = retriever.keyword_search("quantum teleportation xyz", limit=5)
        assert len(results) == 0
    
    def test_semantic_search(self, retriever):
        """Test semantic search."""
        results = retriever.semantic_search("AI and ML", limit=5)
        
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        # Should find ML-related content
        assert any("learning" in r.chunk.text.lower() for r in results)
    
    def test_semantic_search_empty_query(self, retriever):
        """Test semantic search with empty query."""
        results = retriever.semantic_search("", limit=5)
        assert len(results) == 0
    
    def test_semantic_search_without_embedder(self, test_db):
        """Test semantic search fails without embedder."""
        retriever = Retriever(db=test_db)
        
        with pytest.raises(ValueError, match="Embedder is required"):
            retriever.semantic_search("test query")
    
    def test_semantic_search_empty_index(self, test_db, embedder):
        """Test semantic search with empty index."""
        empty_store = FAISSIndexStore(dimension=384, index_type='Flat')
        retriever = Retriever(db=test_db, embedder=embedder, index_store=empty_store)
        
        results = retriever.semantic_search("test query")
        assert len(results) == 0
    
    def test_hybrid_search(self, retriever):
        """Test hybrid search."""
        results = retriever.hybrid_search("machine learning", limit=5)
        
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].score >= 0
    
    def test_hybrid_search_empty_query(self, retriever):
        """Test hybrid search with empty query."""
        results = retriever.hybrid_search("", limit=5)
        assert len(results) == 0
    
    def test_hybrid_search_weights(self, retriever):
        """Test hybrid search with different weights."""
        # Keyword-heavy
        results_kw = retriever.hybrid_search(
            "learning",
            limit=5,
            keyword_weight=0.9,
            semantic_weight=0.1
        )
        
        # Semantic-heavy
        results_sem = retriever.hybrid_search(
            "learning",
            limit=5,
            keyword_weight=0.1,
            semantic_weight=0.9
        )
        
        assert len(results_kw) > 0
        assert len(results_sem) > 0
        # Results may differ based on weights
    
    def test_unified_search_interface(self, retriever):
        """Test unified search interface."""
        # Keyword mode
        kw_results = retriever.search("learning", mode='keyword', limit=5)
        assert len(kw_results) > 0
        
        # Semantic mode
        sem_results = retriever.search("learning", mode='semantic', limit=5)
        assert len(sem_results) > 0
        
        # Hybrid mode
        hyb_results = retriever.search("learning", mode='hybrid', limit=5)
        assert len(hyb_results) > 0
    
    def test_search_invalid_mode(self, retriever):
        """Test search with invalid mode."""
        with pytest.raises(ValueError, match="Unknown search mode"):
            retriever.search("test", mode='invalid')
    
    def test_normalize_scores(self, retriever):
        """Test score normalization."""
        scores = [10.0, 20.0, 30.0, 40.0, 50.0]
        normalized = retriever._normalize_scores(scores)
        
        assert len(normalized) == 5
        assert min(normalized) == 0.0
        assert max(normalized) == 1.0
        assert all(0 <= s <= 1 for s in normalized)
    
    def test_normalize_scores_single(self, retriever):
        """Test score normalization with single score."""
        normalized = retriever._normalize_scores([5.0])
        assert normalized == [1.0]
    
    def test_normalize_scores_empty(self, retriever):
        """Test score normalization with empty list."""
        normalized = retriever._normalize_scores([])
        assert normalized == []
    
    def test_normalize_scores_equal(self, retriever):
        """Test score normalization with equal scores."""
        scores = [10.0, 10.0, 10.0]
        normalized = retriever._normalize_scores(scores)
        assert all(s == 1.0 for s in normalized)
    
    def test_get_chunk_context(self, retriever, sample_chunks):
        """Test getting chunk context."""
        # Get context for middle chunk
        chunk = sample_chunks[2]
        context = retriever.get_chunk_context(chunk, context_before=1, context_after=1)
        
        assert len(context) == 3
        assert context[1].id == chunk.id
    
    def test_get_chunk_context_first_chunk(self, retriever, sample_chunks):
        """Test getting context for first chunk."""
        chunk = sample_chunks[0]
        context = retriever.get_chunk_context(chunk, context_before=2, context_after=1)
        
        # Should start from beginning
        assert context[0].id == chunk.id
    
    def test_get_chunk_context_last_chunk(self, retriever, sample_chunks):
        """Test getting context for last chunk."""
        # Get the last chunk from doc_0
        doc_0_chunks = [c for c in sample_chunks if c.document_id == "doc_0"]
        chunk = doc_0_chunks[-1]
        
        context = retriever.get_chunk_context(chunk, context_before=1, context_after=2)
        
        # Should end at last chunk
        assert context[-1].id == chunk.id
    
    def test_format_result_snippet(self, retriever, sample_chunks):
        """Test formatting result snippet."""
        chunk = sample_chunks[0]
        snippet = retriever.format_result_snippet(chunk, "machine learning", snippet_length=50)
        
        assert isinstance(snippet, str)
        assert len(snippet) <= 53  # 50 + potential "..."
        assert "machine learning" in snippet.lower()
    
    def test_format_result_snippet_short_text(self, retriever, sample_chunks):
        """Test formatting snippet for short text."""
        chunk = sample_chunks[0]
        snippet = retriever.format_result_snippet(chunk, "test", snippet_length=200)
        
        # Should return full text since it's short
        assert snippet == chunk.text
        assert "..." not in snippet
    
    def test_format_result_snippet_long_text(self, retriever, test_db, sample_documents):
        """Test formatting snippet for long text."""
        long_text = "Lorem ipsum " * 100
        chunk = Chunk(
            id="long_chunk",
            document_id=sample_documents[0].id,
            text=long_text,
            tokenized_text=long_text.lower(),
            char_count=len(long_text),
            position=0,
            page_number=1,
            start_offset=0,
            end_offset=len(long_text)
        )
        test_db.add_chunk(chunk)
        
        snippet = retriever.format_result_snippet(chunk, "ipsum", snippet_length=50)
        
        assert len(snippet) <= 53
        assert "..." in snippet
    
    def test_search_result_dataclass(self, sample_chunks):
        """Test SearchResult dataclass."""
        result = SearchResult(
            chunk=sample_chunks[0],
            score=0.95,
            rank=1
        )
        
        assert result.chunk == sample_chunks[0]
        assert result.score == 0.95
        assert result.rank == 1
    
    def test_keyword_search_ranking(self, retriever):
        """Test that keyword search returns ranked results."""
        results = retriever.keyword_search("learning machine", limit=10)
        
        if len(results) > 1:
            # Check ranks are sequential
            assert all(results[i].rank == i + 1 for i in range(len(results)))
            # Scores should be non-increasing (higher score = better)
            scores = [r.score for r in results]
            # Since FTS5 returns negative ranks, we use abs
            assert all(scores[i] >= scores[i+1] or abs(scores[i] - scores[i+1]) < 0.01 
                      for i in range(len(scores)-1))
    
    def test_semantic_search_ranking(self, retriever):
        """Test that semantic search returns ranked results."""
        results = retriever.semantic_search("artificial intelligence", limit=5)
        
        if len(results) > 1:
            # Check ranks are sequential
            assert all(results[i].rank == i + 1 for i in range(len(results)))
            # Scores should be non-increasing
            scores = [r.score for r in results]
            assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    def test_hybrid_search_combines_results(self, retriever):
        """Test that hybrid search combines keyword and semantic results."""
        keyword_results = retriever.keyword_search("learning", limit=5)
        semantic_results = retriever.semantic_search("learning", limit=5)
        hybrid_results = retriever.hybrid_search("learning", limit=10)
        
        # Hybrid should potentially include results from both
        assert len(hybrid_results) > 0
        
        # All results should be unique
        chunk_ids = [r.chunk.id for r in hybrid_results]
        assert len(chunk_ids) == len(set(chunk_ids))
