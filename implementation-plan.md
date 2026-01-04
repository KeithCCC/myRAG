# Folder RAG Implementation Plan

## Overview
Building a local RAG (Retrieval-Augmented Generation) application that indexes files from user-specified folders and provides keyword + semantic search with cited answers.

**Tech Stack:**
- Backend: Python
- UI: PySide6
- LLM: OpenAI API (Cloud)
- Database: SQLite with FTS5
- Vector Search: FAISS
- PDF Processing: PyMuPDF or pdfplumber
- Embeddings: sentence-transformers (local)

---

## Phase 1: Project Setup & Foundation (Days 1-2)

### 1.1 Project Structure Setup
```
myRAG/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── config.py
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── ingestion.py
│   │   ├── extractor.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── index_store.py
│   ├── search/
│   │   ├── __init__.py
│   │   └── retriever.py
│   ├── generation/
│   │   ├── __init__.py
│   │   └── answerer.py
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── library_view.py
│       ├── search_view.py
│       └── ask_view.py
├── tests/
├── data/
├── requirements.txt
├── README.md
└── main.py
```

### 1.2 Dependencies Installation
Create `requirements.txt`:
```
PySide6>=6.6.0
sentence-transformers>=2.2.0
faiss-cpu>=1.7.4
PyMuPDF>=1.23.0
openai>=1.0.0
python-dotenv>=1.0.0
```

### 1.3 Database Schema Implementation
Create SQLite database with tables:
- `documents`
- `chunks`
- `embeddings`
- `index_jobs`
- `settings`
- Enable FTS5 virtual table for full-text search

### 1.4 Phase 1 Testing
**Tests to implement:**
- Verify database connection and table creation
- Test CRUD operations on each table
- Validate schema constraints (unique paths, foreign keys)
- Test settings table read/write
- Verify FTS5 virtual table is created correctly

**Manual verification:**
- Check database file created in data/ folder
- Use SQLite browser to inspect schema
- Run basic INSERT/SELECT queries

**Deliverable:** Project structure, database schema implemented, dependencies installed, basic DB tests passing

---

## Phase 2: Core Indexing Pipeline (Days 3-5)

### 2.1 File Ingestion Module
**File:** `src/indexing/ingestion.py`
- Folder scanning with recursive traversal
- Filter by extensions (.pdf, .txt, .md)
- File metadata extraction (path, mtime, size)
- Duplicate detection
- Store in `documents` table with status='pending'

### 2.2 Text Extractor Module
**File:** `src/indexing/extractor.py`
- **TXT/MD:** Direct read with encoding detection
- **PDF:** Extract with page numbers using PyMuPDF
  - Preserve page metadata for each text block
  - Handle extraction errors gracefully
- Update document status to 'indexed' or 'error'

### 2.3 Chunker Module
**File:** `src/indexing/chunker.py`
- Chunk size: 500-1000 tokens
- Overlap: 100-200 tokens
- Preserve page numbers for PDF chunks
- Calculate text hash for deduplication
- Store chunks in `chunks` table

### 2.4 Phase 2 Testing
**Test files to create:**
- `tests/test_ingestion.py`
- `tests/test_extractor.py`
- `tests/test_chunker.py`

**Tests to implement:**
- Test folder scanning with nested directories
- Test file filtering by extension
- Test PDF extraction with page numbers (use sample PDF)
- Test TXT/MD extraction with various encodings (UTF-8, UTF-16)
- Test chunker with different text lengths (short, medium, long)
- Test chunk overlap calculation
- Test deduplication by hash
- Test error handling for corrupted files
- Verify chunks stored with correct document_id and page numbers

**Manual verification:**
- Process test folder with 5-10 mixed files (PDF, TXT, MD)
- Check `documents` table has all files
- Check `chunks` table has expected number of chunks
- Verify page numbers for PDF chunks
- Test with a corrupted PDF, verify error is logged

**Success criteria:** 10 test files processed successfully with chunks in database

**Deliverable:** Complete ingestion pipeline from folder to chunks, all tests passing

---

## Phase 3: Search Foundation (Days 6-8)

### 3.1 SQLite FTS5 Integration
**File:** `src/core/database.py` extension
- Create FTS5 virtual table for chunk text
- Implement keyword search with ranking
- Return results with document metadata and snippets

### 3.2 Embedder Module
**File:** `src/indexing/embedder.py`
- Initialize sentence-transformers model (e.g., all-MiniLM-L6-v2)
- Batch embedding generation
- Store vector dimensions in settings
- Progress tracking for large batches

### 3.3 FAISS Index Manager
**File:** `src/indexing/index_store.py`
- Create FAISS index (IndexFlatIP or IndexHNSWFlat)
- Map FAISS IDs to chunk IDs
- Save/load index from disk
- Update index incrementally

