"""Tier-1 through Tier-3 upgrade modules for Finite Memory LLM.

These modules provide production-grade enhancements:
- Latency guards with deterministic fallbacks
- Embedding cache with MiniBatchKMeans
- Summary QA gates for fact verification
- Knapsack value-under-budget selection
- Block-sparse attention mask export
"""

__all__ = [
    "guarded_call",
    "SpanEmbedder",
    "SummaryQAGate",
    "choose_under_budget",
    "build_block_sparse_mask",
]

from .latency_guard import guarded_call
from .embed_cache import SpanEmbedder
from .summary_qa_gate import SummaryQAGate
from .knapsack import choose_under_budget
from .block_sparse import build_block_sparse_mask
