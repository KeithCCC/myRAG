"""Debug script for FTS search."""
from src.core.database import Database
from src.indexing.ingestion import Ingestion
from src.indexing.extractor import Extractor
from src.indexing.chunker import Chunker
from src.core.models import Chunk, DocumentStatus

# Setup
db = Database("data/test_debug.db")
ing = Ingestion(db)
ext = Extractor()
ch = Chunker(chunk_size=100, chunk_overlap=20)

# Add files
ing.scan_and_add('tests/test_data', False)
docs = ing.get_pending_documents()

if docs:
    d = docs[0]
    print(f"Processing: {d.title}")
    
    # Extract and chunk
    ex = ext.extract(d.path)
    pages = [(p.page_number, p.text) for p in ex.pages]
    chunks = ch.chunk_pages(pages)
    
    print(f"Chunks created: {len(chunks)}")
    print(f"First chunk text: {chunks[0].text[:100]}")
    
    # Add first chunk
    c = Chunk(None, d.id, chunks[0].page_number, chunks[0].start_offset, 
              chunks[0].end_offset, chunks[0].text, chunks[0].text_hash)
    db.add_chunk(c)
    print("Chunk added to database")
    
    # Try to search
    results = db.search_chunks_fts('test')
    print(f"Search 'test': {len(results)} results")
    
    # Check what's in database
    all_chunks = db.get_chunks_by_document(d.id)
    print(f"Total chunks for doc: {len(all_chunks)}")
    
    if all_chunks:
        print(f"Chunk text: {all_chunks[0].text[:100]}")