### 3.4 Retriever Module
**File:** `src/search/retriever.py`
- **Keyword Search:** Query FTS5, return Top-K
- **Semantic Search:** Embed query, FAISS search, return Top-K
- **Hybrid Search:**
  - Get Top-20 from each
  - Normalize scores (min-max or z-score)
  - Merge and re-rank
  - Return Top-10

### 3.5 Phase 3 Testing
**Test files to create:**
- `tests/test_embedder.py`
- `tests/test_retriever.py`
- `tests/test_faiss_index.py`

**Tests to implement:**
- Test embedding generation for single chunk
- Test batch embedding with progress tracking
- Test embedding dimension consistency
- Test FAISS index creation and saving/loading
- Test FAISS ID to chunk ID mapping
- Test keyword search returns correct results
- Test semantic search with known similar queries
- Test hybrid search score normalization
- Test retriever with empty database
- Test retriever with special characters in query

**Manual verification:**
- Index 20-30 documents from Phase 2
- **Keyword search test:**
  - Query: exact phrase from a document → should return that chunk
  - Query: unique technical term → should return relevant chunks
- **Semantic search test:**
  - Query: paraphrased question → should return related chunks
  - Query: conceptual term → should return semantically similar content
- **Hybrid search test:**
  - Compare results with keyword-only and semantic-only
  - Verify top results make sense
  - Check score normalization (no negative scores)

**Success criteria:**
- All three search modes return results in <2 seconds for 1000 chunks
- Relevant results appear in Top-5 for test queries
- No crashes on edge cases (empty query, special chars)

**Deliverable:** All three search modes working with test queries, comprehensive tests passing

---

## Phase 4: Basic UI (Days 9-11)

### 4.1 Main Window & Navigation
**File:** `src/ui/main_window.py`
- PySide6 QMainWindow with tab widget
- Three tabs: Library, Search, Ask
- Menu bar with Settings
- Status bar for notifications

### 4.2 Library View
**File:** `src/ui/library_view.py`
- Folder list widget
- Add/Remove folder buttons
- Index statistics table:
  - Folder path
  - Last updated
  - Document count
  - Chunk count
  - Error count
- "Create Index" / "Re-index" buttons
- Progress bar during indexing
- Error log viewer (expandable section)

### 4.3 Search View
**File:** `src/ui/search_view.py`
- Search input field
- Tab widget: Semantic / Keyword / Hybrid
- Results list with citation cards:
  - Document name
  - Page number (for PDFs)
  - Text snippet (highlighted keywords)
  - Relevance score
- Click to preview full chunk text
- Export results button

### 4.4 Phase 4 Testing
**UI testing approach:**
- Manual testing (primary for UI)
- Unit tests for UI logic components

**Tests to implement:**
- `tests/test_ui_logic.py` - Test data formatting and filtering

**Manual testing checklist:**

**Library View:**
- [ ] Add folder button opens folder dialog
- [ ] Selected folder appears in list
- [ ] Remove folder button works
- [ ] "Create Index" button triggers indexing
- [ ] Progress bar updates during indexing
- [ ] Statistics table shows correct counts
- [ ] Error log displays failed files with reasons
- [ ] Re-index button works for existing folder

**Search View:**
- [ ] Search input accepts text
- [ ] Each tab (Semantic/Keyword/Hybrid) shows results
- [ ] Results display document name, page, snippet, score
- [ ] Click on result shows full chunk preview
- [ ] Keyword highlighting works in snippets
- [ ] Export button generates file with results
- [ ] Empty query shows appropriate message
- [ ] No results query shows "No matches found"

**General UI:**
- [ ] Tab switching works smoothly
- [ ] Window resizes properly
- [ ] Status bar shows notifications
- [ ] Application doesn't freeze during long operations

**Performance testing:**
- Test with 100+ documents indexed
- Search response time <2 seconds
- UI remains responsive during indexing

**Success criteria:**
- All manual test cases pass
- UI is intuitive for first-time users
- No crashes during normal operation

**Deliverable:** Functional UI for folder management and search, all manual tests verified

---

## Phase 5: Ask/RAG Feature (Days 12-14)

### 5.1 Answerer Module (No-Generation Mode)
**File:** `src/generation/answerer.py`
- Query → Retriever (hybrid search Top-10)
- Extract key points from top chunks
- Format bullet-point summary
- Always display citation cards

### 5.2 OpenAI Integration (Generation Mode)
- Setup OpenAI client with API key
- Create prompt template:
  ```
  Context: [Retrieved chunks]
  Question: [User query]
  Instructions: Answer based only on context. Cite sources.
  ```
