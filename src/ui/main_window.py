"""Main window for the RAG application."""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from pathlib import Path
import logging

from .library_view import LibraryView
from .search_view import SearchView
from .ask_view import AskView

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""
    
    # Signals
    status_message = Signal(str)
    
    def __init__(self, db_path: Path):
        """Initialize the main window.
        
        Args:
            db_path: Path to the SQLite database
        """
        super().__init__()
        
        self.db_path = db_path
        
        self.setWindowTitle("myRAG - Local Document Search")
        self.setMinimumSize(1200, 800)
        
        # Create UI components
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
        # Connect signals
        self.status_message.connect(self.show_status_message)
        
        logger.info("Main window initialized")
    
    def _create_menu_bar(self):
        """Create the menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Settings action
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        # About action
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # Documentation action
        docs_action = QAction("&Documentation", self)
        docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(docs_action)
    
    def _create_central_widget(self):
        """Create the central widget with tabs."""
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Create views
        self.library_view = LibraryView(self.db_path)
        self.search_view = SearchView(self.db_path)
        self.ask_view = AskView(self.db_path)
        
        # Add tabs
        self.tab_widget.addTab(self.library_view, "📚 Library")
        self.tab_widget.addTab(self.search_view, "🔍 Search")
        self.tab_widget.addTab(self.ask_view, "💬 Ask")
        
        # Connect view signals to status bar
        self.library_view.status_message.connect(self.show_status_message)
        self.search_view.status_message.connect(self.show_status_message)
        self.ask_view.status_message.connect(self.show_status_message)
        
        # Set central widget
        self.setCentralWidget(self.tab_widget)
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def show_status_message(self, message: str, timeout: int = 5000):
        """Show a message in the status bar.
        
        Args:
            message: Message to display
            timeout: Timeout in milliseconds (0 for permanent)
        """
        self.status_bar.showMessage(message, timeout)
        logger.info(f"Status: {message}")
    
    def _show_settings(self):
        """Show settings dialog."""
        QMessageBox.information(
            self,
            "Settings",
            "Settings dialog will be implemented in a future update."
        )
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>myRAG</h2>
        <p>Local document search and retrieval system</p>
        <p><b>Version:</b> 1.0.0 (Phase 4)</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Document indexing (PDF, TXT, MD)</li>
            <li>Japanese text support with MeCab</li>
            <li>Keyword search (FTS5)</li>
            <li>Semantic search (embeddings + FAISS)</li>
            <li>Hybrid search</li>
        </ul>
        <p><b>Tech Stack:</b> Python, PySide6, SQLite, sentence-transformers, FAISS</p>
        """
        QMessageBox.about(self, "About myRAG", about_text)
    
    def _show_documentation(self):
        """Show documentation."""
        docs_text = """
        <h3>Quick Start</h3>
        <ol>
            <li><b>Library Tab:</b> Add folders containing documents (PDF, TXT, MD)</li>
            <li>Click "Create Index" to process documents</li>
            <li><b>Search Tab:</b> Search your documents using:
                <ul>
                    <li><b>Keyword:</b> Traditional full-text search</li>
                    <li><b>Semantic:</b> AI-powered meaning-based search</li>
                    <li><b>Hybrid:</b> Combines both methods</li>
                </ul>
            </li>
            <li><b>Ask Tab:</b> (Phase 5) Ask questions and get AI-generated answers</li>
        </ol>
        <p>See README.md for detailed documentation.</p>
        """
        QMessageBox.information(self, "Documentation", docs_text)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up resources
        self.library_view.cleanup()
        self.search_view.cleanup()
        self.ask_view.cleanup()
        
        event.accept()
        logger.info("Application closed")
