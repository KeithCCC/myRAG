"""File ingestion module for scanning folders and enumerating files."""
import os
from pathlib import Path
from typing import List, Set, Optional
from datetime import datetime
import uuid

from ..core.database import Database
from ..core.models import Document, DocumentStatus


class Ingestion:
    """Handles folder scanning and file enumeration for indexing."""
    
    def __init__(self, db: Optional[Database] = None, allowed_extensions: Optional[List[str]] = None):
        """Initialize ingestion with database and allowed file extensions.
        
        Args:
            db: Database instance (optional, only needed for add_files_to_db)
            allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.txt'])
                               If None, uses ['.pdf', '.txt', '.md']
        """
        self.db = db
        self.allowed_extensions = allowed_extensions or ['.pdf', '.txt', '.md']
        # Normalize extensions to lowercase
        self.allowed_extensions = [ext.lower() for ext in self.allowed_extensions]
    
    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """Scan folder for files matching allowed extensions.
        
        Args:
            folder_path: Path to folder to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of file paths found
            
        Raises:
            FileNotFoundError: If folder doesn't exist
            PermissionError: If folder is not accessible
        """
        folder = Path(folder_path)
        
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder_path}")
        
        files = []
        
        try:
            if recursive:
                # Recursively find all files
                for file_path in folder.rglob('*'):
                    if file_path.is_file() and self._is_allowed_file(file_path):
                        files.append(str(file_path.absolute()))
            else:
                # Only scan immediate directory
                for file_path in folder.glob('*'):
                    if file_path.is_file() and self._is_allowed_file(file_path):
                        files.append(str(file_path.absolute()))
        except PermissionError as e:
            raise PermissionError(f"Cannot access folder: {folder_path}") from e
        
        return files
    
    def _is_allowed_file(self, file_path: Path) -> bool:
        """Check if file extension is allowed.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file should be processed
        """
        return file_path.suffix.lower() in self.allowed_extensions
    
    def add_files_to_db(self, file_paths: List[str]) -> tuple[int, int, List[str]]:
        """Add files to database as documents with PENDING status.
        
        Checks for duplicates and updates if file was modified.
        
        Args:
            file_paths: List of file paths to add
            
        Returns:
            Tuple of (added_count, updated_count, error_messages)
        """
        if self.db is None:
            raise ValueError("Database is required for add_files_to_db()")
        
        added = 0
        updated = 0
        errors = []
        
        for file_path in file_paths:
            try:
                path_obj = Path(file_path)
                
                if not path_obj.exists():
                    errors.append(f"{file_path}: File not found")
                    continue
                
                # Get file metadata
                stat = path_obj.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                # Check if document already exists
                existing = self.db.get_document_by_path(file_path)
                
                if existing:
                    # Check if file was modified
                    if existing.mtime < mtime:
                        # File was updated, mark for re-indexing
                        self.db.update_document_status(
                            existing.id,
                            DocumentStatus.PENDING
                        )
                        updated += 1
                    # else: File unchanged, skip
                else:
                    # New file, add to database
                    doc = Document(
                        id=str(uuid.uuid4()),
                        path=file_path,
                        title=path_obj.name,
                        ext=path_obj.suffix.lower(),
                        mtime=mtime,
                        size=stat.st_size,
                        status=DocumentStatus.PENDING,
                        error_message=None
                    )
                    self.db.add_document(doc)
                    added += 1
                    
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
        
        return added, updated, errors
    
    def get_pending_documents(self) -> List[Document]:
        """Get all documents with PENDING status.
        
        Returns:
            List of documents ready for processing
        """
        if self.db is None:
            raise ValueError("Database is required for get_pending_documents()")
        
        all_docs = self.db.get_all_documents()
        return [doc for doc in all_docs if doc.status == DocumentStatus.PENDING]
    
    def scan_and_add(self, folder_path: str, recursive: bool = True) -> tuple[int, int, List[str]]:
        """Convenience method to scan folder and add files in one step.
        
        Args:
            folder_path: Path to folder to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            Tuple of (added_count, skipped_count, error_messages)
        """
        files = self.scan_folder(folder_path, recursive)
        return self.add_files_to_db(files)