- Stream response for better UX
- Parse citations from response
- Link citations to retrieved chunks

### 5.3 Ask View
**File:** `src/ui/ask_view.py`
- Question input (multi-line text edit)
- Generation mode toggle: No-Generation / OpenAI
- Submit button
- Answer display area (rich text)
- Citation cards panel (Top 5-10)
- Copy answer button

### 5.4 Phase 5 Testing
**Test files to create:**
- `tests/test_answerer.py`

**Tests to implement:**
- Test no-generation mode formats bullet points correctly
- Test citation extraction and linking
- Test prompt template generation
- Mock OpenAI API responses to test parsing
- Test error handling for API failures
- Test streaming response handling
- Test citation card creation from retrieved chunks

**Manual testing checklist:**

**No-Generation Mode:**
- [ ] Question retrieves relevant chunks
- [ ] Answer shows key points as bullet list
- [ ] Citations displayed with correct document names
- [ ] Citations show page numbers for PDFs
- [ ] Click citation opens full chunk text
- [ ] Answer appears in <3 seconds

**OpenAI Generation Mode:**
- [ ] Question sends context to OpenAI
- [ ] Answer streams in real-time (if implemented)
- [ ] Answer is factually based on retrieved context
- [ ] Citations are correctly linked to sources
- [ ] API key error shows helpful message
- [ ] Network error handled gracefully
- [ ] Cost tracking/token usage visible (optional)

**Test queries (use these with indexed test documents):**
1. **Factual query:** "What is [specific term in docs]?"
   - Verify answer comes from indexed content
   - Check citation accuracy
2. **Multi-document query:** "Compare [concept A] and [concept B]"
   - Verify pulls from multiple documents
   - Check multiple citations
3. **Not-found query:** "What is quantum teleportation?" (if not in docs)
   - Verify "information not found in documents" response
4. **Complex query:** "How do I [multi-step process]?"
   - Verify coherent answer
   - Check step-by-step format

**Success criteria:**
- No-generation mode works without internet
- OpenAI mode produces accurate, cited answers
- Citations always traceable to source chunks
- Both modes handle "not found" gracefully

**Deliverable:** Complete RAG functionality with both modes, all tests passing

---

## Phase 6: Index Management & Error Handling (Days 15-16)

### 6.1 Index Jobs Tracking
**File:** `src/indexing/index_store.py` extension
- Create job record in `index_jobs` table
- Update progress (total/done/error_count)
- Log errors with file paths and reasons
- Job completion timestamp

### 6.2 Error Handling & Logging
- Wrap all file operations in try-catch
- Log extraction errors to database
- Display user-friendly error messages
- Retry mechanism for transient failures
- Validation for corrupted PDFs

### 6.3 Re-indexing Logic
- Detect file changes (mtime comparison)
- Delete old chunks and embeddings
- Re-process modified files only
- Update existing records

### 6.4 Phase 6 Testing
**Test files to create:**
- `tests/test_index_jobs.py`
- `tests/test_error_handling.py`
- `tests/test_reindexing.py`

**Tests to implement:**
- Test job creation and status updates
- Test progress tracking (total/done/error counts)
- Test error logging to database
- Test concurrent indexing safety
- Test re-indexing detects changed files
- Test re-indexing skips unchanged files
- Test orphaned chunks cleanup
- Test various file error scenarios:
  - Corrupted PDF
  - Locked file
  - Missing file (deleted during indexing)
  - Encoding errors
  - Permission errors

**Manual testing checklist:**
- [ ] Start indexing 50 files
- [ ] Progress bar updates smoothly
- [ ] Total/done/error counts are accurate
- [ ] Intentionally add corrupted PDF → error logged
- [ ] Error log shows file path and error reason
- [ ] Indexing completes successfully for valid files
- [ ] Job finish timestamp recorded
- [ ] Modify 5 files (update content, save)
- [ ] Re-index → only modified files processed
- [ ] Delete 3 files from folder → re-index removes them
- [ ] No duplicate chunks after re-indexing

**Stress testing:**
- Index 200-300 PDFs
- Monitor memory usage (should stay reasonable)
- Verify all chunks stored correctly
- Check FAISS index file size
- Test search performance after large index

**Success criteria:**
- Errors don't stop entire indexing process
- Progress accurately reflects completion
- Re-indexing is efficient (only changed files)
- UI shows helpful error messages

**Deliverable:** Robust indexing with progress tracking and error reporting, all edge cases handled

---

## Phase 7: Settings & Configuration (Day 17)

### 7.1 Settings Module
**File:** `src/core/config.py`
- Load/save from `settings` table
- Configuration options:
  - Allowed extensions (JSON array)
  - Embedding model name
  - Generation mode (none/openai)
  - OpenAI API key
  - Chunk size/overlap
  - Top-K for search

