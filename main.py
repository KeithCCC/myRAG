"""Main entry point for Folder RAG application."""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import Database
from src.core.config import Config


def main():
    """Initialize and verify the application setup."""
    print("=" * 50)
    print("Folder RAG - Local Document Search")
    print("=" * 50)
    print()
    
    # Initialize database
    print("Initializing database...")
    db = Database()
    print(f"✓ Database created at: {db.db_path}")
    print()
    
    # Initialize configuration
    print("Loading configuration...")
    config = Config(db)
    settings = config.get_settings()
    print(f"✓ Embedding model: {settings.embedding_model}")
    print(f"✓ Chunk size: {settings.chunk_size}")
    print(f"✓ Allowed extensions: {', '.join(settings.allowed_ext)}")
    print(f"✓ Generation mode: {settings.generation_mode.value}")
    print()
    
    # Verify database tables
    print("Verifying database schema...")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['documents', 'chunks', 'embeddings', 'index_jobs', 'settings', 'chunks_fts']
        for table in expected_tables:
            if table in tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' missing!")
    
    print()
    print("=" * 50)
    print("Phase 1 Setup Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Run tests: pytest tests/")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Continue to Phase 2: File ingestion")


if __name__ == "__main__":
    main()
