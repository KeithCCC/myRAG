# Folder RAG - Local Document Search

A local RAG (Retrieval-Augmented Generation) application for indexing and searching documents with semantic understanding.

## Features

- **Local document indexing** (PDF, TXT, MD)
- **Hybrid search** (keyword + semantic)
- **Japanese language support** with MeCab tokenization
- **RAG-powered answers** with citations
- **Privacy-focused** (all processing local except LLM)

## Phase 1 - Setup Complete ✓

- Project structure established
- Database schema implemented (SQLite + FTS5)
- Japanese tokenization with MeCab
- Configuration management
- Core data models
- Unit tests (33 passing)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env

# Edit .env and add your OpenAI API key (optional)
```

## Verify Setup

```bash
# Run the application to verify Phase 1
python main.py

# Run tests
pytest tests/ -v
```

## Project Structure

```
myRAG/
├── src/
│   ├── core/           # Database and configuration
│   ├── indexing/       # File processing (Phase 2)
│   ├── search/         # Search and retrieval (Phase 3)
│   ├── generation/     # Answer generation (Phase 5)
│   └── ui/             # PySide6 interface (Phase 4)
├── tests/              # Unit tests
├── data/               # Database and indexes
└── main.py             # Entry point
```

## Development Status

- [x] Phase 1: Project setup and database
- [ ] Phase 2: Indexing pipeline
- [ ] Phase 3: Search functionality
- [ ] Phase 4: UI implementation
- [ ] Phase 5: RAG answers
- [ ] Phase 6: Error handling
- [ ] Phase 7: Settings management
- [ ] Phase 8: Testing and polish

## License

See LICENSE file for details.
