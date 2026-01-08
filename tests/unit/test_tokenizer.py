"""Basic tokenizer tests."""
from log_sculptor.core.tokenizer import tokenize, TokenType

def test_tokenize_simple():
    tokens = tokenize("INFO test")
    assert len(tokens) == 3
    assert tokens[0].type == TokenType.WORD
