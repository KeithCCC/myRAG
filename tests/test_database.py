"""Tests for database operations."""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
import uuid

from src.core.database import Database
from src.core.models import Document, Chunk, Embedding, IndexJob, DocumentStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        yield db


def test_database_creation(temp_db):
    """Test that database and tables are created."""
    assert temp_db.db_path.exists()
    
    # Check that tables exist
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'documents' in tables
        assert 'chunks' in tables
        assert 'embeddings' in tables
        assert 'index_jobs' in tables
        assert 'settings' in tables
        assert 'chunks_fts' in tables


def test_add_and_get_document(temp_db):
    """Test adding and retrieving a document."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    
    temp_db.add_document(doc)
    
    retrieved = temp_db.get_document(doc.id)
    assert retrieved is not None
    assert retrieved.id == doc.id
    assert retrieved.path == doc.path
    assert retrieved.title == doc.title
    assert retrieved.status == DocumentStatus.PENDING


def test_get_document_by_path(temp_db):
    """Test retrieving a document by path."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/unique.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    
    temp_db.add_document(doc)
    
    retrieved = temp_db.get_document_by_path("/test/unique.pdf")
    assert retrieved is not None
    assert retrieved.id == doc.id


def test_update_document_status(temp_db):
    """Test updating document status."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    
    temp_db.add_document(doc)
    temp_db.update_document_status(doc.id, DocumentStatus.INDEXED)
    
    retrieved = temp_db.get_document(doc.id)
    assert retrieved.status == DocumentStatus.INDEXED


def test_document_unique_path_constraint(temp_db):
    """Test that document paths must be unique."""
    doc1 = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document 1",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    
    doc2 = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",  # Same path
        title="Test Document 2",
        ext=".pdf",
        mtime=datetime.now(),
        size=2048,
        status=DocumentStatus.PENDING
    )
    
    temp_db.add_document(doc1)
    
    with pytest.raises(Exception):  # Should raise integrity error
        temp_db.add_document(doc2)


def test_add_and_get_chunk(temp_db):
    """Test adding and retrieving chunks."""
    # First add a document
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    temp_db.add_document(doc)
    
    # Add chunk
    chunk = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page=1,
        start_offset=0,
        end_offset=100,
        text="This is a test chunk of text.",
        text_hash="abc123"
    )
    
    temp_db.add_chunk(chunk)
    
    retrieved = temp_db.get_chunk(chunk.id)
    assert retrieved is not None
    assert retrieved.id == chunk.id
    assert retrieved.text == chunk.text
    assert retrieved.page == 1


def test_get_chunks_by_document(temp_db):
    """Test retrieving all chunks for a document."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    temp_db.add_document(doc)
    
    # Add multiple chunks
    for i in range(3):
        chunk = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            page=i + 1,
            start_offset=i * 100,
            end_offset=(i + 1) * 100,
            text=f"Chunk {i}",
            text_hash=f"hash{i}"
        )
        temp_db.add_chunk(chunk)
    
    chunks = temp_db.get_chunks_by_document(doc.id)
    assert len(chunks) == 3


def test_delete_document_cascades(temp_db):
    """Test that deleting a document also deletes its chunks."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.PENDING
    )
    temp_db.add_document(doc)
    
    chunk = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page=1,
        start_offset=0,
        end_offset=100,
        text="Test chunk",
        text_hash="abc"
    )
    temp_db.add_chunk(chunk)
    
    # Delete document
    temp_db.delete_document(doc.id)
    
    # Verify document and chunks are gone
    assert temp_db.get_document(doc.id) is None
    assert temp_db.get_chunk(chunk.id) is None


def test_fts5_search(temp_db):
    """Test full-text search functionality."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.INDEXED
    )
    temp_db.add_document(doc)
    
    chunk1 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page=1,
        start_offset=0,
        end_offset=100,
        text="Python is a great programming language",
        text_hash="hash1"
    )
    
    chunk2 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page=2,
        start_offset=100,
        end_offset=200,
        text="JavaScript is also a programming language",
        text_hash="hash2"
    )
    
    temp_db.add_chunk(chunk1)
    temp_db.add_chunk(chunk2)
    
    # Search for "Python"
    results = temp_db.search_chunks_fts("Python", limit=10)
    assert len(results) == 1
    assert results[0][0] == chunk1.id
    
    # Search for "programming"
    results = temp_db.search_chunks_fts("programming", limit=10)
    assert len(results) == 2


def test_add_and_get_embedding(temp_db):
    """Test adding and retrieving embeddings."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.INDEXED
    )
    temp_db.add_document(doc)
    
    chunk = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page=1,
        start_offset=0,
        end_offset=100,
        text="Test chunk",
        text_hash="abc"
    )
    temp_db.add_chunk(chunk)
    
    embedding = Embedding(
        chunk_id=chunk.id,
        vector_id=42,
        model_name="test-model",
        created_at=datetime.now()
    )
    temp_db.add_embedding(embedding)
    
    retrieved = temp_db.get_embedding(chunk.id)
    assert retrieved is not None
    assert retrieved.chunk_id == chunk.id
    assert retrieved.vector_id == 42


def test_index_job_operations(temp_db):
    """Test creating and updating index jobs."""
    job = temp_db.create_index_job("/test/folder", total=10)
    
    assert job.id is not None
    assert job.target_path == "/test/folder"
    assert job.total == 10
    assert job.done == 0
    assert job.finished_at is None
    
    # Update job
    job.done = 5
    job.error_count = 1
    job.finished_at = datetime.now()
    temp_db.update_index_job(job)
    
    # Retrieve latest job
    latest = temp_db.get_latest_index_job()
    assert latest.id == job.id
    assert latest.done == 5
    assert latest.error_count == 1


def test_settings_operations(temp_db):
    """Test saving and retrieving settings."""
    # Save settings
    temp_db.save_setting('test_key', 'test_value')
    temp_db.save_setting('test_list', [1, 2, 3])
    temp_db.save_setting('test_dict', {'key': 'value'})
    
    # Retrieve settings
    assert temp_db.get_setting('test_key') == 'test_value'
    assert temp_db.get_setting('test_list') == [1, 2, 3]
    assert temp_db.get_setting('test_dict') == {'key': 'value'}
    assert temp_db.get_setting('nonexistent', 'default') == 'default'
    
    # Get all settings
    all_settings = temp_db.get_all_settings()
    assert 'test_key' in all_settings
    assert all_settings['test_key'] == 'test_value'


def test_chunk_count(temp_db):
    """Test getting total chunk count."""
    doc = Document(
        id=str(uuid.uuid4()),
        path="/test/doc.pdf",
        title="Test Document",
        ext=".pdf",
        mtime=datetime.now(),
        size=1024,
        status=DocumentStatus.INDEXED
    )
    temp_db.add_document(doc)
    
    assert temp_db.get_chunk_count() == 0
    
    for i in range(5):
        chunk = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            page=1,
            start_offset=i * 100,
            end_offset=(i + 1) * 100,
            text=f"Chunk {i}",
            text_hash=f"hash{i}"
        )
        temp_db.add_chunk(chunk)
    
    assert temp_db.get_chunk_count() == 5
