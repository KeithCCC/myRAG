"""Tests for Japanese tokenization."""
import pytest
from src.core.tokenizer import Tokenizer, get_tokenizer


def test_tokenizer_initialization():
    """Test tokenizer can be initialized."""
    tokenizer = Tokenizer()
    assert tokenizer is not None


def test_detect_japanese():
    """Test Japanese character detection."""
    tokenizer = Tokenizer()
    
    # Japanese text
    assert tokenizer._contains_japanese("機械学習")
    assert tokenizer._contains_japanese("こんにちは")
    assert tokenizer._contains_japanese("カタカナ")
    assert tokenizer._contains_japanese("日本語とEnglish混在")
    
    # Non-Japanese text
    assert not tokenizer._contains_japanese("Hello World")
    assert not tokenizer._contains_japanese("Python programming")
    assert not tokenizer._contains_japanese("123456")


def test_tokenize_english():
    """Test English text remains unchanged."""
    tokenizer = Tokenizer()
    
    text = "Python is a programming language"
    result = tokenizer.tokenize(text)
    assert result == text


def test_tokenize_japanese():
    """Test Japanese text tokenization."""
    tokenizer = Tokenizer()
    
    text = "機械学習はPythonで実装できます"
    result = tokenizer.tokenize(text)
    
    # Should return space-separated tokens
    assert isinstance(result, str)
    assert len(result) > 0
    
    # If MeCab is available, should have spaces
    if tokenizer.mecab:
        assert " " in result or result == text
        tokens = result.split()
        assert len(tokens) > 1  # Should be split into multiple words


def test_tokenize_empty():
    """Test empty string handling."""
    tokenizer = Tokenizer()
    
    assert tokenizer.tokenize("") == ""
    assert tokenizer.tokenize(None) == ""


def test_get_tokens_list():
    """Test getting tokens as list."""
    tokenizer = Tokenizer()
    
    text = "Hello World Python"
    result = tokenizer.get_tokens_list(text)
    
    assert isinstance(result, list)
    assert len(result) == 3
    assert "Hello" in result
    assert "World" in result
    assert "Python" in result


def test_get_tokens_list_japanese():
    """Test getting Japanese tokens as list."""
    tokenizer = Tokenizer()
    
    text = "機械学習"
    result = tokenizer.get_tokens_list(text)
    
    assert isinstance(result, list)
    assert len(result) >= 1


def test_global_tokenizer():
    """Test global tokenizer singleton."""
    tokenizer1 = get_tokenizer()
    tokenizer2 = get_tokenizer()
    
    # Should return same instance
    assert tokenizer1 is tokenizer2


def test_mixed_language():
    """Test mixed Japanese and English."""
    tokenizer = Tokenizer()
    
    text = "PythonでRAGアプリを作る"
    result = tokenizer.tokenize(text)
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_tokenize_special_characters():
    """Test handling of special characters."""
    tokenizer = Tokenizer()
    
    text = "Hello! World? Python."
    result = tokenizer.tokenize(text)
    
    assert isinstance(result, str)
    assert len(result) > 0
