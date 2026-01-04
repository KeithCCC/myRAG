"""Data models for the RAG application."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class DocumentStatus(Enum):
    """Status of document indexing."""
    PENDING = "pending"
    INDEXED = "indexed"
    ERROR = "error"


class GenerationMode(Enum):
    """Mode for answer generation."""
    NONE = "none"
    OPENAI = "openai"


@dataclass
class Document:
    """Represents a document in the system."""
    id: str
    path: str
    title: str
    ext: str
    mtime: datetime
    size: int
    status: DocumentStatus
    error_message: Optional[str] = None


@dataclass
class Chunk:
    """Represents a text chunk from a document."""
    id: str
    document_id: str
    page: Optional[int]
    start_offset: int
    end_offset: int
    text: str
    text_hash: str


@dataclass
class Embedding:
    """Represents an embedding vector for a chunk."""
    chunk_id: str
    vector_id: int
    model_name: str
    created_at: datetime


@dataclass
class IndexJob:
    """Represents an indexing job."""
    id: str
    target_path: str
    started_at: datetime
    finished_at: Optional[datetime]
    total: int
    done: int
    error_count: int
    log: str


@dataclass
class Settings:
    """Application settings."""
    included_paths: list[str]
    allowed_ext: list[str]
    embedding_model: str
    generation_mode: GenerationMode
    openai_api_key: Optional[str]
    chunk_size: int
    chunk_overlap: int
    top_k: int


@dataclass
class SearchResult:
    """Represents a search result with citation."""
    chunk_id: str
    document_id: str
    document_name: str
    document_path: str
    page: Optional[int]
    snippet: str
    full_text: str
    score: float
