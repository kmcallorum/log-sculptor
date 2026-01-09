"""Tokenizer tests."""
from log_sculptor.core.tokenizer import tokenize, Token, TokenType, token_signature


class TestTokenize:
    """Tests for tokenize function."""

    def test_tokenize_simple(self):
        """Test simple tokenization."""
        tokens = tokenize("INFO test")
        assert len(tokens) == 3
        assert tokens[0].type == TokenType.WORD

    def test_tokenize_ip_address(self):
        """Test IP address tokenization."""
        tokens = tokenize("192.168.1.1 connected")
        assert tokens[0].type == TokenType.IP
        assert tokens[0].value == "192.168.1.1"

    def test_tokenize_timestamp(self):
        """Test timestamp tokenization."""
        tokens = tokenize("2024-01-15T10:30:00 event")
        assert tokens[0].type == TokenType.TIMESTAMP

    def test_tokenize_quoted_string(self):
        """Test quoted string tokenization."""
        tokens = tokenize('"hello world" message')
        assert tokens[0].type == TokenType.QUOTED
        assert tokens[0].value == '"hello world"'

    def test_tokenize_single_quoted(self):
        """Test single quoted string."""
        tokens = tokenize("'single quoted'")
        assert tokens[0].type == TokenType.QUOTED

    def test_tokenize_bracket(self):
        """Test bracket tokenization."""
        tokens = tokenize("[data] {json}")
        bracket_tokens = [t for t in tokens if t.type == TokenType.BRACKET]
        assert len(bracket_tokens) == 2

    def test_tokenize_number(self):
        """Test number tokenization."""
        tokens = tokenize("123 -456 78.9")
        number_tokens = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(number_tokens) == 3

    def test_tokenize_punct(self):
        """Test punctuation tokenization."""
        tokens = tokenize("a@b")
        # '@' should be PUNCT
        punct_tokens = [t for t in tokens if t.type == TokenType.PUNCT]
        assert len(punct_tokens) == 1
        assert punct_tokens[0].value == "@"

    def test_tokenize_unmatched_char(self):
        """Test unmatched character becomes PUNCT."""
        # Use a character that doesn't match any pattern
        tokens = tokenize("a#b")
        punct_tokens = [t for t in tokens if t.type == TokenType.PUNCT]
        assert len(punct_tokens) == 1

    def test_tokenize_empty_string(self):
        """Test empty string returns empty list."""
        tokens = tokenize("")
        assert tokens == []

    def test_tokenize_whitespace_only(self):
        """Test whitespace-only string."""
        tokens = tokenize("   ")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.WHITESPACE


class TestToken:
    """Tests for Token class."""

    def test_token_creation(self):
        """Test token creation."""
        token = Token(TokenType.WORD, "hello", 0, 5)
        assert token.type == TokenType.WORD
        assert token.value == "hello"
        assert token.start == 0
        assert token.end == 5

    def test_token_to_dict(self):
        """Test Token.to_dict method."""
        token = Token(TokenType.IP, "192.168.1.1", 0, 11)
        d = token.to_dict()

        assert d["type"] == "IP"
        assert d["value"] == "192.168.1.1"
        assert d["start"] == 0
        assert d["end"] == 11

    def test_token_from_dict(self):
        """Test Token.from_dict method."""
        data = {
            "type": "NUMBER",
            "value": "123",
            "start": 5,
            "end": 8,
        }
        token = Token.from_dict(data)

        assert token.type == TokenType.NUMBER
        assert token.value == "123"
        assert token.start == 5
        assert token.end == 8

    def test_token_roundtrip(self):
        """Test to_dict/from_dict roundtrip."""
        original = Token(TokenType.QUOTED, '"test"', 0, 6)
        restored = Token.from_dict(original.to_dict())

        assert original == restored


class TestTokenSignature:
    """Tests for token_signature function."""

    def test_signature_excludes_whitespace(self):
        """Test signature excludes whitespace tokens."""
        tokens = tokenize("INFO test")
        sig = token_signature(tokens)

        assert TokenType.WHITESPACE not in sig
        assert sig == (TokenType.WORD, TokenType.WORD)

    def test_signature_empty_list(self):
        """Test signature of empty list."""
        sig = token_signature([])
        assert sig == ()

    def test_signature_preserves_order(self):
        """Test signature preserves token order."""
        tokens = tokenize("192.168.1.1 INFO 123")
        sig = token_signature(tokens)

        assert sig == (TokenType.IP, TokenType.WORD, TokenType.NUMBER)
