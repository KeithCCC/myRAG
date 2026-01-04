"""Main application entry point for myRAG UI."""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ui.main_window import MainWindow
from src.core.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('myrag.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Run the application."""
    try:
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("myRAG")
        app.setOrganizationName("myRAG")
        
        # Set application style
        app.setStyle("Fusion")
        
        # Database path
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "folderrag.db"
        
        # Initialize database if needed
        logger.info(f"Database: {db_path}")
        db = Database(db_path)
        logger.info("Database initialized")
        
        # Create and show main window
        window = MainWindow(db_path)
        window.show()
        
        logger.info("Application started")
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
