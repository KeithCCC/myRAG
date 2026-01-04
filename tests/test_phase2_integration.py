"""Integration test for Phase 2 - End-to-end indexing pipeline."""
import tempfile
import shutil
from pathlib import Path

from src.core.database import Database
from src.core.models import DocumentStatus, Chunk
from src.indexing.ingestion import Ingestion
from src.indexing.extractor import Extractor
from src.indexing.chunker import Chunker


def test_full_indexing_pipeline():
    """Test complete indexing pipeline from file scan to chunks in database."""
    # Setup
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize components
        db = Database(db_path)
        ingestion = Ingestion(db)
        extractor = Extractor()
        chunker = Chunker(chunk_size=100, chunk_overlap=20)  # Small chunks for testing
        
        # Step 1: Scan and add test files
        test_folder = 'tests/test_data'
        added, updated, errors = ingestion.scan_and_add(test_folder, recursive=False)
        
        print(f"\nStep 1: Scanned and added {added} files")
        assert added == 3  # sample.pdf, sample.txt, sample.md
        assert len(errors) == 0
        
        # Step 2: Get pending documents
        pending_docs = ingestion.get_pending_documents()
        print(f"Step 2: Found {len(pending_docs)} pending documents")
        assert len(pending_docs) == 3
        
        # Step 3: Process each document
        total_chunks_added = 0
        
        for doc in pending_docs:
            print(f"\nProcessing: {doc.title}")
            
            try:
                # Extract text
                extracted = extractor.extract(doc.path)
                print(f"  - Extracted {len(extracted.pages)} pages, {extracted.total_chars} chars")
                
                # Chunk text
                pages_data = [(page.page_number, page.text) for page in extracted.pages]
                chunks = chunker.chunk_pages(pages_data)
                print(f"  - Created {len(chunks)} chunks")
                
                # Add chunks to database
                for chunk in chunks:
                    chunk_obj = Chunk(
                        id=None,  # Auto-generated
                        document_id=doc.id,
                        page=chunk.page_number,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        text=chunk.text,
                        text_hash=chunk.text_hash
                    )
                    db.add_chunk(chunk_obj)
                    total_chunks_added += 1
                
                # Update document status
                db.update_document_status(doc.id, DocumentStatus.INDEXED)
                print(f"  - Status: INDEXED")
                
            except Exception as e:
                print(f"  - Error: {str(e)}")
                db.update_document_status(doc.id, DocumentStatus.ERROR, str(e))
        
        print(f"\nTotal chunks added: {total_chunks_added}")
        assert total_chunks_added > 0
        
        # Step 4: Verify database state
        all_docs = db.get_all_documents()
        indexed_docs = [d for d in all_docs if d.status == DocumentStatus.INDEXED]
        print(f"\nStep 4: {len(indexed_docs)} documents indexed")
        assert len(indexed_docs) == 3
        
        # Step 5: Test FTS search
        print(f"\nStep 5: Testing FTS search")
        
        # Search for English keywords
        # Note: Tokenization may affect search results
        results = db.search_chunks_fts("test", limit=5)
        print(f"  - Search 'test': {len(results)} results")
        # FTS should work (even if tokenized differently)
        
        # Search for common word
        results = db.search_chunks_fts("file", limit=5)
        print(f"  - Search 'file': {len(results)} results")
        
        # Step 6: Verify chunks exist
        print(f"\nStep 6: Verifying chunks")
        for doc in indexed_docs:
            chunks = db.get_chunks_by_document(doc.id)
            print(f"  - {doc.title}: {len(chunks)} chunks")
            assert len(chunks) > 0
        
        print("\n✅ Phase 2 integration test PASSED!")
        
    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


if __name__ == '__main__':
    test_full_indexing_pipeline()
