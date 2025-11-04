"""Vector memory store for cross-session fact retrieval (Tier-3).

Optional module for long-term memory beyond session context.
Requires: faiss-cpu (or faiss-gpu), numpy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Any
import time

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None


@dataclass
class VectorItem:
    """Item stored in vector memory."""
    id: str
    text: str
    embedding: np.ndarray
    timestamp: float
    metadata: dict[str, Any]
    confidence: float = 1.0


class VectorMemory:
    """FAISS-backed vector memory for cross-session recall.
    
    Features:
    - Similarity search over historical facts
    - Recency and confidence gating
    - Automatic deduplication
    
    Args:
        dimension: Embedding dimension
        index_type: FAISS index type ("flat", "ivf", "hnsw")
        max_items: Maximum items to store (FIFO eviction)
    """
    
    def __init__(
        self,
        dimension: int = 384,
        index_type: str = "flat",
        max_items: int = 10000
    ):
        if faiss is None:
            raise ImportError(
                "faiss is required for VectorMemory. "
                "Install with: pip install faiss-cpu"
            )
        
        self.dimension = dimension
        self.max_items = max_items
        
        # Create FAISS index
        if index_type == "flat":
            self.index = faiss.IndexFlatL2(dimension)
        elif index_type == "ivf":
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
            self.index.nprobe = 10
        elif index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(dimension, 32)
        else:
            raise ValueError(f"Unknown index_type: {index_type}")
        
        # Metadata storage (parallel to FAISS index)
        self._items: List[VectorItem] = []
    
    def add(
        self,
        text: str,
        embedding: np.ndarray,
        item_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        confidence: float = 1.0
    ) -> str:
        """Add item to vector memory.
        
        Args:
            text: Text content
            embedding: Dense embedding vector
            item_id: Optional unique ID (auto-generated if not provided)
            metadata: Optional metadata dict
            confidence: Confidence score (0.0 to 1.0)
        
        Returns:
            Item ID
        """
        # Generate ID if not provided
        if item_id is None:
            item_id = f"item_{len(self._items)}_{int(time.time())}"
        
        # Check for duplicates
        if any(item.id == item_id for item in self._items):
            return item_id
        
        # Create item
        item = VectorItem(
            id=item_id,
            text=text,
            embedding=embedding,
            timestamp=time.time(),
            metadata=metadata or {},
            confidence=confidence
        )
        
        # Add to FAISS
        emb = embedding.reshape(1, -1).astype(np.float32)
        self.index.add(emb)
        
        # Store metadata
        self._items.append(item)
        
        # Evict oldest if over limit
        if len(self._items) > self.max_items:
            # Remove oldest (FIFO)
            # Note: This doesn't remove from FAISS index (would need ID tracking)
            # For production, use IndexIDMap wrapper
            self._items.pop(0)
        
        return item_id
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        min_confidence: float = 0.0,
        max_age_seconds: Optional[float] = None
    ) -> List[VectorItem]:
        """Search for similar items.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            min_confidence: Minimum confidence threshold
            max_age_seconds: Maximum age in seconds (recency gate)
        
        Returns:
            List of matching VectorItem objects
        """
        if self.index.ntotal == 0:
            return []
        
        # Search FAISS
        query = query_embedding.reshape(1, -1).astype(np.float32)
        distances, indices = self.index.search(query, min(k * 2, self.index.ntotal))
        
        # Filter by confidence and recency
        results = []
        current_time = time.time()
        
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._items):
                continue
            
            item = self._items[idx]
            
            # Confidence gate
            if item.confidence < min_confidence:
                continue
            
            # Recency gate
            if max_age_seconds is not None:
                age = current_time - item.timestamp
                if age > max_age_seconds:
                    continue
            
            results.append(item)
            
            if len(results) >= k:
                break
        
        return results
    
    def get_by_id(self, item_id: str) -> Optional[VectorItem]:
        """Retrieve item by ID.
        
        Args:
            item_id: Item ID
        
        Returns:
            VectorItem if found, None otherwise
        """
        for item in self._items:
            if item.id == item_id:
                return item
        return None
    
    def delete(self, item_id: str) -> bool:
        """Delete item by ID.
        
        Note: This only removes from metadata, not FAISS index.
        For production, use IndexIDMap.
        
        Args:
            item_id: Item ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        for i, item in enumerate(self._items):
            if item.id == item_id:
                self._items.pop(i)
                return True
        return False
    
    def clear(self) -> None:
        """Clear all items."""
        self.index.reset()
        self._items.clear()
    
    def size(self) -> int:
        """Get number of items in memory."""
        return len(self._items)
    
    def save(self, path: str) -> None:
        """Save index to disk.
        
        Args:
            path: File path to save to
        """
        faiss.write_index(self.index, path)
    
    def load(self, path: str) -> None:
        """Load index from disk.
        
        Args:
            path: File path to load from
        """
        self.index = faiss.read_index(path)
