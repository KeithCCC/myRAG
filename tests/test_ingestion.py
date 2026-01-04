"""Tests for the ingestion module."""
import pytest
import tempfile
import shutil
from pathlib import Path

from src.core.database import Database
from src.core.models import DocumentStatus
from src.indexing.ingestion import Ingestion


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)  # Auto-initializes in __init__
    
    yield db
    
    # Cleanup - just delete the file
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_folder():
    """Create a temporary folder with test files."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test files
    Path(temp_dir, 'test1.pdf').write_text('PDF content')
    Path(temp_dir, 'test2.txt').write_text('TXT content')
    Path(temp_dir, 'test3.md').write_text('MD content')
    Path(temp_dir, 'ignore.doc').write_text('DOC content')
    
    # Create subdirectory
    sub_dir = Path(temp_dir, 'subdir')
    sub_dir.mkdir()
    Path(sub_dir, 'test4.pdf').write_text('Nested PDF')
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_scan_folder_recursive(temp_folder):
    """Test scanning folder recursively."""
    ingestion = Ingestion(None)  # No DB needed for scanning
    files = ingestion.scan_folder(temp_folder, recursive=True)
    
    assert len(files) == 4  # 3 root + 1 nested
    assert any('test1.pdf' in f for f in files)
    assert any('test2.txt' in f for f in files)
    assert any('test3.md' in f for f in files)
    assert any('test4.pdf' in f for f in files)
    assert not any('ignore.doc' in f for f in files)


def test_scan_folder_non_recursive(temp_folder):
    """Test scanning folder non-recursively."""
    ingestion = Ingestion(None)  # No DB needed for scanning
    files = ingestion.scan_folder(temp_folder, recursive=False)
    
    assert len(files) == 3  # Only root level
    assert any('test1.pdf' in f for f in files)
    assert not any('test4.pdf' in f for f in files)


def test_scan_empty_folder():
    """Test scanning empty folder."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ingestion = Ingestion(None)  # No DB needed for scanning
        files = ingestion.scan_folder(temp_dir)
        
        assert len(files) == 0


def test_scan_nonexistent_folder():
    """Test scanning nonexistent folder."""
    ingestion = Ingestion(None)  # No DB needed for scanning
    
    with pytest.raises(FileNotFoundError):
        ingestion.scan_folder('/nonexistent/folder')


def test_add_files_to_db(temp_db, temp_folder):
    """Test adding files to database."""
    ingestion = Ingestion(temp_db)
    files = ingestion.scan_folder(temp_folder, recursive=True)
    
    added, updated, errors = ingestion.add_files_to_db(files)
    
    assert added == 4
    assert updated == 0
    assert len(errors) == 0
    
    # Verify in database
    docs = temp_db.get_all_documents()
    assert len(docs) == 4
    assert all(doc.status == DocumentStatus.PENDING for doc in docs)


def test_add_duplicate_files(temp_db, temp_folder):
    """Test adding same files twice."""
    ingestion = Ingestion(temp_db)
    files = ingestion.scan_folder(temp_folder)
    
    # First add
    added1, _, _ = ingestion.add_files_to_db(files)
    
    # Second add (should skip)
    added2, updated2, _ = ingestion.add_files_to_db(files)
    
    assert added1 == 4
    assert added2 == 0
    assert updated2 == 0


def test_add_modified_files(temp_db, temp_folder):
    """Test adding modified files."""
    ingestion = Ingestion(temp_db)
    test_file = Path(temp_folder, 'test1.pdf')
    
    # First add
    ingestion.add_files_to_db([str(test_file)])
    
    # Modify file
    import time
    time.sleep(0.1)  # Ensure mtime changes
    test_file.write_text('Modified content')
    
    # Add again (should update)
    added, updated, _ = ingestion.add_files_to_db([str(test_file)])
    
    assert added == 0
    assert updated == 1


def test_get_pending_documents(temp_db, temp_folder):
    """Test getting pending documents."""
    ingestion = Ingestion(temp_db)
    files = ingestion.scan_folder(temp_folder)
    ingestion.add_files_to_db(files)
    
    pending = ingestion.get_pending_documents()
    
    assert len(pending) == 4
    assert all(doc.status == DocumentStatus.PENDING for doc in pending)


def test_scan_and_add(temp_db, temp_folder):
    """Test combined scan and add operation."""
    ingestion = Ingestion(temp_db)
    
    added, updated, errors = ingestion.scan_and_add(temp_folder)
    
    assert added == 4
    assert updated == 0
    assert len(errors) == 0
    
    docs = temp_db.get_all_documents()
    assert len(docs) == 4


def test_custom_extensions(temp_db):
    """Test custom file extensions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files with custom extensions
        Path(temp_dir, 'test.custom').write_text('Custom content')
        Path(temp_dir, 'test.pdf').write_text('PDF content')
        
        ingestion = Ingestion(temp_db, allowed_extensions=['.custom'])
        files = ingestion.scan_folder(temp_dir)
        
        assert len(files) == 1
        assert files[0].endswith('.custom')
