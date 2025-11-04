"""Metrics tracking for observability and SLO enforcement.

Tracks key metrics for finite memory LLM performance:
- Token throughput and compression
- Policy latency and fallback rates
- Cache hit rates
- Accuracy proxies
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any
from collections import deque
import time


@dataclass
class TurnMetrics:
    """Metrics for a single turn."""
    timestamp: float
    tokens_seen: int
    tokens_retained: int
    compression_ratio: float
    policy_latency_ms: float
    fallback_occurred: bool
    cache_hit: bool
    evictions: int


class Metrics:
    """Real-time metrics collector with configurable aggregation.
    
    Tracks:
    - Throughput: tokens/sec, turns/sec
    - Compression: average ratio, min/max
    - Latency: p50, p95, p99 policy latency
    - Quality: fallback rate, cache hit rate
    
    Args:
        enabled: Whether to collect metrics
        window_size: Number of recent turns to keep for rolling stats
    """
    
    def __init__(
        self,
        enabled: bool = True,
        window_size: int = 100
    ):
        self.enabled = enabled
        self.window_size = window_size
        
        # Rolling window of recent turn metrics
        self._turns: deque[TurnMetrics] = deque(maxlen=window_size)
        
        # Cumulative counters
        self.total_turns = 0
        self.total_tokens_seen = 0
        self.total_tokens_retained = 0
        self.total_evictions = 0
        self.total_fallbacks = 0
        self.total_cache_hits = 0
        self.total_cache_misses = 0
        
        # Session start time
        self.start_time = time.time()
    
    def observe_turn(
        self,
        stats: Any,
        cache_hit: bool = False
    ) -> None:
        """Record metrics for a completed turn.
        
        Args:
            stats: MemoryStats object from CompleteFiniteMemoryLLM
            cache_hit: Whether KV-cache was reused
        """
        if not self.enabled:
            return
        
        # Extract metrics
        turn = TurnMetrics(
            timestamp=time.time(),
            tokens_seen=stats.tokens_seen,
            tokens_retained=stats.tokens_retained,
            compression_ratio=stats.compression_ratio,
            policy_latency_ms=stats.policy_latency_ms,
            fallback_occurred=(stats.fallback_count > 0),
            cache_hit=cache_hit,
            evictions=stats.evictions,
        )
        
        self._turns.append(turn)
        
        # Update cumulative
        self.total_turns += 1
        self.total_tokens_seen = stats.tokens_seen
        self.total_tokens_retained = stats.tokens_retained
        self.total_evictions = stats.evictions
        self.total_fallbacks = stats.fallback_count
        
        if cache_hit:
            self.total_cache_hits += 1
        else:
            self.total_cache_misses += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of metrics.
        
        Returns:
            Dictionary of metric summaries
        """
        if not self._turns:
            return {
                "total_turns": 0,
                "uptime_seconds": time.time() - self.start_time,
            }
        
        # Calculate aggregates
        recent_compression = [t.compression_ratio for t in self._turns]
        recent_latency = [t.policy_latency_ms for t in self._turns]
        recent_fallbacks = sum(1 for t in self._turns if t.fallback_occurred)
        recent_cache_hits = sum(1 for t in self._turns if t.cache_hit)
        
        uptime = time.time() - self.start_time
        throughput_tokens = self.total_tokens_seen / max(1, uptime)
        throughput_turns = self.total_turns / max(1, uptime)
        
        cache_hit_rate = (
            self.total_cache_hits / max(1, self.total_cache_hits + self.total_cache_misses)
        )
        
        fallback_rate = recent_fallbacks / max(1, len(self._turns))
        
        # Percentiles
        latency_sorted = sorted(recent_latency)
        n = len(latency_sorted)
        
        return {
            # Cumulative
            "total_turns": self.total_turns,
            "total_tokens_seen": self.total_tokens_seen,
            "total_tokens_retained": self.total_tokens_retained,
            "total_evictions": self.total_evictions,
            "uptime_seconds": uptime,
            
            # Throughput
            "tokens_per_second": throughput_tokens,
            "turns_per_second": throughput_turns,
            
            # Compression (recent window)
            "avg_compression_ratio": sum(recent_compression) / max(1, len(recent_compression)),
            "min_compression_ratio": min(recent_compression) if recent_compression else 1.0,
            "max_compression_ratio": max(recent_compression) if recent_compression else 1.0,
            
            # Latency percentiles (recent window)
            "policy_latency_p50_ms": latency_sorted[n // 2] if latency_sorted else 0.0,
            "policy_latency_p95_ms": latency_sorted[int(n * 0.95)] if latency_sorted else 0.0,
            "policy_latency_p99_ms": latency_sorted[int(n * 0.99)] if latency_sorted else 0.0,
            "policy_latency_max_ms": max(recent_latency) if recent_latency else 0.0,
            
            # Quality
            "fallback_rate": fallback_rate,
            "cache_hit_rate": cache_hit_rate,
            "recent_cache_hits": recent_cache_hits,
            "recent_turns": len(self._turns),
        }
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        summary = self.get_summary()
        
        lines = [
            "# HELP finite_memory_tokens_seen_total Total tokens processed",
            "# TYPE finite_memory_tokens_seen_total counter",
            f"finite_memory_tokens_seen_total {summary['total_tokens_seen']}",
            "",
            "# HELP finite_memory_tokens_retained_total Total tokens retained in memory",
            "# TYPE finite_memory_tokens_retained_total counter",
            f"finite_memory_tokens_retained_total {summary['total_tokens_retained']}",
            "",
            "# HELP finite_memory_compression_ratio Average compression ratio",
            "# TYPE finite_memory_compression_ratio gauge",
            f"finite_memory_compression_ratio {summary['avg_compression_ratio']:.3f}",
            "",
            "# HELP finite_memory_policy_latency_ms Policy execution latency",
            "# TYPE finite_memory_policy_latency_ms summary",
            f"finite_memory_policy_latency_ms{{quantile=\"0.5\"}} {summary['policy_latency_p50_ms']:.2f}",
            f"finite_memory_policy_latency_ms{{quantile=\"0.95\"}} {summary['policy_latency_p95_ms']:.2f}",
            f"finite_memory_policy_latency_ms{{quantile=\"0.99\"}} {summary['policy_latency_p99_ms']:.2f}",
            "",
            "# HELP finite_memory_fallback_rate Policy fallback rate",
            "# TYPE finite_memory_fallback_rate gauge",
            f"finite_memory_fallback_rate {summary['fallback_rate']:.3f}",
            "",
            "# HELP finite_memory_cache_hit_rate KV-cache hit rate",
            "# TYPE finite_memory_cache_hit_rate gauge",
            f"finite_memory_cache_hit_rate {summary['cache_hit_rate']:.3f}",
            "",
            "# HELP finite_memory_uptime_seconds Uptime in seconds",
            "# TYPE finite_memory_uptime_seconds counter",
            f"finite_memory_uptime_seconds {summary['uptime_seconds']:.1f}",
        ]
        
        return "\n".join(lines) + "\n"
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._turns.clear()
        self.total_turns = 0
        self.total_tokens_seen = 0
        self.total_tokens_retained = 0
        self.total_evictions = 0
        self.total_fallbacks = 0
        self.total_cache_hits = 0
        self.total_cache_misses = 0
        self.start_time = time.time()
