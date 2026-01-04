"""Text chunking module with overlap and deduplication."""
import hashlib
from typing import List, Tuple
from dataclasses import dataclass

from ..core.tokenizer import get_tokenizer


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    page_number: int
    start_offset: int
    end_offset: int
    text_hash: str
    token_count: int


class Chunker:
    """Handles text chunking with overlap."""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        """Initialize chunker.
        
        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of overlapping tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = get_tokenizer()
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[TextChunk]:
        """Chunk text into overlapping segments.
        
        Args:
            text: Text to chunk
            page_number: Page number for citation
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []
        
        # Tokenize the text
        tokens = self.tokenizer.tokenize(text)
        
        if not tokens:
            return []
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(tokens):
            # Get chunk of tokens
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Find character offsets in original text
            # Calculate approximate character positions based on token positions
            if start_idx == 0:
                start_offset = 0
            else:
                # Use previous chunk's end as our start
                start_offset = chunks[-1].end_offset if chunks else 0
            
            # Calculate end offset - approximate based on average chars per token
            avg_chars_per_token = len(text) / len(tokens) if len(tokens) > 0 else 1
            approx_end = int(start_offset + (len(chunk_tokens) * avg_chars_per_token))
            end_offset = min(approx_end, len(text))
            
            # Extract actual text from original (not reconstructed from tokens)
            chunk_text = text[start_offset:end_offset]
            
            # Generate hash for deduplication
            text_hash = self._generate_hash(chunk_text)
            
            chunk = TextChunk(
                text=chunk_text,
                page_number=page_number,
                start_offset=start_offset,
                end_offset=end_offset,
                text_hash=text_hash,
                token_count=len(chunk_tokens)
            )
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            if end_idx >= len(tokens):
                break
            
            start_idx = end_idx - self.chunk_overlap
            
            # Prevent infinite loop if overlap is too large
            if start_idx <= chunks[-1].start_offset if chunks else 0:
                start_idx = end_idx
        
        return chunks
    
    def chunk_pages(self, pages: List[Tuple[int, str]]) -> List[TextChunk]:
        """Chunk multiple pages while preserving page numbers.
        
        Args:
            pages: List of (page_number, text) tuples
            
        Returns:
            List of TextChunk objects from all pages
        """
        all_chunks = []
        
        for page_num, text in pages:
            page_chunks = self.chunk_text(text, page_number=page_num)
            all_chunks.extend(page_chunks)
        
        return all_chunks
    
    def deduplicate_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Remove duplicate chunks based on hash.
        
        Args:
            chunks: List of chunks to deduplicate
            
        Returns:
            List of unique chunks (first occurrence kept)
        """
        seen_hashes = set()
        unique_chunks = []
        
        for chunk in chunks:
            if chunk.text_hash not in seen_hashes:
                seen_hashes.add(chunk.text_hash)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def _generate_hash(self, text: str) -> str:
        """Generate SHA256 hash of text.
        
        Args:
            text: Text to hash
            
        Returns:
            Hex string of hash
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
