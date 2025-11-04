"""Knapsack value-under-budget selection for memory policies.

Selects spans to maximize value while staying under token budget.
More principled than simple top-K selection.
"""

from __future__ import annotations

from typing import List, Tuple


def choose_under_budget(items: List[Tuple[int, int, int, float]], budget: int) -> List[int]:
    """Select items to maximize value under budget constraint.

    Uses greedy value-per-size heuristic (approximation to knapsack).
    Items are (index, start, end, value) tuples.

    Args:
        items: List of (index, start_pos, end_pos, value) tuples
        budget: Maximum total size (end - start summed across selected items)

    Returns:
        List of selected item indices

    Examples:
        >>> items = [(0, 0, 10, 5.0), (1, 10, 20, 3.0), (2, 20, 30, 8.0)]
        >>> result = choose_under_budget(items, budget=25)
        >>> assert 0 in result and 2 in result  # Best value per size
    """
    if not items or budget <= 0:
        return []

    # Calculate value per token for each item
    scored = []
    for idx, start, end, value in items:
        size = max(1, end - start)
        value_per_token = value / size
        scored.append((idx, start, end, size, value, value_per_token))

    # Sort by value per token (descending)
    scored.sort(key=lambda x: x[5], reverse=True)

    # Greedy selection
    selected = []
    total_size = 0

    for idx, start, end, size, value, vpt in scored:
        if total_size + size <= budget:
            selected.append(idx)
            total_size += size

    return sorted(selected)


def choose_under_budget_dp(items: List[Tuple[int, int, int, float]], budget: int) -> List[int]:
    """Select items using dynamic programming (exact solution).

    More expensive but optimal. Use for small problem sizes.

    Args:
        items: List of (index, start_pos, end_pos, value) tuples
        budget: Maximum total size

    Returns:
        List of selected item indices
    """
    if not items or budget <= 0:
        return []

    n = len(items)

    # Extract sizes and values
    sizes = [max(1, end - start) for _, start, end, _ in items]
    values = [value for _, _, _, value in items]

    # DP table: dp[i][w] = max value using items 0..i-1 with budget w
    dp = [[0.0] * (budget + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        size = sizes[i - 1]
        value = values[i - 1]

        for w in range(budget + 1):
            # Don't take item i-1
            dp[i][w] = dp[i - 1][w]

            # Take item i-1 if it fits
            if size <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - size] + value)

    # Backtrack to find selected items
    selected = []
    w = budget

    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(items[i - 1][0])  # Add index
            w -= sizes[i - 1]

    return sorted(selected)


def partition_budget(
    total_budget: int,
    recency_weight: float = 0.25,
    importance_weight: float = 0.50,
    semantic_weight: float = 0.25,
) -> Tuple[int, int, int]:
    """Partition budget across policy components.

    Args:
        total_budget: Total token budget
        recency_weight: Fraction for recent window
        importance_weight: Fraction for importance-based selection
        semantic_weight: Fraction for semantic diversity

    Returns:
        Tuple of (recency_budget, importance_budget, semantic_budget)
    """
    total_weight = recency_weight + importance_weight + semantic_weight

    recency_budget = int(total_budget * recency_weight / total_weight)
    importance_budget = int(total_budget * importance_weight / total_weight)
    semantic_budget = total_budget - recency_budget - importance_budget

    return recency_budget, importance_budget, semantic_budget
