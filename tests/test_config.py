"""Tests for configuration management."""
import pytest
import tempfile
import os

from src.core.database import Database
from src.core.config import Config
from src.core.models import GenerationMode


@pytest.fixture
def temp_config():
    """Create a temporary config for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        config = Config(db)
        yield config


def test_default_settings(temp_config):
    """Test that default settings are returned when none exist."""
    settings = temp_config.get_settings()
    
    assert settings.included_paths == []
    assert settings.allowed_ext == Config.DEFAULT_ALLOWED_EXT
    assert settings.embedding_model == Config.DEFAULT_EMBEDDING_MODEL
    assert settings.chunk_size == Config.DEFAULT_CHUNK_SIZE
    assert settings.chunk_overlap == Config.DEFAULT_CHUNK_OVERLAP
    assert settings.top_k == Config.DEFAULT_TOP_K
    assert settings.generation_mode == Config.DEFAULT_GENERATION_MODE


def test_save_and_load_settings(temp_config):
    """Test saving and loading settings."""
    settings = temp_config.get_settings()
    settings.included_paths = ['/test/path1', '/test/path2']
    settings.allowed_ext = ['.pdf', '.txt']
    settings.chunk_size = 1000
    settings.top_k = 20
    
    temp_config.save_settings(settings)
    
    loaded = temp_config.get_settings()
    assert loaded.included_paths == ['/test/path1', '/test/path2']
    assert loaded.allowed_ext == ['.pdf', '.txt']
    assert loaded.chunk_size == 1000
    assert loaded.top_k == 20


def test_add_included_path(temp_config):
    """Test adding a path to included paths."""
    temp_config.add_included_path('/test/path1')
    settings = temp_config.get_settings()
    assert '/test/path1' in settings.included_paths
    
    # Adding same path again shouldn't duplicate
    temp_config.add_included_path('/test/path1')
    settings = temp_config.get_settings()
    assert settings.included_paths.count('/test/path1') == 1


def test_remove_included_path(temp_config):
    """Test removing a path from included paths."""
    temp_config.add_included_path('/test/path1')
    temp_config.add_included_path('/test/path2')
    
    temp_config.remove_included_path('/test/path1')
    settings = temp_config.get_settings()
    
    assert '/test/path1' not in settings.included_paths
    assert '/test/path2' in settings.included_paths


def test_validate_settings_chunk_size(temp_config):
    """Test validation of chunk size."""
    settings = temp_config.get_settings()
    
    # Too small
    settings.chunk_size = 50
    errors = temp_config.validate_settings(settings)
    assert any('Chunk size must be at least 100' in e for e in errors)
    
    # Too large
    settings.chunk_size = 3000
    errors = temp_config.validate_settings(settings)
    assert any('Chunk size must be at most 2000' in e for e in errors)
    
    # Valid
    settings.chunk_size = 800
    errors = temp_config.validate_settings(settings)
    assert not any('chunk size' in e.lower() for e in errors)


def test_validate_settings_chunk_overlap(temp_config):
    """Test validation of chunk overlap."""
    settings = temp_config.get_settings()
    
    # Negative overlap
    settings.chunk_overlap = -10
    errors = temp_config.validate_settings(settings)
    assert any('overlap cannot be negative' in e for e in errors)
    
    # Overlap >= chunk size
    settings.chunk_size = 500
    settings.chunk_overlap = 500
    errors = temp_config.validate_settings(settings)
    assert any('overlap must be less than chunk size' in e for e in errors)
    
    # Valid
    settings.chunk_overlap = 100
    errors = temp_config.validate_settings(settings)
    assert not any('overlap' in e.lower() for e in errors)


def test_validate_settings_top_k(temp_config):
    """Test validation of top_k."""
    settings = temp_config.get_settings()
    
    # Too small
    settings.top_k = 0
    errors = temp_config.validate_settings(settings)
    assert any('Top K must be at least 1' in e for e in errors)
    
    # Too large
    settings.top_k = 150
    errors = temp_config.validate_settings(settings)
    assert any('Top K must be at most 100' in e for e in errors)
    
    # Valid
    settings.top_k = 10
    errors = temp_config.validate_settings(settings)
    assert not any('top k' in e.lower() for e in errors)


def test_validate_settings_allowed_ext(temp_config):
    """Test validation of allowed extensions."""
    settings = temp_config.get_settings()
    
    # Empty extensions
    settings.allowed_ext = []
    errors = temp_config.validate_settings(settings)
    assert any('at least one file extension' in e.lower() for e in errors)
    
    # Valid
    settings.allowed_ext = ['.pdf']
    errors = temp_config.validate_settings(settings)
    assert not any('extension' in e.lower() for e in errors)


def test_validate_settings_openai_key(temp_config):
    """Test validation of OpenAI API key requirement."""
    settings = temp_config.get_settings()
    
    # OpenAI mode without API key
    settings.generation_mode = GenerationMode.OPENAI
    settings.openai_api_key = None
    errors = temp_config.validate_settings(settings)
    assert any('OpenAI API key is required' in e for e in errors)
    
    # OpenAI mode with API key
    settings.openai_api_key = 'sk-test123'
    errors = temp_config.validate_settings(settings)
    assert not any('api key' in e.lower() for e in errors)
    
    # None mode doesn't require API key
    settings.generation_mode = GenerationMode.NONE
    settings.openai_api_key = None
    errors = temp_config.validate_settings(settings)
    assert not any('api key' in e.lower() for e in errors)


def test_validate_all_valid_settings(temp_config):
    """Test that valid settings pass validation."""
    settings = temp_config.get_settings()
    settings.chunk_size = 800
    settings.chunk_overlap = 150
    settings.top_k = 10
    settings.allowed_ext = ['.pdf', '.txt', '.md']
    settings.generation_mode = GenerationMode.NONE
    
    errors = temp_config.validate_settings(settings)
    assert len(errors) == 0
