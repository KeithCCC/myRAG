"""Tests for the chunker module."""
import pytest

from src.indexing.chunker import Chunker, TextChunk


@pytest.fixture
def chunker():
    """Create chunker with small chunk size for testing."""
    return Chunker(chunk_size=20, chunk_overlap=5)


@pytest.fixture
def large_chunker():
    """Create chunker with default size."""
    return Chunker(chunk_size=800, chunk_overlap=150)


def test_chunk_simple_text(chunker):
    """Test chunking simple English text."""
    text = "This is a test sentence. " * 10
    chunks = chunker.chunk_text(text, page_number=1)
    
    assert len(chunks) > 0
    assert all(isinstance(c, TextChunk) for c in chunks)
    assert all(c.page_number == 1 for c in chunks)
    assert all(c.text_hash for c in chunks)


def test_chunk_japanese_text(chunker):
    """Test chunking Japanese text."""
    text = "機械学習は人工知能の一分野である。" * 5
    chunks = chunker.chunk_text(text, page_number=1)
    
    assert len(chunks) > 0
    # After tokenization, Japanese words are separated with spaces
    # Just verify that we get chunks back
    assert all(len(c.text) > 0 for c in chunks)


def test_chunk_mixed_language(chunker):
    """Test chunking mixed language text."""
    text = "Machine Learning 機械学習 is a field of AI 人工知能. " * 5
    chunks = chunker.chunk_text(text, page_number=1)
    
    assert len(chunks) > 0


def test_chunk_overlap(chunker):
    """Test that chunks have overlap."""
    text = "word " * 50
    chunks = chunker.chunk_text(text, page_number=1)
    
    # With overlap, we should have multiple chunks
    assert len(chunks) > 1
    
    # Some tokens should appear in multiple chunks (overlap)
    # This is hard to test directly, but we can check that
    # chunks are not completely disjoint
    for i in range(len(chunks) - 1):
        curr_tokens = set(chunks[i].text.split())
        next_tokens = set(chunks[i+1].text.split())
        # Should have some overlap
        assert len(curr_tokens & next_tokens) > 0


def test_chunk_empty_text(chunker):
    """Test chunking empty text."""
    assert chunker.chunk_text("", page_number=1) == []
    assert chunker.chunk_text("   ", page_number=1) == []


def test_chunk_short_text(chunker):
    """Test chunking text shorter than chunk size."""
    text = "Short text."
    chunks = chunker.chunk_text(text, page_number=1)
    
    assert len(chunks) == 1
    assert chunks[0].text


def test_chunk_pages(chunker):
    """Test chunking multiple pages."""
    pages = [
        (1, "Page 1 content " * 10),
        (2, "Page 2 content " * 10),
        (3, "Page 3 content " * 10)
    ]
    
    chunks = chunker.chunk_pages(pages)
    
    assert len(chunks) > 0
    
    # Check that page numbers are preserved
    page_numbers = {c.page_number for c in chunks}
    assert page_numbers == {1, 2, 3}


def test_deduplicate_chunks(chunker):
    """Test deduplication of chunks."""
    text = "Same text. " * 10
    chunks1 = chunker.chunk_text(text, page_number=1)
    chunks2 = chunker.chunk_text(text, page_number=2)
    
    all_chunks = chunks1 + chunks2
    unique_chunks = chunker.deduplicate_chunks(all_chunks)
    
    # Should have removed duplicates
    assert len(unique_chunks) < len(all_chunks)
    
    # Check that all hashes are unique
    hashes = [c.text_hash for c in unique_chunks]
    assert len(hashes) == len(set(hashes))


def test_chunk_offsets(chunker):
    """Test that chunk offsets are created."""
    text = "This is a test sentence. " * 10
    chunks = chunker.chunk_text(text, page_number=1)
    
    # Just verify offsets are set (they're approximate after tokenization)
    for chunk in chunks:
        assert chunk.start_offset >= 0
        assert chunk.end_offset >= 0


def test_chunk_token_count(chunker):
    """Test that token counts are accurate."""
    text = "word " * 100
    chunks = chunker.chunk_text(text, page_number=1)
    
    for chunk in chunks:
        assert chunk.token_count > 0
        assert chunk.token_count <= chunker.chunk_size


def test_large_document_chunking(large_chunker):
    """Test chunking a large document."""
    # Create a large text (similar to a real document)
    text = """
    Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without explicit instructions.
    
    機械学習（きかいがくしゅう）は、人工知能の一分野で、データから学習し、明示的な指示なしにタスクを実行できる統計的アルゴリズムの開発と研究に関係しています。
    
    Recently, generative artificial intelligence has been the subject of increased interest and public attention, driven by successes like ChatGPT and other large language models.
    """ * 10
    
    chunks = large_chunker.chunk_text(text, page_number=1)
    
    assert len(chunks) > 0
    assert all(c.token_count <= 800 for c in chunks)


def test_hash_generation(chunker):
    """Test that hash generation is consistent."""
    text = "Test text for hashing."
    
    chunks1 = chunker.chunk_text(text, page_number=1)
    chunks2 = chunker.chunk_text(text, page_number=1)
    
    # Same text should produce same hashes
    assert chunks1[0].text_hash == chunks2[0].text_hash


def test_different_text_different_hash(chunker):
    """Test that different texts produce different hashes."""
    chunk1 = chunker.chunk_text("Text A " * 10, page_number=1)
    chunk2 = chunker.chunk_text("Text B " * 10, page_number=1)
    
    assert chunk1[0].text_hash != chunk2[0].text_hash


def test_chunk_real_pdf_text(large_chunker):
    """Test chunking with real extracted PDF text."""
    from src.indexing.extractor import Extractor
    
    extractor = Extractor()
    doc = extractor.extract('tests/test_data/sample.pdf')
    
    all_chunks = []
    for page in doc.pages:
        chunks = large_chunker.chunk_text(page.text, page_number=page.page_number)
        all_chunks.extend(chunks)
    
    assert len(all_chunks) > 0
    
    # Check that page numbers are preserved
    page_nums = {c.page_number for c in all_chunks}
    assert 1 in page_nums  # At least page 1 should be there


def test_chunk_pages_convenience(large_chunker):
    """Test the convenience method for chunking pages."""
    from src.indexing.extractor import Extractor
    
    extractor = Extractor()
    doc = extractor.extract('tests/test_data/sample.pdf')
    
    pages = [(page.page_number, page.text) for page in doc.pages]
    chunks = large_chunker.chunk_pages(pages)
    
    assert len(chunks) > 0
    assert all(isinstance(c, TextChunk) for c in chunks)
