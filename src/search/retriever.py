"""Search retrieval with keyword, semantic, and hybrid modes."""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import numpy as np
import logging

from ..core.database import Database
from ..core.models import Chunk
from ..indexing.embedder import Embedder
from ..indexing.index_store import FAISSIndexStore

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with chunk and score."""
    chunk: Chunk
    score: float
    rank: int


class Retriever:
    """Retrieve relevant chunks using keyword, semantic, or hybrid search."""
    
    def __init__(
        self,
        db: Database,
        embedder: Optional[Embedder] = None,
        index_store: Optional[FAISSIndexStore] = None
    ):
        """Initialize retriever.
        
        Args:
            db: Database manager
            embedder: Text embedder (required for semantic/hybrid search)
            index_store: FAISS index store (required for semantic/hybrid search)
        """
        self.db = db
        self.embedder = embedder
        self.index_store = index_store
    
    def keyword_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using FTS5 keyword matching.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results sorted by relevance
        """
        if not query.strip():
            return []
        
        # Search using FTS5
        results = self.db.search_chunks_fts(query, limit=limit)
        
        # Get chunks and create results
        search_results = []
        for rank, (chunk_id, score) in enumerate(results, 1):
            chunk = self.db.get_chunk(chunk_id)
            if chunk:
                search_results.append(SearchResult(
                    chunk=chunk,
                    score=abs(score),  # FTS5 ranks are negative
                    rank=rank
                ))
        
        return search_results
    
    def semantic_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results sorted by similarity
        """
        if not query.strip():
            return []
        
        if self.embedder is None:
            raise ValueError("Embedder is required for semantic search")
        
        if self.index_store is None or self.index_store.size == 0:
            logger.warning("FAISS index is empty")
            return []
        
        # Generate query embedding
        query_embedding = self.embedder.embed(query)
        
        # Search FAISS index
        results = self.index_store.search(query_embedding, k=limit)
        
        # Get chunks and create results
        search_results = []
        for rank, (chunk_id, score) in enumerate(results, 1):
            chunk = self.db.get_chunk(chunk_id)
            if chunk:
                search_results.append(SearchResult(
                    chunk=chunk,
                    score=score,
                    rank=rank
                ))
        
        return search_results
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        keyword_limit: int = 20,
        semantic_limit: int = 20,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5
    ) -> List[SearchResult]:
        """Search using hybrid keyword + semantic approach.
        
        Combines results from both keyword and semantic search with score normalization.
        
        Args:
            query: Search query
            limit: Maximum number of final results
            keyword_limit: Number of results to fetch from keyword search
            semantic_limit: Number of results to fetch from semantic search
            keyword_weight: Weight for keyword scores (0-1)
            semantic_weight: Weight for semantic scores (0-1)
            
        Returns:
            List of search results sorted by combined score
        """
        if not query.strip():
            return []
        
        # Get results from both methods
        keyword_results = self.keyword_search(query, limit=keyword_limit)
        semantic_results = self.semantic_search(query, limit=semantic_limit)
        
        if not keyword_results and not semantic_results:
            return []
        
        # Normalize scores using min-max normalization
        keyword_scores = self._normalize_scores([r.score for r in keyword_results])
        semantic_scores = self._normalize_scores([r.score for r in semantic_results])
        
        # Create score maps
        chunk_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}
        
        # Add keyword scores
        for i, result in enumerate(keyword_results):
            chunk_id = result.chunk.id
            chunk_scores[chunk_id] = keyword_weight * keyword_scores[i]
            chunk_map[chunk_id] = result.chunk
        
        # Add semantic scores
        for i, result in enumerate(semantic_results):
            chunk_id = result.chunk.id
            if chunk_id in chunk_scores:
                # Combine scores if chunk appears in both
                chunk_scores[chunk_id] += semantic_weight * semantic_scores[i]
            else:
                chunk_scores[chunk_id] = semantic_weight * semantic_scores[i]
            chunk_map[chunk_id] = result.chunk
        
        # Sort by combined score
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Create final results
        search_results = []
        for rank, (chunk_id, score) in enumerate(sorted_chunks, 1):
            search_results.append(SearchResult(
                chunk=chunk_map[chunk_id],
                score=score,
                rank=rank
            ))
        
        return search_results
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalize scores to 0-1 range using min-max normalization.
        
        Args:
            scores: List of scores
            
        Returns:
            Normalized scores
        """
        if not scores:
            return []
        
        if len(scores) == 1:
            return [1.0]
        
        scores_array = np.array(scores)
        min_score = scores_array.min()
        max_score = scores_array.max()
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        normalized = (scores_array - min_score) / (max_score - min_score)
        return normalized.tolist()
    
    def get_chunk_context(
        self,
        chunk: Chunk,
        context_before: int = 1,
        context_after: int = 1
    ) -> List[Chunk]:
        """Get surrounding chunks for context.
        
        Args:
            chunk: The chunk to get context for
            context_before: Number of chunks before
            context_after: Number of chunks after
            
        Returns:
            List of chunks including the original and context
        """
        # Get all chunks from the same document
        doc_chunks = self.db.get_chunks_by_document(chunk.document_id)
        
        if not doc_chunks:
            return [chunk]
        
        # Find the chunk index
        try:
            chunk_idx = next(i for i, c in enumerate(doc_chunks) if c.id == chunk.id)
        except StopIteration:
            return [chunk]
        
        # Get context range
        start_idx = max(0, chunk_idx - context_before)
        end_idx = min(len(doc_chunks), chunk_idx + context_after + 1)
        
        return doc_chunks[start_idx:end_idx]
    
    def format_result_snippet(
        self,
        chunk: Chunk,
        query: str,
        snippet_length: int = 200
    ) -> str:
        """Format a snippet with query highlighting.
        
        Args:
            chunk: Chunk to format
            query: Search query for highlighting
            snippet_length: Maximum snippet length
            
        Returns:
            Formatted snippet string
        """
        text = chunk.text
        
        if len(text) <= snippet_length:
            snippet = text
        else:
            # Try to find query in text for context
            query_words = query.lower().split()
            best_pos = 0
            
            for word in query_words:
                pos = text.lower().find(word)
                if pos != -1:
                    # Center around the found word
                    start = max(0, pos - snippet_length // 2)
                    best_pos = start
                    break
            
            snippet = text[best_pos:best_pos + snippet_length]
            if best_pos > 0:
                snippet = "..." + snippet
            if best_pos + snippet_length < len(text):
                snippet = snippet + "..."
        
        return snippet
    
    def search(
        self,
        query: str,
        mode: str = 'hybrid',
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Unified search interface.
        
        Args:
            query: Search query
            mode: Search mode ('keyword', 'semantic', 'hybrid')
            limit: Maximum number of results
            **kwargs: Additional arguments for specific modes
            
        Returns:
            List of search results
        """
        mode = mode.lower()
        
        if mode == 'keyword':
            return self.keyword_search(query, limit=limit)
        elif mode == 'semantic':
            return self.semantic_search(query, limit=limit)
        elif mode == 'hybrid':
            return self.hybrid_search(query, limit=limit, **kwargs)
        else:
            raise ValueError(f"Unknown search mode: {mode}")