### 7.2 Settings UI
- Settings dialog window
- Form fields for all configurable options
- Validate inputs before saving
- Restart prompt if model changes

### 7.3 Phase 7 Testing
**Test files to create:**
- `tests/test_config.py`

**Tests to implement:**
- Test settings load from database
- Test settings save to database
- Test default values when no settings exist
- Test validation for each setting type
- Test invalid API key detection
- Test extension list parsing (JSON)
- Test chunk size limits (min/max)

**Manual testing checklist:**
- [ ] Open settings dialog
- [ ] Change each setting
- [ ] Save settings
- [ ] Restart app → settings persist
- [ ] Enter invalid API key → validation error shown
- [ ] Change embedding model → restart prompt appears
- [ ] Add custom extension (e.g., .log) → works in indexing
- [ ] Set invalid chunk size (e.g., 0) → validation prevents save
- [ ] Reset to defaults button works

**Integration testing:**
- Change settings → perform full workflow:
  1. Change allowed extensions to only .txt
  2. Index folder → verify only .txt files indexed
  3. Change chunk size to 200 tokens
  4. Re-index → verify new chunk sizes
  5. Change generation mode → verify Ask view respects setting

**Success criteria:**
- All settings persist across restarts
- Validation prevents invalid configurations
- Settings changes take effect immediately or after restart

**Deliverable:** User-configurable settings with persistence, all validation tests passing

---

## Phase 8: Testing & Polish (Days 18-20)

### 8.1 Unit Tests
- Test chunker with various text lengths
- Test retriever score normalization
- Test database CRUD operations
- Mock external dependencies (OpenAI)

### 8.2 Integration Tests
- End-to-end: Folder → Index → Search → Answer
- Test with sample document set (50-100 files)
- Verify citation accuracy
- Performance benchmarks

### 8.3 UI/UX Polish
- Loading spinners and animations
- Keyboard shortcuts (Ctrl+F for search)
- Tooltips and help text
- Dark mode support (optional)
- Responsive layouts

### 8.4 Documentation
- User manual (README.md)
- Installation guide
- Troubleshooting section
- API documentation (docstrings)

**Deliverable:** Tested, polished application ready for use

---

## Definition of Done Checklist

- [ ] Can index 100-300 PDFs from specified folder
- [ ] Keyword search returns relevant results with FTS5
- [ ] Semantic search returns relevant results with FAISS
- [ ] Hybrid search merges both methods effectively
- [ ] Ask mode returns answers with citations
- [ ] No-generation mode works without LLM
- [ ] Errors are visible in UI with file paths and reasons
- [ ] Progress bar shows indexing status
- [ ] Application doesn't crash on corrupted files
- [ ] All three UI tabs are functional
- [ ] Settings can be saved and loaded
- [ ] Basic tests pass

---

## Risk Mitigation

### Technical Risks
1. **Large PDF processing:** Implement batch processing with memory limits
2. **FAISS memory usage:** Use IndexIVFFlat for >100K chunks
3. **FTS5 performance:** Add indexes on foreign keys, limit result size
4. **OpenAI API costs:** Cache responses, implement rate limiting

### Scope Risks
1. **Feature creep:** Stick to MVP spec, defer enhancements
2. **Complex PDFs:** Accept limitations, log unsupported formats
3. **Performance:** Set realistic expectations (local processing)

---

## Post-MVP Enhancements (Future)

1. OCR for scanned PDFs (Tesseract)
2. Additional formats (docx, pptx)
3. Auto-refresh on file changes (watchdog)
4. Export search results to CSV
5. Query history
6. Multi-folder projects
7. Advanced chunking (semantic splitting)
8. Local LLM support (Ollama, LlamaCPP)
9. Bookmarks and annotations
10. Graph view of document relationships

---

## Development Schedule Summary

| Phase | Duration | Focus |
|-------|----------|-------|
| 1. Setup | 2 days | Structure, dependencies, database |
| 2. Indexing | 3 days | File processing pipeline |
| 3. Search | 3 days | FTS5, FAISS, hybrid retrieval |
| 4. UI | 3 days | PySide6 interface |
| 5. RAG | 3 days | Answer generation |
| 6. Jobs | 2 days | Error handling, progress |
| 7. Settings | 1 day | Configuration |
| 8. Testing | 3 days | QA and polish |
| **Total** | **20 days** | **MVP completion** |

---

## Next Steps

1. Review and approve this implementation plan
2. Set up development environment
3. Initialize Git repository
4. Start Phase 1: Project setup
5. Daily standups to track progress
6. Weekly demo to validate functionality

**Ready to begin implementation!** 🚀
