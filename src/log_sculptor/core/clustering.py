"""Line clustering by structural similarity."""

from collections import defaultdict
from dataclasses import dataclass

from log_sculptor.core.tokenizer import Token, TokenType, token_signature


def jaccard_similarity(sig1: tuple[TokenType, ...], sig2: tuple[TokenType, ...]) -> float:
    if not sig1 and not sig2:
        return 1.0
    if not sig1 or not sig2:
        return 0.0
    matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
    total = max(len(sig1), len(sig2))
    return matches / total if total > 0 else 0.0


def sequence_similarity(sig1: tuple[TokenType, ...], sig2: tuple[TokenType, ...]) -> float:
    if not sig1 and not sig2:
        return 1.0
    if not sig1 or not sig2:
        return 0.0
    len_ratio = min(len(sig1), len(sig2)) / max(len(sig1), len(sig2))
    position_matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
    position_score = position_matches / max(len(sig1), len(sig2))
    set1, set2 = set(sig1), set(sig2)
    type_overlap = len(set1 & set2) / len(set1 | set2) if (set1 | set2) else 1.0
    return 0.4 * len_ratio + 0.4 * position_score + 0.2 * type_overlap


@dataclass
class Cluster:
    """A cluster of similar lines."""
    id: int
    members: list[tuple[list[Token], str]]
    centroid: tuple[TokenType, ...]
    cohesion: float

    def __len__(self) -> int:
        return len(self.members)


def _compute_cohesion(members: list[tuple[list[Token], str]]) -> float:
    if len(members) <= 1:
        return 1.0
    signatures = [token_signature(tokens) for tokens, _ in members]
    total_sim = 0.0
    count = 0
    for i in range(len(signatures)):
        for j in range(i + 1, len(signatures)):
            total_sim += sequence_similarity(signatures[i], signatures[j])
            count += 1
    return total_sim / count if count > 0 else 1.0


def cluster_lines(lines: list[tuple[list[Token], str]], threshold: float = 0.7) -> list[Cluster]:
    if not lines:
        return []

    clusters: list[Cluster] = []
    for tokens, line in lines:
        sig = token_signature(tokens)
        best_cluster = None
        best_sim = threshold

        for cluster in clusters:
            sim = sequence_similarity(sig, cluster.centroid)
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster

        if best_cluster is not None:
            best_cluster.members.append((tokens, line))
        else:
            clusters.append(Cluster(id=len(clusters), members=[(tokens, line)], centroid=sig, cohesion=1.0))

    for cluster in clusters:
        cluster.cohesion = _compute_cohesion(cluster.members)

    return clusters


def cluster_by_exact_signature(lines: list[tuple[list[Token], str]]) -> list[Cluster]:
    sig_groups: dict[tuple[TokenType, ...], list[tuple[list[Token], str]]] = defaultdict(list)
    for tokens, line in lines:
        sig = token_signature(tokens)
        sig_groups[sig].append((tokens, line))

    return [
        Cluster(id=i, members=members, centroid=sig, cohesion=1.0)
        for i, (sig, members) in enumerate(sig_groups.items())
    ]
