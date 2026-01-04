"""Ask view for RAG-based question answering (Phase 5)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from pathlib import Path
import logging

from ..core.database import Database

logger = logging.getLogger(__name__)


class AskView(QWidget):
    """View for asking questions and getting AI-generated answers."""
    
    status_message = Signal(str)
    
    def __init__(self, db_path: Path):
        super().__init__()
        self.db_path = db_path
        self.db = Database(db_path)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Placeholder message
        placeholder_group = QGroupBox("Ask - Coming in Phase 5")
        placeholder_layout = QVBoxLayout()
        
        info_label = QLabel(
            "<h3>🚧 Question Answering Feature</h3>"
            "<p>This feature will be implemented in Phase 5.</p>"
            "<p><b>Planned capabilities:</b></p>"
            "<ul>"
            "<li>Ask natural language questions about your documents</li>"
            "<li>Get AI-generated answers with citations</li>"
            "<li>Two modes:"
            "<ul>"
            "<li><b>No-Generation:</b> Extract key points from top chunks</li>"
            "<li><b>OpenAI:</b> GPT-powered answers with source citations</li>"
            "</ul>"
            "</li>"
            "<li>View source chunks used to generate answers</li>"
            "<li>Copy answers to clipboard</li>"
            "</ul>"
            "<p><b>Current Status:</b></p>"
            "<ul>"
            "<li>✅ Phase 1: Project Setup & Database</li>"
            "<li>✅ Phase 2: Indexing Pipeline</li>"
            "<li>✅ Phase 3: Search Foundation</li>"
            "<li>✅ Phase 4: Basic UI (Current)</li>"
            "<li>⏳ Phase 5: RAG/Answer Generation (Next)</li>"
            "</ul>"
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        placeholder_layout.addWidget(info_label)
        placeholder_layout.addStretch()
        
        placeholder_group.setLayout(placeholder_layout)
        layout.addWidget(placeholder_group)
    
    def cleanup(self):
        """Clean up resources."""
        pass
