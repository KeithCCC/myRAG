"""Demo script to test Japanese tokenization."""
import sys
sys.path.insert(0, '.')

from src.core.tokenizer import get_tokenizer

def demo_japanese_tokenization():
    """Demonstrate Japanese text tokenization."""
    print("=" * 60)
    print("Japanese Tokenization Demo with MeCab")
    print("=" * 60)
    print()
    
    tokenizer = get_tokenizer()
    
    # Check if MeCab is available
    if tokenizer.mecab:
        print("✓ MeCab is available and initialized")
    else:
        print("✗ MeCab not available, using fallback")
    print()
    
    # Test cases
    test_texts = [
        "機械学習はPythonで実装できます",
        "自然言語処理とRAGアプリケーション",
        "Python is a programming language",
        "日本語とEnglishの混在テキスト",
        "深層学習、ニューラルネットワーク、AI技術"
    ]
    
    for text in test_texts:
        print(f"Original:  {text}")
        tokenized = tokenizer.tokenize(text)
        print(f"Tokenized: {tokenized}")
        tokens = tokenizer.get_tokens_list(text)
        print(f"Tokens:    {tokens}")
        print(f"Count:     {len(tokens)} tokens")
        print("-" * 60)
        print()
    
    print("=" * 60)
    print("FTS5 Search Test")
    print("=" * 60)
    print()
    
    # Simulate FTS5 search
    query = "機械学習"
    print(f"Search query: {query}")
    tokenized_query = tokenizer.tokenize(query)
    print(f"FTS5 will search for: {tokenized_query}")
    print()
    
    query2 = "Python"
    print(f"Search query: {query2}")
    tokenized_query2 = tokenizer.tokenize(query2)
    print(f"FTS5 will search for: {tokenized_query2}")
    print()
    
    print("=" * 60)
    print("MeCab Integration Complete! ✓")
    print("=" * 60)


if __name__ == "__main__":
    demo_japanese_tokenization()
