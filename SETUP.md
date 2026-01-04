# Phase 1 Setup Instructions

## Prerequisites

### 1. Install Python
Download and install Python 3.10 or higher from:
- https://www.python.org/downloads/

During installation:
- ✓ Check "Add Python to PATH"
- ✓ Check "Install pip"

Verify installation:
```powershell
python --version
pip --version
```

### 2. Install Dependencies

```powershell
cd c:\Development\projects\myRAG
pip install -r requirements.txt
```

### 3. Configure Environment (Optional)

For OpenAI integration:
```powershell
copy .env.example .env
# Edit .env and add your OpenAI API key
```

## Verify Phase 1 Setup

### Run the application:
```powershell
python main.py
```

Expected output:
```
==================================================
Folder RAG - Local Document Search
==================================================

Initializing database...
✓ Database created at: data\folderrag.db

Loading configuration...
✓ Embedding model: all-MiniLM-L6-v2
✓ Chunk size: 800
✓ Allowed extensions: .pdf, .txt, .md
✓ Generation mode: none

Verifying database schema...
✓ Table 'chunks' exists
✓ Table 'chunks_fts' exists
✓ Table 'documents' exists
✓ Table 'embeddings' exists
✓ Table 'index_jobs' exists
✓ Table 'settings' exists

==================================================
Phase 1 Setup Complete!
==================================================
```

## Run Tests

```powershell
pytest tests/ -v
```

Expected: All tests pass ✓

## Phase 1 Checklist

- [x] Project directory structure created
- [x] All __init__.py files in place
- [x] requirements.txt with dependencies
- [x] Database schema implemented (SQLite + FTS5)
- [x] Data models defined
- [x] Configuration management implemented
- [x] Unit tests created (test_database.py, test_config.py)
- [x] Main entry point created
- [x] README.md documentation
- [x] .gitignore configured

## Manual Verification

Check that these files exist:

### Core files:
- [x] src/core/database.py
- [x] src/core/models.py
- [x] src/core/config.py

### Test files:
- [x] tests/test_database.py
- [x] tests/test_config.py

### Configuration:
- [x] requirements.txt
- [x] .env.example
- [x] .gitignore

### Entry point:
- [x] main.py

## Test Database Operations

After Python is installed, you can verify database operations:

```python
# Test in Python REPL
from src.core.database import Database
from src.core.models import Document, DocumentStatus
from datetime import datetime
import uuid

# Create database
db = Database("data/test.db")

# Add a document
doc = Document(
    id=str(uuid.uuid4()),
    path="/test/sample.pdf",
    title="Sample Document",
    ext=".pdf",
    mtime=datetime.now(),
    size=1024,
    status=DocumentStatus.PENDING
)
db.add_document(doc)

# Retrieve it
retrieved = db.get_document(doc.id)
print(f"Document: {retrieved.title}, Status: {retrieved.status.value}")
```

## What's Next?

Once Phase 1 verification is complete:
1. ✓ Database working
2. ✓ Configuration loading
3. ✓ Tests passing

Proceed to **Phase 2: Indexing Pipeline**
- File ingestion
- Text extraction
- Chunking
