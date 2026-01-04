"""Configuration management for the RAG application."""
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import os

from .database import Database
from .models import Settings, GenerationMode


class Config:
    """Application configuration manager."""
    
    # Default settings
    DEFAULT_ALLOWED_EXT = ['.pdf', '.txt', '.md']
    DEFAULT_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    DEFAULT_CHUNK_SIZE = 800
    DEFAULT_CHUNK_OVERLAP = 150
    DEFAULT_TOP_K = 10
    DEFAULT_GENERATION_MODE = GenerationMode.NONE
    
    def __init__(self, db: Database):
        """Initialize configuration manager.
        
        Args:
            db: Database instance
        """
        self.db = db
        load_dotenv()
    
    def get_settings(self) -> Settings:
        """Load settings from database or return defaults."""
        included_paths = self.db.get_setting('included_paths', [])
        allowed_ext = self.db.get_setting('allowed_ext', self.DEFAULT_ALLOWED_EXT)
        embedding_model = self.db.get_setting('embedding_model', self.DEFAULT_EMBEDDING_MODEL)
        generation_mode_str = self.db.get_setting('generation_mode', self.DEFAULT_GENERATION_MODE.value)
        chunk_size = self.db.get_setting('chunk_size', self.DEFAULT_CHUNK_SIZE)
        chunk_overlap = self.db.get_setting('chunk_overlap', self.DEFAULT_CHUNK_OVERLAP)
        top_k = self.db.get_setting('top_k', self.DEFAULT_TOP_K)
        
        # Get OpenAI API key from environment or database
        openai_api_key = os.getenv('OPENAI_API_KEY') or self.db.get_setting('openai_api_key')
        
        return Settings(
            included_paths=included_paths,
            allowed_ext=allowed_ext,
            embedding_model=embedding_model,
            generation_mode=GenerationMode(generation_mode_str),
            openai_api_key=openai_api_key,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=top_k
        )
    
    def save_settings(self, settings: Settings) -> None:
        """Save settings to database.
        
        Args:
            settings: Settings object to save
        """
        self.db.save_setting('included_paths', settings.included_paths)
        self.db.save_setting('allowed_ext', settings.allowed_ext)
        self.db.save_setting('embedding_model', settings.embedding_model)
        self.db.save_setting('generation_mode', settings.generation_mode.value)
        self.db.save_setting('chunk_size', settings.chunk_size)
        self.db.save_setting('chunk_overlap', settings.chunk_overlap)
        self.db.save_setting('top_k', settings.top_k)
        
        # Only save API key to database if provided
        if settings.openai_api_key:
            self.db.save_setting('openai_api_key', settings.openai_api_key)
    
    def add_included_path(self, path: str) -> None:
        """Add a path to included paths."""
        settings = self.get_settings()
        if path not in settings.included_paths:
            settings.included_paths.append(path)
            self.save_settings(settings)
    
    def remove_included_path(self, path: str) -> None:
        """Remove a path from included paths."""
        settings = self.get_settings()
        if path in settings.included_paths:
            settings.included_paths.remove(path)
            self.save_settings(settings)
    
    def validate_settings(self, settings: Settings) -> list[str]:
        """Validate settings and return list of errors.
        
        Args:
            settings: Settings to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if settings.chunk_size < 100:
            errors.append("Chunk size must be at least 100 tokens")
        
        if settings.chunk_size > 2000:
            errors.append("Chunk size must be at most 2000 tokens")
        
        if settings.chunk_overlap < 0:
            errors.append("Chunk overlap cannot be negative")
        
        if settings.chunk_overlap >= settings.chunk_size:
            errors.append("Chunk overlap must be less than chunk size")
        
        if settings.top_k < 1:
            errors.append("Top K must be at least 1")
        
        if settings.top_k > 100:
            errors.append("Top K must be at most 100")
        
        if not settings.allowed_ext:
            errors.append("At least one file extension must be allowed")
        
        if settings.generation_mode == GenerationMode.OPENAI and not settings.openai_api_key:
            errors.append("OpenAI API key is required for OpenAI generation mode")
        
        return errors
