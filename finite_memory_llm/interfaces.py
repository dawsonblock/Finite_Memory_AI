"""Lightweight interfaces and base classes - NO heavy imports.

This module contains only abstract base classes and interfaces.
NO torch, NO transformers, NO heavy dependencies.
Import time: <0.01s
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generator


@dataclass
class MemoryStats:
    """Statistics about memory usage and compression."""

    tokens_seen: int = 0
    tokens_retained: int = 0
    evictions: int = 0
    turns: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_count: int = 0
    policy_calls: int = 0
    total_policy_ms: float = 0.0

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if self.tokens_seen == 0:
            return 1.0
        return self.tokens_seen / max(self.tokens_retained, 1)

    @property
    def avg_policy_ms(self) -> float:
        """Calculate average policy execution time."""
        if self.policy_calls == 0:
            return 0.0
        return self.total_policy_ms / self.policy_calls


class LLMBackend(ABC):
    """Abstract base class for LLM backends.
    
    Lightweight interface - implementations can import heavy dependencies.
    """

    @abstractmethod
    def generate(
        self, input_ids: Any, max_new_tokens: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Generate text from input IDs.

        Args:
            input_ids: Input token IDs (implementation-specific type)
            max_new_tokens: Maximum number of new tokens to generate
            **kwargs: Additional generation arguments

        Returns:
            Dictionary with generated sequences
        """
        pass

    @abstractmethod
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs.

        Args:
            text: Text to encode

        Returns:
            List of token IDs
        """
        pass

    @abstractmethod
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text.

        Args:
            tokens: List of token IDs

        Returns:
            Decoded text
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass

    def generate_stream(
        self, input_ids: Any, max_new_tokens: int, **kwargs: Any
    ) -> Generator[dict[str, Any], None, None]:
        """Generate text token by token (optional, for streaming).

        Args:
            input_ids: Input token IDs
            max_new_tokens: Maximum number of new tokens to generate
            **kwargs: Additional generation arguments

        Yields:
            Dictionary with token information
        """
        # Default: non-streaming fallback
        result = self.generate(input_ids, max_new_tokens, **kwargs)
        yield {"sequences": result["sequences"], "is_final": True}


class TelemetryHook(ABC):
    """Abstract base class for telemetry hooks."""

    @abstractmethod
    def on_chat_start(self, message: str) -> None:
        """Called when a chat turn starts."""
        pass

    @abstractmethod
    def on_chat_end(
        self,
        message: str,
        response: str,
        tokens_used: int,
        latency_ms: float,
        stats: MemoryStats,
    ) -> None:
        """Called when a chat turn ends."""
        pass

    @abstractmethod
    def on_eviction(
        self, policy: str, tokens_before: int, tokens_after: int, latency_ms: float
    ) -> None:
        """Called when memory eviction occurs."""
        pass


class PrometheusHook(TelemetryHook):
    """Lightweight Prometheus telemetry hook (no-op if prometheus not available)."""

    def __init__(self):
        """Initialize Prometheus hook."""
        self._available = False
        try:
            # Only import if available
            import prometheus_client  # noqa: F401

            self._available = True
        except ImportError:
            pass

    def on_chat_start(self, message: str) -> None:
        """Called when a chat turn starts."""
        if not self._available:
            return
        # Prometheus implementation would go here

    def on_chat_end(
        self,
        message: str,
        response: str,
        tokens_used: int,
        latency_ms: float,
        stats: MemoryStats,
    ) -> None:
        """Called when a chat turn ends."""
        if not self._available:
            return
        # Prometheus implementation would go here

    def on_eviction(
        self, policy: str, tokens_before: int, tokens_after: int, latency_ms: float
    ) -> None:
        """Called when memory eviction occurs."""
        if not self._available:
            return
        # Prometheus implementation would go here


# Export lightweight interfaces
__all__ = [
    "LLMBackend",
    "MemoryStats",
    "TelemetryHook",
    "PrometheusHook",
]
