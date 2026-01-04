"""FAISS vector index management."""

from typing import List, Optional, Tuple, Dict
import numpy as np
import faiss
from pathlib import Path
import pickle
import logging

logger = logging.getLogger(__name__)


class FAISSIndexStore:
    """Manage FAISS index for vector search.
    
    Handles creating, loading, saving, and searching FAISS indexes
    with mapping between FAISS IDs and chunk IDs.
    """
    
    def __init__(self, dimension: int, index_type: str = 'Flat'):
        """Initialize FAISS index store.
        
        Args:
            dimension: Embedding vector dimension
            index_type: Type of FAISS index ('Flat', 'HNSW', 'IVF')
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index: Optional[faiss.Index] = None
        self.chunk_id_map: Dict[int, str] = {}  # FAISS ID -> chunk ID
        self.reverse_map: Dict[str, int] = {}   # chunk ID -> FAISS ID
        self._next_id = 0
    
    def create_index(self) -> None:
        """Create a new FAISS index."""
        if self.index_type == 'Flat':
            # Flat L2 index (exact search)
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine sim)
        elif self.index_type == 'HNSW':
            # HNSW index (approximate, fast)
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)  # 32 is M parameter
            self.index.hnsw.efConstruction = 40
            self.index.hnsw.efSearch = 16
        elif self.index_type == 'IVF':
            # IVF index (approximate, memory efficient)
            nlist = 100  # Number of clusters
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")
        
        logger.info(f"Created {self.index_type} index with dimension {self.dimension}")
    
    def add(self, chunk_ids: List[str], embeddings: np.ndarray) -> None:
        """Add vectors to the index.
        
        Args:
            chunk_ids: List of chunk IDs
            embeddings: 2D numpy array of embeddings (num_chunks x dimension)
        """
        if self.index is None:
            self.create_index()
        
        if len(chunk_ids) == 0:
            return
        
        # Ensure embeddings are 2D
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Normalize vectors for cosine similarity (with IndexFlatIP)
        if self.index_type == 'Flat' or self.index_type == 'HNSW':
            faiss.normalize_L2(embeddings)
        
        # Train index if needed (IVF requires training)
        if self.index_type == 'IVF' and not self.index.is_trained:
            if len(embeddings) < 100:
                logger.warning(f"Only {len(embeddings)} vectors for training IVF index, recommend at least 100")
            self.index.train(embeddings)
        
        # Add to index
        start_id = self._next_id
        self.index.add(embeddings)
        
        # Update mappings
        for i, chunk_id in enumerate(chunk_ids):
            faiss_id = start_id + i
            self.chunk_id_map[faiss_id] = chunk_id
            self.reverse_map[chunk_id] = faiss_id
        
        self._next_id += len(chunk_ids)
        
        logger.info(f"Added {len(chunk_ids)} vectors to index (total: {self.index.ntotal})")
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """Search for similar vectors.
        
        Args:
            query_embedding: Query vector (1D array)
            k: Number of results to return
            
        Returns:
            List of (chunk_id, score) tuples sorted by relevance
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Reshape to 2D if needed
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Normalize for cosine similarity
        if self.index_type == 'Flat' or self.index_type == 'HNSW':
            faiss.normalize_L2(query_embedding)
        
        # Search
        k = min(k, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, k)
        
        # Convert to chunk IDs
        results = []
        for i in range(len(indices[0])):
            faiss_id = int(indices[0][i])
            score = float(scores[0][i])
            
            if faiss_id in self.chunk_id_map:
                chunk_id = self.chunk_id_map[faiss_id]
                results.append((chunk_id, score))
        
        return results
    
    def remove(self, chunk_ids: List[str]) -> None:
        """Remove vectors from the index.
        
        Note: FAISS doesn't support efficient removal. This rebuilds the index.
        
        Args:
            chunk_ids: List of chunk IDs to remove
        """
        if self.index is None:
            return
        
        # Get all vectors except the ones to remove
        keep_ids = []
        keep_faiss_ids = []
        
        for faiss_id, chunk_id in self.chunk_id_map.items():
            if chunk_id not in chunk_ids:
                keep_ids.append(chunk_id)
                keep_faiss_ids.append(faiss_id)
        
        if len(keep_ids) == len(self.chunk_id_map):
            # Nothing to remove
            return
        
        # Rebuild index (FAISS limitation)
        logger.info(f"Rebuilding index after removing {len(chunk_ids)} vectors")
        
        # Get vectors to keep
        keep_embeddings = []
        for faiss_id in keep_faiss_ids:
            vector = self.index.reconstruct(int(faiss_id))
            keep_embeddings.append(vector)
        
        # Reset and rebuild
        self.create_index()
        self.chunk_id_map.clear()
        self.reverse_map.clear()
        self._next_id = 0
        
        if keep_embeddings:
            embeddings_array = np.array(keep_embeddings)
            self.add(keep_ids, embeddings_array)
    
    def save(self, index_path: Path, map_path: Path) -> None:
        """Save index and mappings to disk.
        
        Args:
            index_path: Path to save FAISS index
            map_path: Path to save ID mappings
        """
        if self.index is None:
            logger.warning("No index to save")
            return
        
        # Save FAISS index
        faiss.write_index(self.index, str(index_path))
        
        # Save mappings
        mappings = {
            'chunk_id_map': self.chunk_id_map,
            'reverse_map': self.reverse_map,
            'next_id': self._next_id,
            'dimension': self.dimension,
            'index_type': self.index_type
        }
        
        with open(map_path, 'wb') as f:
            pickle.dump(mappings, f)
        
        logger.info(f"Saved index ({self.index.ntotal} vectors) to {index_path}")
    
    def load(self, index_path: Path, map_path: Path) -> None:
        """Load index and mappings from disk.
        
        Args:
            index_path: Path to FAISS index file
            map_path: Path to ID mappings file
        """
        if not index_path.exists():
            logger.warning(f"Index file not found: {index_path}")
            self.create_index()
            return
        
        if not map_path.exists():
            logger.warning(f"Mapping file not found: {map_path}")
            self.create_index()
            return
        
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))
        
        # Load mappings
        with open(map_path, 'rb') as f:
            mappings = pickle.load(f)
        
        self.chunk_id_map = mappings['chunk_id_map']
        self.reverse_map = mappings['reverse_map']
        self._next_id = mappings['next_id']
        self.dimension = mappings['dimension']
        self.index_type = mappings['index_type']
        
        logger.info(f"Loaded index ({self.index.ntotal} vectors) from {index_path}")
    
    def clear(self) -> None:
        """Clear the index and all mappings."""
        self.index = None
        self.chunk_id_map.clear()
        self.reverse_map.clear()
        self._next_id = 0
        logger.info("Cleared index")
    
    @property
    def size(self) -> int:
        """Get number of vectors in the index."""
        if self.index is None:
            return 0
        return self.index.ntotal
    
    def has_chunk(self, chunk_id: str) -> bool:
        """Check if a chunk is in the index.
        
        Args:
            chunk_id: Chunk ID to check
            
        Returns:
            True if chunk is in the index
        """
        return chunk_id in self.reverse_map
