"""Search view for querying documents."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTabWidget, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QGroupBox, QSplitter, QMessageBox,
    QFileDialog
)
from PySide6.QtCore import Qt, Signal
from pathlib import Path
import logging
from datetime import datetime

from ..core.database import Database
from ..indexing.embedder import Embedder
from ..indexing.index_store import FAISSIndexStore
from ..search.retriever import Retriever, SearchResult

logger = logging.getLogger(__name__)


class SearchView(QWidget):
    """View for searching documents."""
    
    status_message = Signal(str)
    
    def __init__(self, db_path: Path):
        super().__init__()
        self.db_path = db_path
        self.db = Database(db_path)
        self.retriever = None
        self.current_results = []
        
        self._init_retriever()
        self._init_ui()
    
    def _init_retriever(self):
        """Initialize the retriever with embedder and index if available."""
        try:
            # Check if FAISS index exists
            data_dir = self.db_path.parent
            index_path = data_dir / "embeddings.index"
            map_path = data_dir / "embeddings.map"
            
            if index_path.exists() and map_path.exists():
                # Load embedder and FAISS index
                embedder = Embedder()
                index_store = FAISSIndexStore(
                    dimension=embedder.dimension,
                    index_type='Flat'
                )
                index_store.load(index_path, map_path)
                
                self.retriever = Retriever(
                    db=self.db,
                    embedder=embedder,
                    index_store=index_store
                )
                logger.info("Retriever initialized with semantic search")
            else:
                # Keyword-only retriever
                self.retriever = Retriever(db=self.db)
                logger.info("Retriever initialized (keyword-only)")
                
        except Exception as e:
            logger.error(f"Error initializing retriever: {e}")
            self.retriever = Retriever(db=self.db)
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Search input section
        search_group = QGroupBox("Search Query")
        search_layout = QVBoxLayout()
        
        # Search input
        input_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter your search query...")
        self.search_input.returnPressed.connect(self._perform_search)
        input_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.clicked.connect(self._perform_search)
        input_layout.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self._clear_search)
        input_layout.addWidget(self.clear_btn)
        
        search_layout.addLayout(input_layout)
        
        # Search mode tabs
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setMaximumHeight(35)
        self.mode_tabs.addTab(QWidget(), "🔤 Keyword")
        self.mode_tabs.addTab(QWidget(), "🧠 Semantic")
        self.mode_tabs.addTab(QWidget(), "⚡ Hybrid")
        
        search_layout.addWidget(self.mode_tabs)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Results section (split view)
        splitter = QSplitter(Qt.Horizontal)
        
        # Results list
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_result_selected)
        results_layout.addWidget(self.results_list)
        
        # Export button
        export_layout = QHBoxLayout()
        
        self.result_count_label = QLabel("No results")
        export_layout.addWidget(self.result_count_label)
        
        export_layout.addStretch()
        
        self.export_btn = QPushButton("💾 Export Results")
        self.export_btn.clicked.connect(self._export_results)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        results_layout.addLayout(export_layout)
        
        results_group.setLayout(results_layout)
        splitter.addWidget(results_group)
        
        # Preview pane
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Select a result to preview...")
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        splitter.addWidget(preview_group)
        
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        # Check retriever capabilities
        self._update_mode_tabs()
    
    def _update_mode_tabs(self):
        """Update available search mode tabs based on retriever capabilities."""
        has_semantic = (
            self.retriever and 
            self.retriever.embedder is not None and 
            self.retriever.index_store is not None
        )
        
        # Enable/disable tabs
        self.mode_tabs.setTabEnabled(1, has_semantic)  # Semantic
        self.mode_tabs.setTabEnabled(2, has_semantic)  # Hybrid
        
        if not has_semantic:
            self.mode_tabs.setTabText(
                1,
                "🧠 Semantic (Index Required)"
            )
            self.mode_tabs.setTabText(
                2,
                "⚡ Hybrid (Index Required)"
            )
            self.mode_tabs.setCurrentIndex(0)  # Default to keyword
    
    def _perform_search(self):
        """Perform search based on selected mode."""
        query = self.search_input.text().strip()
        
        if not query:
            QMessageBox.warning(
                self,
                "Empty Query",
                "Please enter a search query."
            )
            return
        
        # Get search mode
        mode_index = self.mode_tabs.currentIndex()
        mode_names = ['keyword', 'semantic', 'hybrid']
        mode = mode_names[mode_index]
        
        try:
            # Perform search
            self.status_message.emit(f"Searching ({mode})...")
            
            if mode == 'keyword':
                results = self.retriever.keyword_search(query, limit=20)
            elif mode == 'semantic':
                results = self.retriever.semantic_search(query, limit=20)
            else:  # hybrid
                results = self.retriever.hybrid_search(query, limit=20)
            
            self.current_results = results
            self._display_results(results, query)
            
            self.status_message.emit(
                f"Found {len(results)} results ({mode} search)"
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Search Error",
                f"An error occurred during search:\n{str(e)}"
            )
            self.status_message.emit("Search failed")
    
    def _display_results(self, results: list[SearchResult], query: str):
        """Display search results in the list."""
        self.results_list.clear()
        
        if not results:
            self.result_count_label.setText("No results found")
            self.export_btn.setEnabled(False)
            return
        
        self.result_count_label.setText(f"{len(results)} results")
        self.export_btn.setEnabled(True)
        
        for result in results:
            # Get document info
            doc = self.db.get_document(result.chunk.document_id)
            if not doc:
                continue
            
            # Create result item
            item_text = f"#{result.rank} {doc.title}"
            if result.chunk.page:
                item_text += f" (p.{result.chunk.page})"
            item_text += f" | Score: {result.score:.3f}"
            
            # Add snippet
            snippet = self.retriever.format_result_snippet(
                result.chunk,
                query,
                snippet_length=150
            )
            
            item = QListWidgetItem(f"{item_text}\n{snippet}")
            item.setData(Qt.UserRole, result)
            self.results_list.addItem(item)
    
    def _on_result_selected(self, item: QListWidgetItem):
        """Handle result selection."""
        result: SearchResult = item.data(Qt.UserRole)
        if not result:
            return
        
        # Get document
        doc = self.db.get_document(result.chunk.document_id)
        if not doc:
            self.preview_text.setText("Document not found")
            return
        
        # Build preview
        preview = f"<h3>{doc.title}</h3>\n"
        preview += f"<p><b>Path:</b> {doc.path}</p>\n"
        
        if result.chunk.page:
            preview += f"<p><b>Page:</b> {result.chunk.page}</p>\n"
        
        preview += f"<p><b>Score:</b> {result.score:.3f}</p>\n"
        preview += f"<p><b>Rank:</b> #{result.rank}</p>\n"
        
        preview += "<hr>\n"
        preview += "<h4>Text Content:</h4>\n"
        preview += f"<p>{result.chunk.text}</p>"
        
        self.preview_text.setHtml(preview)
    
    def _clear_search(self):
        """Clear search input and results."""
        self.search_input.clear()
        self.results_list.clear()
        self.preview_text.clear()
        self.current_results = []
        self.result_count_label.setText("No results")
        self.export_btn.setEnabled(False)
        self.status_message.emit("Search cleared")
    
    def _export_results(self):
        """Export search results to a file."""
        if not self.current_results:
            return
        
        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            str(Path.home() / f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Build export content
            query = self.search_input.text()
            mode_names = ['Keyword', 'Semantic', 'Hybrid']
            mode = mode_names[self.mode_tabs.currentIndex()]
            
            content = f"Search Results\n"
            content += f"{'=' * 80}\n\n"
            content += f"Query: {query}\n"
            content += f"Mode: {mode}\n"
            content += f"Results: {len(self.current_results)}\n"
            content += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"{'=' * 80}\n\n"
            
            for result in self.current_results:
                doc = self.db.get_document(result.chunk.document_id)
                if not doc:
                    continue
                
                content += f"#{result.rank} | Score: {result.score:.3f}\n"
                content += f"Document: {doc.title}\n"
                content += f"Path: {doc.path}\n"
                
                if result.chunk.page:
                    content += f"Page: {result.chunk.page}\n"
                
                content += f"\n{result.chunk.text}\n"
                content += f"\n{'-' * 80}\n\n"
            
            # Write to file
            Path(file_path).write_text(content, encoding='utf-8')
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Results exported to:\n{file_path}"
            )
            self.status_message.emit(f"Exported {len(self.current_results)} results")
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export results:\n{str(e)}"
            )
    
    def cleanup(self):
        """Clean up resources."""
        pass
