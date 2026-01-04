"""Text extraction module for PDF, TXT, and MD files."""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ExtractedPage:
    """Represents extracted text from a single page."""
    page_number: int
    text: str
    char_count: int


@dataclass
class ExtractedDocument:
    """Represents extracted text from an entire document."""
    file_path: str
    pages: List[ExtractedPage]
    total_chars: int
    
    @property
    def full_text(self) -> str:
        """Get all text concatenated."""
        return '\n\n'.join(page.text for page in self.pages)


class Extractor:
    """Handles text extraction from various file formats."""
    
    def extract(self, file_path: str) -> ExtractedDocument:
        """Extract text from file based on extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            ExtractedDocument with text and page information
            
        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return self.extract_pdf(file_path)
        elif ext == '.txt':
            return self.extract_txt(file_path)
        elif ext == '.md':
            return self.extract_md(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def extract_pdf(self, file_path: str) -> ExtractedDocument:
        """Extract text from PDF file with page numbers.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ExtractedDocument with page-by-page text
            
        Raises:
            Exception: If PDF cannot be read
        """
        try:
            doc = fitz.open(file_path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Clean up text
                text = text.strip()
                
                if text:  # Only add non-empty pages
                    pages.append(ExtractedPage(
                        page_number=page_num + 1,  # 1-indexed
                        text=text,
                        char_count=len(text)
                    ))
            
            doc.close()
            
            total_chars = sum(p.char_count for p in pages)
            
            return ExtractedDocument(
                file_path=file_path,
                pages=pages,
                total_chars=total_chars
            )
            
        except Exception as e:
            raise Exception(f"Failed to extract PDF {file_path}: {str(e)}") from e
    
    def extract_txt(self, file_path: str) -> ExtractedDocument:
        """Extract text from TXT file.
        
        TXT files are treated as single-page documents.
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            ExtractedDocument with single page
            
        Raises:
            Exception: If file cannot be read
        """
        try:
            # Try multiple encodings
            encodings = ['utf-8', 'utf-8-sig', 'shift_jis', 'cp932', 'latin-1']
            text = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if text is None:
                raise Exception("Could not decode file with any supported encoding")
            
            text = text.strip()
            
            pages = [ExtractedPage(
                page_number=1,
                text=text,
                char_count=len(text)
            )]
            
            return ExtractedDocument(
                file_path=file_path,
                pages=pages,
                total_chars=len(text)
            )
            
        except Exception as e:
            raise Exception(f"Failed to extract TXT {file_path}: {str(e)}") from e
    
    def extract_md(self, file_path: str) -> ExtractedDocument:
        """Extract text from Markdown file.
        
        MD files are treated as single-page documents.
        Currently extracts raw markdown without rendering.
        
        Args:
            file_path: Path to MD file
            
        Returns:
            ExtractedDocument with single page
            
        Raises:
            Exception: If file cannot be read
        """
        # Markdown files can be treated the same as TXT for now
        # In the future, could parse markdown structure
        return self.extract_txt(file_path)
    
    def extract_with_error_handling(self, file_path: str) -> tuple[Optional[ExtractedDocument], Optional[str]]:
        """Extract text with error handling.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (ExtractedDocument or None, error_message or None)
        """
        try:
            doc = self.extract(file_path)
            return doc, None
        except Exception as e:
            return None, str(e)
