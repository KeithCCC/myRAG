"""Integration test for Phase 3 search functionality."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.database import Database
from src.indexing.embedder import Embedder
from src.indexing.index_store import FAISSIndexStore
from src.search.retriever import Retriever

def main():
    print("=== Phase 3 Integration Test ===\n")
    
    # Use existing database
    db_path = project_root / "data" / "folderrag.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Please run some indexing first (Phase 2)")
        return 1
    
    print(f"✓ Using database: {db_path}")
    db = Database(db_path)
    
    # Check if we have chunks
    chunk_count = db.get_chunk_count()
    print(f"✓ Found {chunk_count} chunks in database")
    
    if chunk_count == 0:
        print("❌ No chunks found. Please index some documents first.")
        return 1
    
    print("\n--- Testing Keyword Search ---")
    try:
        # Test keyword search
        results = db.search_chunks_fts("machine", limit=5)
        print(f"✓ Keyword search returned {len(results)} results")
        if results:
            print(f"  Top result: chunk_id={results[0][0]}, score={results[0][1]:.2f}")
    except Exception as e:
        print(f"❌ Keyword search failed: {e}")
        return 1
    
    print("\n--- Testing Embedder ---")
    try:
        embedder = Embedder(model_name='all-MiniLM-L6-v2')
        print(f"✓ Embedder initialized")
        print(f"✓ Embedding dimension: {embedder.dimension}")
        
        # Test embedding generation
        test_text = "This is a test sentence for embedding."
        embedding = embedder.embed(test_text)
        print(f"✓ Generated embedding: shape={embedding.shape}")
        
        # Test batch embedding
        texts = ["First text", "Second text", "Third text"]
        embeddings = embedder.embed_batch(texts)
        print(f"✓ Batch embedding: shape={embeddings.shape}")
        
    except Exception as e:
        print(f"❌ Embedder failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n--- Testing FAISS Index Store ---")
    try:
        index_store = FAISSIndexStore(dimension=embedder.dimension, index_type='Flat')
        print(f"✓ FAISS index store initialized")
        
        # Create sample index
        chunk_ids = ["chunk_0", "chunk_1", "chunk_2"]
        test_embeddings = embedder.embed_batch(["Test one", "Test two", "Test three"])
        index_store.add(chunk_ids, test_embeddings)
        print(f"✓ Added 3 vectors to index")
        print(f"✓ Index size: {index_store.size}")
        
        # Test search
        query_emb = embedder.embed("Test one")
        search_results = index_store.search(query_emb, k=2)
        print(f"✓ FAISS search returned {len(search_results)} results")
        if search_results:
            print(f"  Top result: chunk_id={search_results[0][0]}, score={search_results[0][1]:.3f}")
        
    except Exception as e:
        print(f"❌ FAISS Index Store failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n--- Testing Retriever (with sample data) ---")
    try:
        # For this test, we'll use a small test index
        retriever = Retriever(db=db, embedder=embedder, index_store=index_store)
        print(f"✓ Retriever initialized")
        
        # Test keyword search
        print("\n  Testing keyword search...")
        kw_results = retriever.keyword_search("test", limit=3)
        print(f"  ✓ Keyword search: {len(kw_results)} results")
        
        # Note: Semantic search won't work well with our tiny test index
        # In real usage, you'd need to index all chunks first
        
    except Exception as e:
        print(f"❌ Retriever failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n=== Phase 3 Components Working! ===")
    print("\nNext steps:")
    print("1. To use semantic search, run a full embedding pipeline:")
    print("   - Get all chunks from database")
    print("   - Generate embeddings for all")
    print("   - Build FAISS index")
    print("   - Save index to disk")
    print("2. Then you can test hybrid search combining keyword + semantic")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
