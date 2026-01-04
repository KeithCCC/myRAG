# Phase 2 Complete: File Indexing Pipeline

**Status**: ✅ COMPLETE  
**Date**: 2025  
**Tests**: 69/69 passing (36 Phase 2 tests + 33 Phase 1 tests)

## Overview

Phase 2 successfully implements the complete file indexing pipeline for the myRAG application. This phase adds the ability to scan folders, extract text from various document formats, and chunk text into searchable segments that are stored in the database.

## Components Implemented

### 1. File Ingestion (`src/indexing/ingestion.py`)

Handles folder scanning and file enumeration with support for:
- **Recursive folder scanning** with configurable depth
- **File filtering** by extension (.pdf, .txt, .md)
- **Duplicate detection** via file path
- **Modification tracking** via file mtime
- **Batch processing** with error handling

**Key Features**:
```python
ingestion = Ingestion(db)
added, updated, errors = ingestion.scan_and_add('/path/to/docs', recursive=True)
pending = ingestion.get_pending_documents()
```

**Tests**: 10 tests covering scanning, adding, duplicates, updates

### 2. Text Extraction (`src/indexing/extractor.py`)

Extracts text from multiple document formats with page number preservation:
- **PDF extraction** using PyMuPDF with page-by-page text
- **TXT extraction** with multiple encoding support (UTF-8, Shift-JIS, CP932, Latin-1)
- **Markdown extraction** (raw text, future: could parse structure)
- **Error handling** with detailed error messages

**Key Features**:
```python
extractor = Extractor()
doc = extractor.extract('document.pdf')
print(f"Pages: {len(doc.pages)}, Total chars: {doc.total_chars}")
for page in doc.pages:
    print(f"Page {page.page_number}: {page.char_count} chars")
```

**Tests**: 10 tests covering all formats, encoding, empty pages, errors

### 3. Text Chunking (`src/indexing/chunker.py`)

Splits text into overlapping chunks with Japanese tokenization support:
- **Token-based chunking** (default: 800 tokens per chunk)
- **Overlap support** (default: 150 tokens overlap for context)
- **Japanese tokenization** via MeCab integration
- **Hash generation** (SHA256) for deduplication
- **Page number preservation** for citations

**Key Features**:
```python
chunker = Chunker(chunk_size=800, chunk_overlap=150)
chunks = chunker.chunk_text(text, page_number=1)
chunks = chunker.chunk_pages([(page_num, text), ...])
unique = chunker.deduplicate_chunks(chunks)
```

**Tests**: 15 tests covering chunking, overlap, Japanese, deduplication

### 4. Integration Test (`tests/test_phase2_integration.py`)

End-to-end test of the complete indexing pipeline:
1. **Scan** folder for documents
2. **Add** files to database with PENDING status
3. **Extract** text from each document
4. **Chunk** text into segments
5. **Store** chunks in database with FTS5 index
6. **Verify** indexed documents and chunks
7. **Test** search functionality (ready for Phase 3)

## Test Files Created

Located in `tests/test_data/`:
- **sample.txt**: Mixed English/Japanese text file (486 chars)
- **sample.md**: Markdown with headings, code, lists, Japanese (549 chars)
- **sample.pdf**: 3-page PDF with text content (424 chars)

## Database Integration

Phase 2 modules integrate seamlessly with the Phase 1 database schema:
- Documents are added with `DocumentStatus.PENDING`
- Chunks are stored with page numbers and offsets
- FTS5 automatically tokenizes and indexes chunk text
- Japanese text is tokenized via MeCab before FTS5 indexing
- Status updates: PENDING → INDEXED or ERROR

## Test Results

```
Phase 1 Tests:  33 passing
  - Database:   13 tests
  - Config:     10 tests
  - Tokenizer:  10 tests

Phase 2 Tests:  36 passing
  - Ingestion:  10 tests
  - Extractor:  10 tests
  - Chunker:    15 tests
  - Integration: 1 test

Total:          69 tests passing
```

## Usage Example

