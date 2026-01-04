"""Text tokenization utilities for Japanese and multilingual support."""
import re
from typing import List

# Try to import MeCab, fall back to basic tokenization if not available
try:
    import MeCab
    MECAB_AVAILABLE = True
except ImportError:
    MECAB_AVAILABLE = False


class Tokenizer:
    """Multi-language tokenizer with Japanese support via MeCab."""
    
    def __init__(self):
        """Initialize tokenizer with MeCab if available."""
        self.mecab = None
        if MECAB_AVAILABLE:
            try:
                # -Owakati: Output only words separated by spaces
                self.mecab = MeCab.Tagger("-Owakati")
            except Exception as e:
                print(f"Warning: MeCab initialization failed: {e}")
                print("Falling back to basic tokenization")
    
    def tokenize(self, text: str) -> str:
        """Tokenize text for FTS5 indexing.
        
        Detects language and applies appropriate tokenization:
        - Japanese: MeCab word segmentation
        - English/Other: Space-separated (FTS5 default)
        
        Args:
            text: Input text to tokenize
            
        Returns:
            Space-separated tokens suitable for FTS5
        """
        if not text:
            return ""
        
        # If text contains Japanese characters, use MeCab
        if self._contains_japanese(text) and self.mecab:
            return self._tokenize_japanese(text)
        
        # For non-Japanese text, return as-is (FTS5 handles it)
        return text
    
    def _contains_japanese(self, text: str) -> bool:
        """Check if text contains Japanese characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains Hiragana, Katakana, or Kanji
        """
        # Hiragana: \u3040-\u309f
        # Katakana: \u30a0-\u30ff
        # Kanji: \u4e00-\u9fff
        return bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', text))
    
    def _tokenize_japanese(self, text: str) -> str:
        """Tokenize Japanese text using MeCab.
        
        Args:
            text: Japanese text to tokenize
            
        Returns:
            Space-separated tokens
        """
        try:
            # Parse and get space-separated words
            result = self.mecab.parse(text)
            if result:
                return result.strip()
            return text
        except Exception as e:
            print(f"Warning: MeCab tokenization failed: {e}")
            return text
    
    def get_tokens_list(self, text: str) -> List[str]:
        """Get tokens as a list instead of space-separated string.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens
        """
        tokenized = self.tokenize(text)
        return tokenized.split() if tokenized else []


# Global tokenizer instance
_tokenizer = None

def get_tokenizer() -> Tokenizer:
    """Get or create global tokenizer instance.
    
    Returns:
        Tokenizer instance
    """
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = Tokenizer()
    return _tokenizer
