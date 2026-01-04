"""Database management for the RAG application."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager
import uuid

from .models import (
    Document, Chunk, Embedding, IndexJob, Settings,
    DocumentStatus, GenerationMode, SearchResult
)
from .tokenizer import get_tokenizer


class Database:
    """SQLite database manager with FTS5 support."""
    
    def __init__(self, db_path: str = "data/folderrag.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.tokenizer = get_tokenizer()
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    ext TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT
                )
            """)
            
            # Chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    page INTEGER,
                    start_offset INTEGER NOT NULL,
                    end_offset INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Create index on document_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_document_id 
                ON chunks(document_id)
            """)
            
            # FTS5 virtual table for full-text search
            # Using unicode61 tokenizer for better Japanese support
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    content='',
                    tokenize='unicode61 remove_diacritics 0'
                )
            """)
            
            # Triggers to keep FTS5 in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text)
                    VALUES (new.rowid, new.text);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.rowid, old.text);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.rowid, old.text);
                    INSERT INTO chunks_fts(rowid, text)
                    VALUES (new.rowid, new.text);
                END
            """)
            
            # Embeddings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    vector_id INTEGER NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                )
            """)
            
            # Index jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_jobs (
                    id TEXT PRIMARY KEY,
                    target_path TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    finished_at REAL,
                    total INTEGER NOT NULL,
                    done INTEGER NOT NULL,
                    error_count INTEGER NOT NULL,
                    log TEXT
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
    
    # Document operations
    def add_document(self, document: Document) -> None:
        """Add a document to the database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO documents (id, path, title, ext, mtime, size, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document.id,
                document.path,
                document.title,
                document.ext,
                document.mtime.timestamp(),
                document.size,
                document.status.value,
                document.error_message
            ))
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            
            if row:
                return Document(
                    id=row['id'],
                    path=row['path'],
                    title=row['title'],
                    ext=row['ext'],
                    mtime=datetime.fromtimestamp(row['mtime']),
                    size=row['size'],
                    status=DocumentStatus(row['status']),
                    error_message=row['error_message']
                )
            return None
    
    def get_document_by_path(self, path: str) -> Optional[Document]:
        """Get a document by file path."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE path = ?", (path,)
            ).fetchone()
            
            if row:
                return Document(
                    id=row['id'],
                    path=row['path'],
                    title=row['title'],
                    ext=row['ext'],
                    mtime=datetime.fromtimestamp(row['mtime']),
                    size=row['size'],
                    status=DocumentStatus(row['status']),
                    error_message=row['error_message']
                )
            return None
    
    def update_document_status(self, document_id: str, status: DocumentStatus, 
                              error_message: Optional[str] = None) -> None:
        """Update document status."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE documents SET status = ?, error_message = ?
                WHERE id = ?
            """, (status.value, error_message, document_id))
    
    def delete_document(self, document_id: str) -> None:
        """Delete a document and its chunks."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    
    def get_all_documents(self) -> List[Document]:
        """Get all documents."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM documents").fetchall()
            return [
                Document(
                    id=row['id'],
                    path=row['path'],
                    title=row['title'],
                    ext=row['ext'],
                    mtime=datetime.fromtimestamp(row['mtime']),
                    size=row['size'],
                    status=DocumentStatus(row['status']),
                    error_message=row['error_message']
                )
                for row in rows
            ]
    
    # Chunk operations
    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk to the database.
        
        The text is automatically tokenized for Japanese support before
        being added to the FTS5 index via triggers.
        """
        # Tokenize text for FTS5 (handles Japanese)
        tokenized_text = self.tokenizer.tokenize(chunk.text)
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO chunks (id, document_id, page, start_offset, end_offset, text, text_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.id,
                chunk.document_id,
                chunk.page,
                chunk.start_offset,
                chunk.end_offset,
                tokenized_text,  # Store tokenized version for FTS5
                chunk.text_hash
            ))
    
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
            
            if row:
                return Chunk(
                    id=row['id'],
                    document_id=row['document_id'],
                    page=row['page'],
                    start_offset=row['start_offset'],
                    end_offset=row['end_offset'],
                    text=row['text'],
                    text_hash=row['text_hash']
                )
            return None
    
    def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        """Get all chunks for a document."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ?", (document_id,)
            ).fetchall()
            
            return [
                Chunk(
                    id=row['id'],
                    document_id=row['document_id'],
                    page=row['page'],
                    start_offset=row['start_offset'],
                    end_offset=row['end_offset'],
                    text=row['text'],
                    text_hash=row['text_hash']
                )
                for row in rows
            ]
    
    def delete_chunks_by_document(self, document_id: str) -> None:
        """Delete all chunks for a document."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    
    def get_chunk_count(self) -> int:
        """Get total number of chunks."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM chunks").fetchone()
            return row['count']
    
    # FTS5 search
    def search_chunks_fts(self, query: str, limit: int = 10) -> List[tuple[str, float]]:
        """Full-text search using FTS5 with Japanese support.
        
        Query is automatically tokenized for Japanese before searching.
        
        Args:
            query: Search query (can be Japanese or English)
            limit: Maximum number of results
        
        Returns:
            List of (chunk_id, score) tuples
        """
        # Tokenize query for Japanese support
        tokenized_query = self.tokenizer.tokenize(query)
        
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT c.id as chunk_id, cf.rank as score
                FROM chunks_fts cf
                JOIN chunks c ON c.rowid = cf.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY cf.rank
                LIMIT ?
            """, (tokenized_query, limit)).fetchall()
            
            return [(row['chunk_id'], row['score']) for row in rows]
    
    # Embedding operations
    def add_embedding(self, embedding: Embedding) -> None:
        """Add an embedding to the database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO embeddings (chunk_id, vector_id, model_name, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                embedding.chunk_id,
                embedding.vector_id,
                embedding.model_name,
                embedding.created_at.timestamp()
            ))
    
    def get_embedding(self, chunk_id: str) -> Optional[Embedding]:
        """Get an embedding by chunk ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM embeddings WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()
            
            if row:
                return Embedding(
                    chunk_id=row['chunk_id'],
                    vector_id=row['vector_id'],
                    model_name=row['model_name'],
                    created_at=datetime.fromtimestamp(row['created_at'])
                )
            return None
    
    # Index job operations
    def create_index_job(self, target_path: str, total: int) -> IndexJob:
        """Create a new index job."""
        job = IndexJob(
            id=str(uuid.uuid4()),
            target_path=target_path,
            started_at=datetime.now(),
            finished_at=None,
            total=total,
            done=0,
            error_count=0,
            log=""
        )
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO index_jobs (id, target_path, started_at, finished_at, total, done, error_count, log)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.target_path,
                job.started_at.timestamp(),
                None,
                job.total,
                job.done,
                job.error_count,
                job.log
            ))
        
        return job
    
    def update_index_job(self, job: IndexJob) -> None:
        """Update an index job."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE index_jobs
                SET finished_at = ?, done = ?, error_count = ?, log = ?
                WHERE id = ?
            """, (
                job.finished_at.timestamp() if job.finished_at else None,
                job.done,
                job.error_count,
                job.log,
                job.id
            ))
    
    def get_latest_index_job(self) -> Optional[IndexJob]:
        """Get the most recent index job."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM index_jobs
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            
            if row:
                return IndexJob(
                    id=row['id'],
                    target_path=row['target_path'],
                    started_at=datetime.fromtimestamp(row['started_at']),
                    finished_at=datetime.fromtimestamp(row['finished_at']) if row['finished_at'] else None,
                    total=row['total'],
                    done=row['done'],
                    error_count=row['error_count'],
                    log=row['log']
                )
            return None
    
    # Settings operations
    def save_setting(self, key: str, value: any) -> None:
        """Save a setting."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, (key, json.dumps(value)))
    
    def get_setting(self, key: str, default: any = None) -> any:
        """Get a setting."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            
            if row:
                return json.loads(row['value'])
            return default
    
    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {row['key']: json.loads(row['value']) for row in rows}