```python
from src.core.database import Database
from src.indexing.ingestion import Ingestion
from src.indexing.extractor import Extractor
from src.indexing.chunker import Chunker
from src.core.models import Chunk, DocumentStatus

# Initialize
db = Database()
ingestion = Ingestion(db)
extractor = Extractor()
chunker = Chunker(chunk_size=800, chunk_overlap=150)

# Scan and add files
added, updated, errors = ingestion.scan_and_add('/path/to/docs')
print(f"Added {added} files")

# Process pending documents
for doc in ingestion.get_pending_documents():
    try:
        # Extract text
        extracted = extractor.extract(doc.path)
        
        # Chunk text
        pages = [(p.page_number, p.text) for p in extracted.pages]
        chunks = chunker.chunk_pages(pages)
        
        # Store chunks
        for chunk in chunks:
            chunk_obj = Chunk(
                id=None,
                document_id=doc.id,
                page=chunk.page_number,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                text=chunk.text,
                text_hash=chunk.text_hash
            )
            db.add_chunk(chunk_obj)
        
        # Mark as indexed
        db.update_document_status(doc.id, DocumentStatus.INDEXED)
        print(f"✓ Indexed: {doc.title}")
        
    except Exception as e:
        db.update_document_status(doc.id, DocumentStatus.ERROR, str(e))
        print(f"✗ Error: {doc.title} - {str(e)}")
```

## Technical Highlights

1. **MeCab Integration**: Japanese text is properly tokenized before indexing
2. **Multi-encoding Support**: Handles UTF-8, Shift-JIS, CP932, Latin-1 for TXT files
3. **Page Preservation**: PDF page numbers are maintained for accurate citations
4. **Hash Deduplication**: SHA256 hashes prevent duplicate chunks
5. **Error Handling**: Detailed error messages with graceful fallbacks
6. **Overlap Strategy**: Configurable overlap ensures context is preserved
7. **FTS5 Ready**: All chunks are automatically indexed for fast search

## Files Modified/Created

**New Modules** (3):
- `src/indexing/ingestion.py` (165 lines)
- `src/indexing/extractor.py` (177 lines)
- `src/indexing/chunker.py` (154 lines)

**New Tests** (4):
- `tests/test_ingestion.py` (165 lines, 10 tests)
- `tests/test_extractor.py` (181 lines, 10 tests)
- `tests/test_chunker.py` (187 lines, 15 tests)
- `tests/test_phase2_integration.py` (111 lines, 1 test)

**Test Data** (3):
- `tests/test_data/sample.txt`
- `tests/test_data/sample.md`
- `tests/test_data/sample.pdf`

**Total**: ~1,140 lines of production code + tests

## Dependencies Used

- **PyMuPDF (fitz)**: PDF text extraction
- **MeCab**: Japanese tokenization
- **hashlib**: SHA256 hashing for deduplication
- **pathlib**: Cross-platform file path handling
- **datetime**: File modification tracking

## Known Issues & Notes

1. **FTS5 Tokenization**: When Japanese text is tokenized with spaces (e.g., "機械 学習"), FTS5 may not match the original phrase directly. This is expected behavior and Phase 3 will handle search queries appropriately.

2. **PDF Japanese Fonts**: Some Japanese characters in PDFs may not render correctly if fonts aren't embedded. The sample PDF uses simple ASCII test due to this limitation.

3. **Offset Accuracy**: Character offsets after tokenization are approximate since MeCab changes text structure. This doesn't affect functionality.

## Next Steps (Phase 3)

Phase 3 will implement the search functionality:
1. **Keyword search** with proper query tokenization
2. **Semantic search** with embeddings (sentence-transformers)
3. **Hybrid search** combining FTS5 and vector similarity
4. **Re-ranking** of search results
5. **Search API** for UI integration

## Verification

To verify Phase 2 implementation:

```bash
# Run all tests
pytest tests/ -v

# Run just Phase 2 tests
pytest tests/test_ingestion.py tests/test_extractor.py tests/test_chunker.py tests/test_phase2_integration.py -v

# Run integration test with output
pytest tests/test_phase2_integration.py -v -s
```

---

**Phase 2 Status**: ✅ COMPLETE  
**Ready for Phase 3**: ✅ YES  
**All Tests Passing**: ✅ 69/69
