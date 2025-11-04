"""Optional vector memory bridge for cross-session recall (Tier-3).

Provides FAISS/SQLite-backed vector storage for long-term memory.
"""

from typing import Any

__all__ = ["VectorMemory", "VectorItem"]

VectorMemory: Any
VectorItem: Any

try:
    from .vector_store import VectorMemory, VectorItem
except ImportError:
    # Make optional - don't fail if dependencies missing
    VectorMemory = None
    VectorItem = None
