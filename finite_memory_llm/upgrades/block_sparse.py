"""Block-sparse attention mask export for efficient transformers.

Converts span keep-sets to block-sparse attention masks compatible
with Longformer, BigBird, or flash-attention sparse implementations.
"""

from __future__ import annotations

from typing import List, Union
import numpy as np


def build_block_sparse_mask(
    keep_indices: List[int],
    span_size: int,
    total_tokens: int,
    block_size: int = 16,
    format: str = "dense",
) -> Union[np.ndarray, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Build block-sparse attention mask from kept span indices.

    Args:
        keep_indices: Indices of spans to keep
        span_size: Size of each span in tokens
        total_tokens: Total number of tokens in sequence
        block_size: Size of attention blocks (for block-sparse attention)
        format: Output format - "dense", "coo", or "block_diagonal"

    Returns:
        Attention mask array
        - "dense": (total_tokens, total_tokens) binary mask
        - "coo": COO sparse matrix (row, col, data)
        - "block_diagonal": (n_blocks, n_blocks) binary mask
    """
    if format == "dense":
        return _build_dense_mask(keep_indices, span_size, total_tokens)
    elif format == "coo":
        return _build_coo_mask(keep_indices, span_size, total_tokens)
    elif format == "block_diagonal":
        return _build_block_mask(keep_indices, span_size, total_tokens, block_size)
    else:
        raise ValueError(f"Unknown format: {format}")


def _build_dense_mask(keep_indices: List[int], span_size: int, total_tokens: int) -> np.ndarray:
    """Build dense attention mask (total_tokens x total_tokens)."""
    mask = np.zeros((total_tokens, total_tokens), dtype=bool)

    # Mark kept spans as attending to each other
    kept_positions: list[int] = []
    for span_idx in keep_indices:
        start = span_idx * span_size
        end = min(start + span_size, total_tokens)
        kept_positions.extend(range(start, end))

    # Create attention pattern: kept tokens attend to all kept tokens
    for i in kept_positions:
        for j in kept_positions:
            if 0 <= i < total_tokens and 0 <= j < total_tokens:
                mask[i, j] = True

    return mask


def _build_coo_mask(
    keep_indices: List[int], span_size: int, total_tokens: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build COO sparse mask (row, col, data)."""
    kept_positions: list[int] = []
    for span_idx in keep_indices:
        start = span_idx * span_size
        end = min(start + span_size, total_tokens)
        kept_positions.extend(range(start, end))

    rows: list[int] = []
    cols: list[int] = []

    for i in kept_positions:
        for j in kept_positions:
            if 0 <= i < total_tokens and 0 <= j < total_tokens:
                rows.append(i)
                cols.append(j)

    data = np.ones(len(rows), dtype=bool)
    return np.array(rows), np.array(cols), data


def _build_block_mask(
    keep_indices: List[int], span_size: int, total_tokens: int, block_size: int
) -> np.ndarray:
    """Build block-diagonal sparse mask (n_blocks x n_blocks)."""
    n_blocks = (total_tokens + block_size - 1) // block_size
    mask = np.zeros((n_blocks, n_blocks), dtype=bool)

    # Map span indices to block indices
    kept_blocks: set[int] = set()
    for span_idx in keep_indices:
        start = span_idx * span_size
        end = min(start + span_size, total_tokens)

        # Mark all blocks touched by this span
        start_block = start // block_size
        end_block = (end - 1) // block_size
        kept_blocks.update(range(start_block, end_block + 1))

    # Blocks attend to each other
    for i in kept_blocks:
        for j in kept_blocks:
            if 0 <= i < n_blocks and 0 <= j < n_blocks:
                mask[i, j] = True

    return mask


def apply_causal_mask(mask: np.ndarray) -> np.ndarray:
    """Apply causal masking (lower triangular) to attention mask.

    Args:
        mask: Square attention mask

    Returns:
        Masked array with causal constraint
    """
    n = mask.shape[0]
    causal = np.tril(np.ones((n, n), dtype=bool))
    return mask & causal  # type: ignore


def estimate_sparsity(mask: np.ndarray) -> float:
    """Calculate sparsity ratio of attention mask.

    Args:
        mask: Attention mask (dense or block)

    Returns:
        Sparsity ratio (fraction of zeros)
    """
    total = mask.size
    nonzero = np.count_nonzero(mask)
    return 1.0 - (nonzero / total)


def export_longformer_mask(
    keep_indices: List[int], span_size: int, total_tokens: int, window_size: int = 512
) -> tuple[np.ndarray, np.ndarray]:
    """Export mask compatible with Longformer attention pattern.

    Longformer uses:
    - Local sliding window attention (all tokens)
    - Global attention (selected tokens)

    Args:
        keep_indices: Span indices to mark as global
        span_size: Size of each span
        total_tokens: Total sequence length
        window_size: Local attention window size

    Returns:
        Tuple of (attention_mask, global_attention_mask)
    """
    # All tokens get standard attention mask (1 = attend)
    attention_mask = np.ones(total_tokens, dtype=int)

    # Mark kept spans for global attention
    global_attention_mask = np.zeros(total_tokens, dtype=int)
    for span_idx in keep_indices:
        start = span_idx * span_size
        end = min(start + span_size, total_tokens)
        global_attention_mask[start:end] = 1

    return attention_mask, global_attention_mask
