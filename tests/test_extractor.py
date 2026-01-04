"""Tests for the extractor module."""
import pytest
from pathlib import Path

from src.indexing.extractor import Extractor, ExtractedDocument, ExtractedPage


@pytest.fixture
def extractor():
    """Create extractor instance."""
    return Extractor()


def test_extract_txt(extractor):
    """Test extracting text from TXT file."""
    txt_path = 'tests/test_data/sample.txt'
    doc = extractor.extract(txt_path)
    
    assert isinstance(doc, ExtractedDocument)
    assert doc.file_path == txt_path
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    assert 'test text file' in doc.pages[0].text.lower()
    assert '機械学習' in doc.pages[0].text
    assert doc.total_chars > 0


def test_extract_md(extractor):
    """Test extracting text from MD file."""
    md_path = 'tests/test_data/sample.md'
    doc = extractor.extract(md_path)
    
    assert isinstance(doc, ExtractedDocument)
    assert len(doc.pages) == 1
    assert 'Test Markdown File' in doc.pages[0].text
    assert '機械学習' in doc.pages[0].text
    assert 'hello_world' in doc.pages[0].text


def test_extract_pdf(extractor):
    """Test extracting text from PDF file."""
    pdf_path = 'tests/test_data/sample.pdf'
    doc = extractor.extract(pdf_path)
    
    assert isinstance(doc, ExtractedDocument)
    assert len(doc.pages) == 3
    
    # Check page numbers
    assert doc.pages[0].page_number == 1
    assert doc.pages[1].page_number == 2
    assert doc.pages[2].page_number == 3
    
    # Check content
    assert 'Page 1' in doc.pages[0].text
    assert 'Page 2' in doc.pages[1].text
    assert 'Page 3' in doc.pages[2].text
    assert 'Machine Learning' in doc.pages[0].text


def test_extract_pdf_page_details(extractor):
    """Test PDF page extraction details."""
    pdf_path = 'tests/test_data/sample.pdf'
    doc = extractor.extract(pdf_path)
    
    # Check each page has char count
    for page in doc.pages:
        assert page.char_count > 0
        assert page.char_count == len(page.text)
    
    # Check total chars
    expected_total = sum(p.char_count for p in doc.pages)
    assert doc.total_chars == expected_total


def test_extract_nonexistent_file(extractor):
    """Test extracting from nonexistent file."""
    with pytest.raises(FileNotFoundError):
        extractor.extract('/nonexistent/file.pdf')


def test_extract_unsupported_format(extractor):
    """Test extracting unsupported format."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as f:
        f.write(b'test')
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match='Unsupported file format'):
            extractor.extract(temp_path)
    finally:
        Path(temp_path).unlink()


def test_extract_with_error_handling(extractor):
    """Test extraction with error handling."""
    # Valid file
    doc, error = extractor.extract_with_error_handling('tests/test_data/sample.txt')
    assert doc is not None
    assert error is None
    
    # Invalid file
    doc, error = extractor.extract_with_error_handling('/nonexistent/file.txt')
    assert doc is None
    assert error is not None
    assert 'not found' in error.lower()


def test_full_text_property(extractor):
    """Test full_text property concatenation."""
    pdf_path = 'tests/test_data/sample.pdf'
    doc = extractor.extract(pdf_path)
    
    full = doc.full_text
    
    # Should contain content from all pages
    assert 'Page 1' in full
    assert 'Page 2' in full
    assert 'Page 3' in full
    
    # Should be concatenated with double newlines
    assert '\n\n' in full


def test_extract_empty_pages(extractor):
    """Test that empty pages are skipped."""
    import tempfile
    import fitz
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        temp_path = f.name
    
    try:
        # Create PDF with empty and non-empty pages
        doc = fitz.open()
        page1 = doc.new_page()
        page1.insert_text((72, 72), 'Page with text')
        page2 = doc.new_page()  # Empty page
        page3 = doc.new_page()
        page3.insert_text((72, 72), 'Another page')
        doc.save(temp_path)
        doc.close()
        
        # Extract
        extracted = extractor.extract(temp_path)
        
        # Should only have 2 pages (empty page skipped)
        assert len(extracted.pages) == 2
        assert extracted.pages[0].page_number == 1
        assert extracted.pages[1].page_number == 3
        
    finally:
        Path(temp_path).unlink()


def test_txt_encoding_fallback(extractor):
    """Test TXT file encoding detection."""
    import tempfile
    
    # Test UTF-8
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write('UTF-8 text with 日本語')
        temp_path = f.name
    
    try:
        doc = extractor.extract(temp_path)
        assert '日本語' in doc.pages[0].text
    finally:
        Path(temp_path).unlink()
