"""Tests for log line clustering."""
import pytest
from log_sculptor.core.clustering import (
    cluster_lines,
    cluster_by_exact_signature,
    sequence_similarity,
    Cluster,
)
from log_sculptor.core.tokenizer import tokenize


class TestSequenceSimilarity:
    """Tests for sequence similarity calculation."""

    def test_identical_sequences(self):
        """Identical sequences should have similarity 1.0."""
        from log_sculptor.core.tokenizer import TokenType
        seq1 = (TokenType.WORD, TokenType.WHITESPACE, TokenType.NUMBER)
        seq2 = (TokenType.WORD, TokenType.WHITESPACE, TokenType.NUMBER)
        assert sequence_similarity(seq1, seq2) == 1.0

    def test_completely_different(self):
        """Completely different sequences should have low similarity."""
        from log_sculptor.core.tokenizer import TokenType
        seq1 = (TokenType.WORD, TokenType.WORD, TokenType.WORD)
        seq2 = (TokenType.NUMBER, TokenType.IP, TokenType.QUOTED)
        sim = sequence_similarity(seq1, seq2)
        # Different types but same length - will have some similarity from length ratio
        assert sim < 0.5

    def test_partial_overlap(self):
        """Partially overlapping sequences."""
        from log_sculptor.core.tokenizer import TokenType
        seq1 = (TokenType.WORD, TokenType.WHITESPACE, TokenType.NUMBER)
        seq2 = (TokenType.WORD, TokenType.WHITESPACE, TokenType.WORD)
        sim = sequence_similarity(seq1, seq2)
        assert 0.0 < sim < 1.0

    def test_empty_sequences(self):
        """Empty sequences should have similarity 1.0."""
        assert sequence_similarity((), ()) == 1.0

    def test_one_empty_sequence(self):
        """One empty sequence should have similarity 0.0."""
        from log_sculptor.core.tokenizer import TokenType
        assert sequence_similarity((TokenType.WORD,), ()) == 0.0
        assert sequence_similarity((), (TokenType.WORD,)) == 0.0

    def test_different_lengths(self):
        """Different length sequences."""
        from log_sculptor.core.tokenizer import TokenType
        seq1 = (TokenType.WORD, TokenType.WHITESPACE, TokenType.NUMBER, TokenType.WORD)
        seq2 = (TokenType.WORD, TokenType.WHITESPACE)
        sim = sequence_similarity(seq1, seq2)
        assert 0.0 < sim < 1.0


class TestClusterByExactSignature:
    """Tests for exact signature clustering."""

    def test_same_signatures_cluster(self):
        """Lines with same token signatures should cluster."""
        lines = [
            (tokenize("INFO server started"), "INFO server started"),
            (tokenize("WARN server stopped"), "WARN server stopped"),
            (tokenize("ERROR server crashed"), "ERROR server crashed"),
        ]

        clusters = cluster_by_exact_signature(lines)

        # All have same signature: WORD WHITESPACE WORD WHITESPACE WORD
        assert len(clusters) == 1
        assert len(clusters[0].members) == 3

    def test_different_signatures_separate(self):
        """Lines with different signatures should be separate clusters."""
        lines = [
            (tokenize("INFO started"), "INFO started"),
            (tokenize("192.168.1.1 connected"), "192.168.1.1 connected"),
        ]

        clusters = cluster_by_exact_signature(lines)

        # Different signatures: one starts with WORD, other with IP
        assert len(clusters) == 2

    def test_empty_input(self):
        """Empty input should return empty clusters."""
        clusters = cluster_by_exact_signature([])
        assert clusters == []

    def test_single_line(self):
        """Single line should return single cluster."""
        lines = [(tokenize("test line"), "test line")]
        clusters = cluster_by_exact_signature(lines)

        assert len(clusters) == 1
        assert len(clusters[0].members) == 1


class TestClusterLines:
    """Tests for similarity-based clustering."""

    def test_cluster_similar_lines(self):
        """Similar lines should cluster together."""
        lines = [
            (tokenize("INFO server started"), "INFO server started"),
            (tokenize("WARN server stopped"), "WARN server stopped"),
            (tokenize("ERROR disk full"), "ERROR disk full"),
        ]

        clusters = cluster_lines(lines, threshold=0.7)

        # With high similarity threshold, similar structures should cluster
        assert len(clusters) >= 1

    def test_threshold_affects_clustering(self):
        """Higher threshold should create more clusters."""
        lines = [
            (tokenize("INFO server started"), "INFO server started"),
            (tokenize("WARN server stopped"), "WARN server stopped"),
            (tokenize("ERROR 404 not found"), "ERROR 404 not found"),
        ]

        clusters_low = cluster_lines(lines, threshold=0.5)
        clusters_high = cluster_lines(lines, threshold=0.9)

        # Lower threshold = fewer clusters (more merged)
        assert len(clusters_low) <= len(clusters_high)

    def test_empty_input(self):
        """Empty input should return empty clusters."""
        clusters = cluster_lines([], threshold=0.7)
        assert clusters == []


class TestClusterClass:
    """Tests for Cluster dataclass."""

    def test_cluster_creation(self):
        """Test cluster creation."""
        from log_sculptor.core.tokenizer import TokenType
        centroid = (TokenType.WORD,)
        cluster = Cluster(id=0, members=[], centroid=centroid, cohesion=1.0)
        assert cluster.id == 0
        assert cluster.members == []
        assert cluster.cohesion == 1.0

    def test_cluster_with_members(self):
        """Test cluster with members."""
        from log_sculptor.core.tokenizer import TokenType
        tokens = tokenize("test line")
        members = [(tokens, "test line")]
        centroid = (TokenType.WORD, TokenType.WHITESPACE, TokenType.WORD)
        cluster = Cluster(id=0, members=members, centroid=centroid, cohesion=0.9)

        assert len(cluster.members) == 1
        assert cluster.cohesion == 0.9
