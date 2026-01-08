"""Pattern merging for log-sculptor."""

import hashlib

from log_sculptor.core.tokenizer import TokenType
from log_sculptor.core.models import Pattern, PatternElement


def _get_type_signature(pattern: Pattern) -> tuple[TokenType | None, ...]:
    """Get token type sequence for a pattern (excluding whitespace)."""
    return tuple(
        e.token_type for e in pattern.elements
        if not (e.type == "literal" and e.token_type == TokenType.WHITESPACE)
    )


def can_merge(p1: Pattern, p2: Pattern, threshold: float = 0.8) -> bool:
    """
    Check if two patterns can be merged.

    Patterns can merge if they have similar token type signatures.

    Args:
        p1: First pattern.
        p2: Second pattern.
        threshold: Minimum similarity to allow merge.

    Returns:
        True if patterns can be merged.
    """
    sig1 = _get_type_signature(p1)
    sig2 = _get_type_signature(p2)

    # Must have same length
    if len(sig1) != len(sig2):
        return False

    # Must have same token types at each position
    for t1, t2 in zip(sig1, sig2):
        if t1 != t2:
            return False

    return True


def merge_two(p1: Pattern, p2: Pattern) -> Pattern:
    """
    Merge two patterns into a generalized pattern.

    Literals that match stay as literals.
    Literals that differ become fields.
    Fields stay as fields.

    Args:
        p1: First pattern.
        p2: Second pattern.

    Returns:
        Merged pattern.
    """
    new_elements: list[PatternElement] = []
    field_index = 0

    # Iterate over elements, skipping whitespace alignment
    e1_iter = iter(p1.elements)
    e2_iter = iter(p2.elements)

    for e1 in e1_iter:
        # Handle whitespace
        if e1.type == "literal" and e1.token_type == TokenType.WHITESPACE:
            new_elements.append(e1)
            # Consume corresponding whitespace from p2
            try:
                next(e2_iter)
            except StopIteration:
                pass
            continue

        # Get corresponding element from p2
        try:
            e2 = next(e2_iter)
            # Skip whitespace in e2
            while e2.type == "literal" and e2.token_type == TokenType.WHITESPACE:
                e2 = next(e2_iter)
        except StopIteration:
            e2 = None

        if e2 is None:
            # No corresponding element, keep e1
            new_elements.append(e1)
            continue

        # Both are fields
        if e1.type == "field" and e2.type == "field":
            # Keep the field, prefer first pattern's name
            new_elements.append(e1)
            field_index += 1
            continue

        # Both are literals
        if e1.type == "literal" and e2.type == "literal":
            if e1.value == e2.value:
                # Same literal, keep it
                new_elements.append(e1)
            else:
                # Different literals, convert to field
                new_elements.append(PatternElement(
                    type="field",
                    token_type=e1.token_type,
                    field_name=f"field_{field_index}",
                ))
            field_index += 1
            continue

        # Mixed: one is literal, one is field -> result is field
        field_elem = e1 if e1.type == "field" else e2
        new_elements.append(PatternElement(
            type="field",
            token_type=field_elem.token_type,
            field_name=field_elem.field_name or f"field_{field_index}",
        ))
        field_index += 1

    # Generate new ID
    sig = "|".join(
        f"{e.type}:{e.token_type.value if e.token_type else e.value}"
        for e in new_elements
        if not (e.type == "literal" and e.token_type == TokenType.WHITESPACE)
    )
    new_id = hashlib.md5(sig.encode()).hexdigest()[:12]

    # Combine metadata
    total_freq = p1.frequency + p2.frequency
    weighted_conf = (p1.confidence * p1.frequency + p2.confidence * p2.frequency) / total_freq

    return Pattern(
        id=new_id,
        elements=new_elements,
        frequency=total_freq,
        confidence=weighted_conf,
        example=p1.example,  # Keep first pattern's example
    )


def merge_patterns(
    patterns: list[Pattern],
    threshold: float = 0.8,
) -> list[Pattern]:
    """
    Merge similar patterns into generalized patterns.

    Uses greedy merging: repeatedly merge the most similar pair until
    no more merges are possible.

    Args:
        patterns: List of patterns to merge.
        threshold: Minimum similarity to allow merge.

    Returns:
        List of merged patterns.
    """
    if len(patterns) <= 1:
        return patterns.copy()

    result = patterns.copy()
    changed = True

    while changed:
        changed = False
        new_result: list[Pattern] = []
        merged_indices: set[int] = set()

        for i in range(len(result)):
            if i in merged_indices:
                continue

            best_j = -1
            for j in range(i + 1, len(result)):
                if j in merged_indices:
                    continue
                if can_merge(result[i], result[j], threshold):
                    best_j = j
                    break

            if best_j >= 0:
                # Merge i and j
                merged = merge_two(result[i], result[best_j])
                new_result.append(merged)
                merged_indices.add(i)
                merged_indices.add(best_j)
                changed = True
            else:
                new_result.append(result[i])

        result = new_result

    return result
