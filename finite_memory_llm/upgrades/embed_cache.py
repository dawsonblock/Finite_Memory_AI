"""Embedding cache with MiniBatchKMeans for semantic policy.

Caches span embeddings by token hash to avoid recomputation.
Uses MiniBatchKMeans with warm-start for stable, low-jitter clustering.
"""

from __future__ import annotations

import hashlib
from typing import List, Tuple, Optional, Any
from collections import OrderedDict

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from sklearn.cluster import MiniBatchKMeans
except ImportError:
    MiniBatchKMeans = None


class SpanEmbedder:
    """Efficient span embedding with caching and stable clustering.
    
    Features:
    - LRU cache for span embeddings (avoids recomputation)
    - MiniBatchKMeans with warm-start (reduces jitter)
    - Automatic cache eviction (prevents memory growth)
    
    Args:
        model_name: SentenceTransformer model name
        cache_size: Maximum number of cached embeddings
        random_state: Random seed for reproducible clustering
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_size: int = 1000,
        random_state: int = 42
    ):
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers is required for SpanEmbedder. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model = SentenceTransformer(model_name)
        self.cache_size = cache_size
        self.random_state = random_state
        
        # LRU cache for embeddings
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        
        # Persistent clustering state for warm-start
        self._kmeans: Optional[Any] = None
        self._last_k: int = 0
        
        # Stats
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _hash_span(self, tokens: List[int]) -> str:
        """Create a stable hash for a token span."""
        return hashlib.md5(str(tokens).encode()).hexdigest()
    
    def encode_span(self, tokens: List[int], text: Optional[str] = None) -> np.ndarray:
        """Encode a single span with caching.
        
        Args:
            tokens: Token IDs for the span
            text: Optional pre-decoded text (avoids re-decoding)
        
        Returns:
            Embedding vector
        """
        span_hash = self._hash_span(tokens)
        
        # Check cache
        if span_hash in self._cache:
            self.cache_hits += 1
            # Move to end (LRU)
            self._cache.move_to_end(span_hash)
            return self._cache[span_hash]
        
        # Cache miss: compute embedding
        self.cache_misses += 1
        
        if text is None:
            # If no text provided, caller needs to handle decoding
            # For now, use a placeholder
            raise ValueError("text must be provided for new spans")
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Store in cache
        self._cache[span_hash] = embedding
        
        # Evict oldest if over limit
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
        
        return embedding
    
    def encode_spans(
        self,
        spans: List[List[int]],
        texts: Optional[List[str]] = None
    ) -> np.ndarray:
        """Encode multiple spans with batch caching.
        
        Args:
            spans: List of token ID lists
            texts: Optional list of pre-decoded texts
        
        Returns:
            Array of embeddings, shape (n_spans, embedding_dim)
        """
        if not spans:
            return np.array([])
        
        embeddings = []
        to_compute = []
        to_compute_idx = []
        
        # Check cache for each span
        for i, span in enumerate(spans):
            span_hash = self._hash_span(span)
            if span_hash in self._cache:
                self.cache_hits += 1
                self._cache.move_to_end(span_hash)
                embeddings.append(self._cache[span_hash])
            else:
                self.cache_misses += 1
                embeddings.append(None)
                to_compute_idx.append(i)
                if texts is not None:
                    to_compute.append(texts[i])
        
        # Compute missing embeddings in batch
        if to_compute:
            new_embeddings = self.model.encode(to_compute, convert_to_numpy=True)
            
            for idx, emb in zip(to_compute_idx, new_embeddings):
                embeddings[idx] = emb
                span_hash = self._hash_span(spans[idx])
                self._cache[span_hash] = emb
                
                # Evict oldest if needed
                if len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)
        
        return np.vstack(embeddings)
    
    def select_representatives(
        self,
        embeddings: np.ndarray,
        k: int,
        recency_bias: float = 0.15
    ) -> List[int]:
        """Select representative span indices using MiniBatchKMeans.
        
        Uses warm-start when k matches previous clustering for stability.
        
        Args:
            embeddings: Array of span embeddings, shape (n_spans, dim)
            k: Number of clusters/representatives
            recency_bias: Weight for recent spans (0.0 to 1.0)
        
        Returns:
            List of selected span indices
        """
        if MiniBatchKMeans is None:
            raise ImportError(
                "scikit-learn is required for clustering. "
                "Install with: pip install scikit-learn"
            )
        
        n_spans = len(embeddings)
        if n_spans == 0:
            return []
        
        k = min(k, n_spans)
        
        # Check if we can warm-start
        can_warm_start = (
            self._kmeans is not None and
            self._last_k == k and
            hasattr(self._kmeans, 'cluster_centers_')
        )
        
        if can_warm_start:
            # Warm-start: continue from previous clustering
            kmeans = self._kmeans
            kmeans.partial_fit(embeddings)
        else:
            # Cold start: new clustering
            kmeans = MiniBatchKMeans(
                n_clusters=k,
                random_state=self.random_state,
                batch_size=min(100, n_spans),
                n_init=3,
                max_iter=100
            )
            kmeans.fit(embeddings)
            self._kmeans = kmeans
            self._last_k = k
        
        # Predict cluster labels
        labels = kmeans.predict(embeddings)
        
        # Select one representative per cluster
        representatives = []
        for cluster_id in range(k):
            cluster_mask = labels == cluster_id
            if not cluster_mask.any():
                continue
            
            cluster_indices = np.where(cluster_mask)[0]
            cluster_embs = embeddings[cluster_mask]
            centroid = kmeans.cluster_centers_[cluster_id]
            
            # Distance to centroid
            distances = np.linalg.norm(cluster_embs - centroid, axis=1)
            
            # Apply recency bias: prefer later spans
            if recency_bias > 0:
                recency_scores = cluster_indices / max(1, n_spans - 1)
                # Lower distance = better, higher recency = better
                # Normalize both to [0, 1] and combine
                norm_dist = distances / (distances.max() + 1e-6)
                combined_scores = (1 - norm_dist) * (1 - recency_bias) + recency_scores * recency_bias
                best_idx = cluster_indices[np.argmax(combined_scores)]
            else:
                # Pure centroid distance
                best_idx = cluster_indices[np.argmin(distances)]
            
            representatives.append(int(best_idx))
        
        return sorted(representatives)
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        hit_rate = self.cache_hits / max(1, self.cache_hits + self.cache_misses)
        return {
            "cache_size": len(self._cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "max_size": self.cache_size,
        }
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
