"""Library view for managing document folders and indexing."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTableWidget, QTableWidgetItem, QProgressBar,
    QTextEdit, QLabel, QFileDialog, QSplitter, QGroupBox,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from pathlib import Path
import logging
from datetime import datetime
from typing import List

from ..core.database import Database
from ..core.models import Document, DocumentStatus
from ..indexing.ingestion import Ingestion
from ..indexing.extractor import Extractor
from ..indexing.chunker import Chunker
from ..indexing.embedder import Embedder
from ..indexing.index_store import FAISSIndexStore

logger = logging.getLogger(__name__)


class IndexingWorker(QThread):
    """Worker thread for indexing operations."""
    
    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(bool, str)  # success, message
    
    def __init__(self, db_path: Path, folder_path: Path, force_reindex: bool = False):
        super().__init__()
        self.db_path = db_path
        self.folder_path = folder_path
        self.force_reindex = force_reindex
        self._is_running = True
    
    def run(self):
        """Run the indexing process."""
        try:
            db = Database(self.db_path)
            
            # If force reindex, reset all documents to PENDING
            if self.force_reindex:
                self.progress.emit(0, 100, "Resetting documents for re-indexing...")
                reset_count = db.reset_all_documents_to_pending()
                logger.info(f"Reset {reset_count} documents to PENDING status")
            
            # Phase 1: Scan and add documents
            self.progress.emit(0, 100, "Scanning folder...")
            ingestion = Ingestion(db)
            added, updated, errors = ingestion.scan_and_add(
                str(self.folder_path),
                recursive=True
            )
            
            # Check for pending documents (not just newly added/updated)
            pending_docs = ingestion.get_pending_documents()
            total_docs = len(pending_docs)
            
            if total_docs == 0:
                self.finished.emit(True, "No new documents to index")
                return
            
            self.progress.emit(10, 100, f"Found {total_docs} documents to process")
            
            # Phase 2: Extract and chunk
            extractor = Extractor()
            chunker = Chunker(chunk_size=500, chunk_overlap=100)
            
            processed = 0
            
            for doc in pending_docs:
                if not self._is_running:
                    self.finished.emit(False, "Indexing cancelled")
                    return
                
                try:
                    # Extract text
                    extracted_doc = extractor.extract(doc.path)
                    
                    # Chunk text - convert pages to list of tuples
                    page_tuples = [(p.page_number, p.text) for p in extracted_doc.pages]
                    text_chunks = chunker.chunk_pages(page_tuples)
                    
                    # Convert TextChunk to Chunk and add to database
                    import uuid
                    from ..core.models import Chunk
                    
                    for text_chunk in text_chunks:
                        chunk = Chunk(
                            id=str(uuid.uuid4()),
                            document_id=doc.id,
                            page=text_chunk.page_number,
                            start_offset=text_chunk.start_offset,
                            end_offset=text_chunk.end_offset,
                            text=text_chunk.text,
                            text_hash=text_chunk.text_hash
                        )
                        db.add_chunk(chunk)
                    
                    # Update document status
                    doc.status = DocumentStatus.INDEXED
                    db.update_document(doc)
                    
                    processed += 1
                    progress_pct = 10 + int((processed / total_docs) * 70)
                    self.progress.emit(
                        progress_pct,
                        100,
                        f"Processed {processed}/{total_docs}: {doc.title}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing {doc.path}: {e}")
                    doc.status = DocumentStatus.ERROR
                    doc.error_message = str(e)
                    db.update_document(doc)
            
            # Phase 3: Generate embeddings and build FAISS index
            self.progress.emit(80, 100, "Generating embeddings...")
            
            try:
                embedder = Embedder()
                chunks = []
                chunk_texts = []
                
                # Get all chunks
                for doc in db.get_all_documents():
                    if doc.status == DocumentStatus.INDEXED:
                        doc_chunks = db.get_chunks_by_document(doc.id)
                        chunks.extend(doc_chunks)
                        chunk_texts.extend([c.text for c in doc_chunks])
                
                if chunks:
                    # Generate embeddings
                    self.progress.emit(85, 100, f"Embedding {len(chunks)} chunks...")
                    embeddings = embedder.embed_batch(chunk_texts, batch_size=32)
                    
                    # Build FAISS index
                    self.progress.emit(90, 100, "Building search index...")
                    index_store = FAISSIndexStore(
                        dimension=embedder.dimension,
                        index_type='Flat'
                    )
                    chunk_ids = [c.id for c in chunks]
                    index_store.add(chunk_ids, embeddings)
                    
                    # Save index
                    data_dir = self.db_path.parent
                    index_path = data_dir / "embeddings.index"
                    map_path = data_dir / "embeddings.map"
                    index_store.save(index_path, map_path)
                    
                    # Save embedding metadata
                    self.progress.emit(95, 100, "Saving metadata...")
                    from ..core.models import Embedding
                    for i, chunk in enumerate(chunks):
                        embedding = Embedding(
                            chunk_id=chunk.id,
                            vector_id=i,
                            model_name=embedder.model_name,
                            created_at=datetime.now()
                        )
                        db.add_embedding(embedding)
                
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")
                # Continue anyway - keyword search will still work
            
            self.progress.emit(100, 100, "Indexing complete")
            self.finished.emit(
                True,
                f"Indexed {processed} documents with {len(chunks) if chunks else 0} chunks"
            )
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            self.finished.emit(False, f"Indexing failed: {str(e)}")
    
    def stop(self):
        """Stop the worker."""
        self._is_running = False


class LibraryView(QWidget):
    """View for managing document library and indexing."""
    
    status_message = Signal(str)
    
    def __init__(self, db_path: Path):
        super().__init__()
        self.db_path = db_path
        self.db = Database(db_path)
        self.worker = None
        
        self._init_ui()
        self._load_statistics()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Folder management section
        folder_group = QGroupBox("Document Folders")
        folder_layout = QVBoxLayout()
        
        # Folder list
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(150)
        folder_layout.addWidget(self.folder_list)
        
        # Folder buttons
        folder_btn_layout = QHBoxLayout()
        
        self.add_folder_btn = QPushButton("➕ Add Folder")
        self.add_folder_btn.clicked.connect(self._add_folder)
        folder_btn_layout.addWidget(self.add_folder_btn)
        
        self.remove_folder_btn = QPushButton("➖ Remove Folder")
        self.remove_folder_btn.clicked.connect(self._remove_folder)
        folder_btn_layout.addWidget(self.remove_folder_btn)
        
        folder_btn_layout.addStretch()
        folder_layout.addLayout(folder_btn_layout)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Statistics section
        stats_group = QGroupBox("Index Statistics")
        stats_layout = QVBoxLayout()
        
        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels([
            "Metric", "Count", "Last Updated", "Status"
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setMaximumHeight(200)
        stats_layout.addWidget(self.stats_table)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Indexing controls
        index_group = QGroupBox("Indexing")
        index_layout = QVBoxLayout()
        
        # Index buttons
        index_btn_layout = QHBoxLayout()
        
        self.create_index_btn = QPushButton("🔨 Create Index")
        self.create_index_btn.clicked.connect(self._create_index)
        index_btn_layout.addWidget(self.create_index_btn)
        
        self.reindex_btn = QPushButton("🔄 Re-index All")
        self.reindex_btn.clicked.connect(self._reindex_all)
        index_btn_layout.addWidget(self.reindex_btn)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self._cancel_indexing)
        self.cancel_btn.setEnabled(False)
        index_btn_layout.addWidget(self.cancel_btn)
        
        index_btn_layout.addStretch()
        index_layout.addLayout(index_btn_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        index_layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        index_layout.addWidget(self.progress_label)
        
        index_group.setLayout(index_layout)
        layout.addWidget(index_group)
        
        # Error log section
        error_group = QGroupBox("Error Log")
        error_layout = QVBoxLayout()
        
        self.error_log = QTextEdit()
        self.error_log.setReadOnly(True)
        self.error_log.setMaximumHeight(150)
        error_layout.addWidget(self.error_log)
        
        error_group.setLayout(error_layout)
        layout.addWidget(error_group)
        
        layout.addStretch()
    
    def _add_folder(self):
        """Add a folder to the library."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Document Folder",
            str(Path.home())
        )
        
        if folder:
            folder_path = Path(folder)
            
            # Check if already added
            for i in range(self.folder_list.count()):
                if self.folder_list.item(i).text() == str(folder_path):
                    QMessageBox.warning(
                        self,
                        "Duplicate Folder",
                        "This folder is already in the library."
                    )
                    return
            
            self.folder_list.addItem(str(folder_path))
            self.status_message.emit(f"Added folder: {folder_path.name}")
            logger.info(f"Added folder: {folder_path}")
    
    def _remove_folder(self):
        """Remove selected folder from the library."""
        current_item = self.folder_list.currentItem()
        if current_item:
            folder_path = current_item.text()
            
            reply = QMessageBox.question(
                self,
                "Remove Folder",
                f"Remove {folder_path} from library?\n\n"
                "Note: Documents will remain in the index until re-indexed.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.folder_list.takeItem(self.folder_list.currentRow())
                self.status_message.emit(f"Removed folder: {Path(folder_path).name}")
                logger.info(f"Removed folder: {folder_path}")
    
    def _create_index(self):
        """Create index for all folders."""
        if self.folder_list.count() == 0:
            QMessageBox.warning(
                self,
                "No Folders",
                "Please add at least one folder before creating an index."
            )
            return
        
        # Get all folders
        folders = []
        for i in range(self.folder_list.count()):
            folders.append(Path(self.folder_list.item(i).text()))
        
        # Start indexing first folder (can extend to process all)
        self._start_indexing(folders[0])
    
    def _reindex_all(self):
        """Re-index all documents."""
        reply = QMessageBox.question(
            self,
            "Re-index All",
            "This will re-process all documents.\n\n"
            "This may take a while. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes and self.folder_list.count() > 0:
            folder = Path(self.folder_list.item(0).text())
            self._start_indexing(folder, force_reindex=True)
    
    def _start_indexing(self, folder_path: Path, force_reindex: bool = False):
        """Start the indexing process."""
        self.create_index_btn.setEnabled(False)
        self.reindex_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        
        # Create and start worker
        self.worker = IndexingWorker(self.db_path, folder_path, force_reindex)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        
        self.status_message.emit("Indexing started...")
    
    def _cancel_indexing(self):
        """Cancel the indexing process."""
        if self.worker:
            self.worker.stop()
            self.status_message.emit("Cancelling indexing...")
    
    def _on_progress(self, current: int, total: int, message: str):
        """Handle progress updates."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
        logger.debug(f"Progress: {current}/{total} - {message}")
    
    def _on_finished(self, success: bool, message: str):
        """Handle indexing completion."""
        self.create_index_btn.setEnabled(True)
        self.reindex_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Indexing Complete", message)
            self.status_message.emit(message)
        else:
            QMessageBox.warning(self, "Indexing Failed", message)
            self.status_message.emit(f"Error: {message}")
        
        # Reload statistics
        self._load_statistics()
        
        self.worker = None
    
    def _load_statistics(self):
        """Load and display index statistics."""
        try:
            doc_count = self.db.get_document_count()
            chunk_count = self.db.get_chunk_count()
            
            # Get error count
            error_docs = [
                d for d in self.db.get_all_documents()
                if d.status == DocumentStatus.ERROR
            ]
            error_count = len(error_docs)
            
            # Update table
            self.stats_table.setRowCount(4)
            
            # Documents
            self.stats_table.setItem(0, 0, QTableWidgetItem("Documents"))
            self.stats_table.setItem(0, 1, QTableWidgetItem(str(doc_count)))
            self.stats_table.setItem(0, 2, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.stats_table.setItem(0, 3, QTableWidgetItem("✓" if doc_count > 0 else "-"))
            
            # Chunks
            self.stats_table.setItem(1, 0, QTableWidgetItem("Chunks"))
            self.stats_table.setItem(1, 1, QTableWidgetItem(str(chunk_count)))
            self.stats_table.setItem(1, 2, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.stats_table.setItem(1, 3, QTableWidgetItem("✓" if chunk_count > 0 else "-"))
            
            # Errors
            self.stats_table.setItem(2, 0, QTableWidgetItem("Errors"))
            self.stats_table.setItem(2, 1, QTableWidgetItem(str(error_count)))
            self.stats_table.setItem(2, 2, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.stats_table.setItem(2, 3, QTableWidgetItem("⚠" if error_count > 0 else "✓"))
            
            # Embeddings (check if index exists)
            data_dir = self.db_path.parent
            index_exists = (data_dir / "embeddings.index").exists()
            self.stats_table.setItem(3, 0, QTableWidgetItem("Vector Index"))
            self.stats_table.setItem(3, 1, QTableWidgetItem("Ready" if index_exists else "Not created"))
            self.stats_table.setItem(3, 2, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.stats_table.setItem(3, 3, QTableWidgetItem("✓" if index_exists else "-"))
            
            # Update error log
            if error_docs:
                error_text = "Errors during indexing:\n\n"
                for doc in error_docs[:10]:  # Show first 10 errors
                    error_text += f"• {doc.title}\n  {doc.error_message}\n\n"
                if len(error_docs) > 10:
                    error_text += f"... and {len(error_docs) - 10} more errors\n"
                self.error_log.setText(error_text)
            else:
                self.error_log.setText("No errors")
            
        except Exception as e:
            logger.error(f"Error loading statistics: {e}")
            self.error_log.setText(f"Error loading statistics: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
