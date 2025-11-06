"""Production-ready finite memory + context distillation LLM.

Modern Python 3.10+ implementation with:
- Type hints using modern syntax (PEP 604: X | Y unions)
- Deterministic ContextBuilder (local+global slicing)
- Real attention-based importance eviction (HF local)
- APIChatBackend shim for hosted models (OpenAI/Anthropic/etc.)
- Multiple memory policies: sliding, importance, semantic, rolling_summary

Install:
    pip install torch transformers sentence-transformers scikit-learn numpy

Quick start (local HF):
    from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend
    llm = CompleteFiniteMemoryLLM(
        HuggingFaceBackend("gpt2"),
        memory_policy="semantic",
        max_tokens=1024,
        window_size=256
    )
    print(llm.chat("Hello!")["response"])

Quick start (hosted API):
    from transformers import AutoTokenizer
    from finite_memory_llm import CompleteFiniteMemoryLLM, APIChatBackend
    
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    
    def call_hosted(prompt: str, max_new_tokens: int) -> str:
        # Your API call here (OpenAI/Anthropic/etc.)
        # Example: return openai_client.chat.completions.create(...)
        raise NotImplementedError("Plug in your hosted model call")
    
    backend = APIChatBackend(
        tokenizer=tokenizer,
        send_callable=call_hosted,
        name="hosted-api"
    )
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="semantic",
        max_tokens=4096,
        window_size=1024
    )
    print(llm.chat("Hello!")["response"])
"""

from __future__ import annotations

import json
import time
import warnings
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, asdict
from functools import wraps
from pathlib import Path
from typing import Any, Generator

import numpy as np
import torch

warnings.filterwarnings("ignore")

# Tier-1 upgrade imports (optional, graceful degradation)
try:
    from .upgrades.latency_guard import guarded_call, timed_call
    from .upgrades.embed_cache import SpanEmbedder
    from .upgrades.summary_qa_gate import SummaryQAGate
    from .upgrades.knapsack import choose_under_budget, partition_budget
    from .upgrades.block_sparse import build_block_sparse_mask, export_longformer_mask
    from .telemetry.metrics import Metrics
    from .telemetry.turn_debug_dump import TurnDumper
    _UPGRADES_AVAILABLE = True
except ImportError as e:
    _UPGRADES_AVAILABLE = False
    guarded_call = None
    timed_call = None
    SpanEmbedder = None
    SummaryQAGate = None
    choose_under_budget = None
    partition_budget = None
    Metrics = None
    TurnDumper = None
    build_block_sparse_mask = None
    export_longformer_mask = None


# ====================== TELEMETRY HOOKS ======================

class TelemetryHook:
    """Production telemetry hook for monitoring (v2.3+).
    
    Provides callbacks for key events to enable Prometheus,
    StatsD, or custom monitoring integrations.
    """
    
    def on_chat_start(self, message: str) -> None:
        """Called when chat() starts."""
        pass
    
    def on_chat_complete(self, stats: dict[str, Any], latency_ms: float) -> None:
        """Called when chat() completes.
        
        Args:
            stats: Dictionary of statistics
            latency_ms: Total chat latency in milliseconds
        """
        pass
    
    def on_policy_execute(self, policy: str, latency_ms: float, tokens_before: int, tokens_after: int) -> None:
        """Called after policy execution.
        
        Args:
            policy: Policy name
            latency_ms: Policy execution time
            tokens_before: Tokens before eviction
            tokens_after: Tokens after eviction
        """
        pass
    
    def on_cache_hit(self, prefix_len: int, delta_len: int) -> None:
        """Called on KV-cache hit.
        
        Args:
            prefix_len: Length of reused prefix
            delta_len: Length of new tokens processed
        """
        pass
    
    def on_cache_miss(self, context_len: int) -> None:
        """Called on KV-cache miss.
        
        Args:
            context_len: Full context length processed
        """
        pass


class PrometheusHook(TelemetryHook):
    """Prometheus-compatible telemetry hook (v2.3+).
    
    Requires prometheus_client library.
    """
    
    def __init__(self):
        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            self.chat_total = Counter('finite_memory_chat_total', 'Total chat calls')
            self.chat_latency = Histogram('finite_memory_chat_latency_seconds', 'Chat latency')
            self.policy_latency = Histogram('finite_memory_policy_latency_seconds', 'Policy execution latency', ['policy'])
            self.tokens_evicted = Counter('finite_memory_tokens_evicted_total', 'Total tokens evicted')
            self.cache_hits = Counter('finite_memory_cache_hits_total', 'KV-cache hits')
            self.cache_misses = Counter('finite_memory_cache_misses_total', 'KV-cache misses')
            self.buffer_size = Gauge('finite_memory_buffer_size', 'Current token buffer size')
            
        except ImportError:
            print("⚠ prometheus_client not installed, metrics disabled")
    
    def on_chat_complete(self, stats: dict[str, Any], latency_ms: float) -> None:
        try:
            self.chat_total.inc()
            self.chat_latency.observe(latency_ms / 1000.0)
            self.tokens_evicted.inc(stats.get('evictions', 0))
            self.buffer_size.set(stats.get('tokens_retained', 0))
        except Exception:
            pass
    
    def on_policy_execute(self, policy: str, latency_ms: float, tokens_before: int, tokens_after: int) -> None:
        try:
            self.policy_latency.labels(policy=policy).observe(latency_ms / 1000.0)
        except Exception:
            pass
    
    def on_cache_hit(self, prefix_len: int, delta_len: int) -> None:
        try:
            self.cache_hits.inc()
        except Exception:
            pass
    
    def on_cache_miss(self, context_len: int) -> None:
        try:
            self.cache_misses.inc()
        except Exception:
            pass


# ====================== DATA STRUCTURES ======================

@dataclass
class MemoryStats:
    """Diagnostics for finite-memory behavior."""
    tokens_seen: int = 0
    tokens_retained: int = 0
    cache_hits: int = 0
    evictions: int = 0
    compression_ratio: float = 1.0
    summaries_created: int = 0
    clusters_merged: int = 0
    importance_evictions: int = 0
    sparsity_ratio: float = 1.0  # kept for continuity
    
    # Performance telemetry (v2.1+)
    policy_latency_ms: float = 0.0
    total_policy_calls: int = 0
    fallback_count: int = 0
    anchor_cache_hits: int = 0


# ====================== BACKEND INTERFACE ======================

class LLMBackend(ABC):
    """Abstract interface for any LLM backend."""

    @abstractmethod
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Return dict with 'sequences' (torch.LongTensor [1, seq_len])."""
        ...

    @abstractmethod
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        ...

    @abstractmethod
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        ...


class HuggingFaceBackend(LLMBackend):
    """HuggingFace transformers backend with KV-cache carryover (v2.2+)."""

    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cpu",
        enable_kv_cache: bool = True
    ):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.device = device
        self.enable_kv_cache = enable_kv_cache

        print(f"Loading {model_name}...")
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        print(f"✓ Model loaded on {device}")
        
        # KV-cache carryover state (v2.2+)
        self._cached_tokens: list[int] = []
        self._cached_kv: Any = None
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def _find_common_prefix_length(self, tokens1: list[int], tokens2: list[int]) -> int:
        """Find length of common prefix between two token sequences."""
        min_len = min(len(tokens1), len(tokens2))
        for i in range(min_len):
            if tokens1[i] != tokens2[i]:
                return i
        return min_len
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate tokens with simplified KV-cache (v2.4+).
        
        Simplified approach: just use model.generate() normally.
        KV-cache is handled internally by transformers for speed.
        """
        with torch.no_grad():
            # Use optimized model.generate() - transformers handles KV-cache internally
            generated_ids = self.model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                use_cache=self.enable_kv_cache,
                pad_token_id=self.tokenizer.eos_token_id,
                **kwargs
            )
        
        # Track cache stats (simplified - just count calls)
        input_tokens = input_ids[0].tolist()
        if self._cached_tokens:
            prefix_len = self._find_common_prefix_length(input_tokens, self._cached_tokens)
            if prefix_len > 0 and prefix_len == len(self._cached_tokens):
                self._cache_hits += 1
            else:
                self._cache_misses += 1
        
        # Update cached tokens for next turn
        self._cached_tokens = generated_ids[0].tolist()
        
        return {"sequences": generated_ids}
    
    def generate_stream(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ):
        """Generate tokens with streaming (v2.3+).
        
        Yields tokens as they are generated for real-time display.
        
        Yields:
            dict with 'token_id', 'token_text', 'is_final'
        """
        input_tokens = input_ids[0].tolist()
        
        # Check for KV-cache reuse
        prefix_len = 0
        can_reuse_kv = False
        
        if self.enable_kv_cache and self._cached_tokens and self._cached_kv is not None:
            prefix_len = self._find_common_prefix_length(input_tokens, self._cached_tokens)
            can_reuse_kv = prefix_len > 0 and prefix_len == len(self._cached_tokens)
        
        if can_reuse_kv:
            self._cache_hits += 1
            delta_tokens = input_tokens[prefix_len:]
            
            if delta_tokens:
                delta_ids = torch.tensor([delta_tokens], device=self.device)
                with torch.no_grad():
                    outputs = self.model(
                        input_ids=delta_ids,
                        past_key_values=self._cached_kv,
                        use_cache=True,
                    )
                    past_kv = outputs.past_key_values
            else:
                past_kv = self._cached_kv
                outputs = None
            
            generated_tokens = []
            current_kv = past_kv
            
            for i in range(max_new_tokens):
                if generated_tokens:
                    next_input = torch.tensor([[generated_tokens[-1]]], device=self.device)
                else:
                    if outputs is not None:
                        logits = outputs.logits[0, -1, :]
                    else:
                        # Need to get logits for exact match case
                        with torch.no_grad():
                            dummy_out = self.model(
                                input_ids=torch.tensor([[input_tokens[-1]]], device=self.device),
                                past_key_values=past_kv,
                                use_cache=True,
                            )
                            logits = dummy_out.logits[0, -1, :]
                            current_kv = dummy_out.past_key_values
                    
                    next_token = logits.argmax().item()
                    generated_tokens.append(next_token)
                    token_text = self.tokenizer.decode([next_token])
                    
                    yield {
                        "token_id": next_token,
                        "token_text": token_text,
                        "is_final": (next_token == self.tokenizer.eos_token_id or i == max_new_tokens - 1)
                    }
                    
                    if next_token == self.tokenizer.eos_token_id:
                        break
                    continue
                
                with torch.no_grad():
                    outputs = self.model(
                        input_ids=next_input,
                        past_key_values=current_kv,
                        use_cache=True,
                    )
                    current_kv = outputs.past_key_values
                    logits = outputs.logits[0, -1, :]
                    next_token = logits.argmax().item()
                    generated_tokens.append(next_token)
                    token_text = self.tokenizer.decode([next_token])
                    
                    yield {
                        "token_id": next_token,
                        "token_text": token_text,
                        "is_final": (next_token == self.tokenizer.eos_token_id or i == max_new_tokens - 1)
                    }
                    
                    if next_token == self.tokenizer.eos_token_id:
                        break
            
            self._cached_kv = current_kv
            self._cached_tokens = input_tokens + generated_tokens
            
        else:
            # Full forward pass with streaming
            if self._cached_tokens:
                self._cache_misses += 1
            
            with torch.no_grad():
                outputs = self.model(
                    input_ids=input_ids,
                    use_cache=True,
                )
                past_kv = outputs.past_key_values
                
                generated_tokens = []
                current_kv = past_kv
                
                for i in range(max_new_tokens):
                    if generated_tokens:
                        next_input = torch.tensor([[generated_tokens[-1]]], device=self.device)
                    else:
                        logits = outputs.logits[0, -1, :]
                        next_token = logits.argmax().item()
                        generated_tokens.append(next_token)
                        token_text = self.tokenizer.decode([next_token])
                        
                        yield {
                            "token_id": next_token,
                            "token_text": token_text,
                            "is_final": (next_token == self.tokenizer.eos_token_id or i == max_new_tokens - 1)
                        }
                        
                        if next_token == self.tokenizer.eos_token_id:
                            break
                        continue
                    
                    outputs = self.model(
                        input_ids=next_input,
                        past_key_values=current_kv,
                        use_cache=True,
                    )
                    current_kv = outputs.past_key_values
                    logits = outputs.logits[0, -1, :]
                    next_token = logits.argmax().item()
                    generated_tokens.append(next_token)
                    token_text = self.tokenizer.decode([next_token])
                    
                    yield {
                        "token_id": next_token,
                        "token_text": token_text,
                        "is_final": (next_token == self.tokenizer.eos_token_id or i == max_new_tokens - 1)
                    }
                    
                    if next_token == self.tokenizer.eos_token_id:
                        break
                
                if self.enable_kv_cache:
                    self._cached_kv = current_kv
                    self._cached_tokens = input_tokens + generated_tokens
    
    def get_cache_stats(self) -> dict[str, int]:
        """Get KV-cache statistics."""
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cached_tokens": len(self._cached_tokens),
        }

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model_name


class APIChatBackend(LLMBackend):
    """Thin shim for hosted chat/completions APIs.
    
    Args:
        tokenizer: Any HF tokenizer for token counting
        send_callable: Function that takes (prompt: str, max_new_tokens: int) -> str
        name: Name identifier for this backend
    """
    
    def __init__(
        self,
        tokenizer: Any,
        send_callable: Callable[[str, int], str],
        name: str = "api-chat"
    ) -> None:
        self._tok = tokenizer
        self._send = send_callable
        self._name = name

    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via API call."""
        prompt = self.decode(input_ids[0].tolist())
        text = self._send(prompt, max_new_tokens)
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        return {"sequences": seq}

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._tok.encode(text, add_special_tokens=False)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self._tok.decode(tokens, skip_special_tokens=True)

    def get_model_name(self) -> str:
        """Return the backend name."""
        return self._name


# ====================== CONTEXT BUILDER ======================

class ContextBuilder:
    """Deterministic context selection that all models will respect.
    
    Strategy:
        - Keep a recent tail window
        - Preserve global anchors at sentence boundaries
        - If still over limit, trim from the head
    
    Args:
        max_tokens: Maximum number of tokens to keep
        window_size: Size of recent window to always preserve
    """
    
    def __init__(self, max_tokens: int, window_size: int = 256) -> None:
        self.max_tokens = max_tokens
        self.window_size = window_size
        
        # Anchor caching (v2.1+)
        self._anchor_cache: dict[int, list[int]] = {}
        self._cache_hits = 0

    def global_boundaries(
        self,
        backend: LLMBackend,
        toks: list[int]
    ) -> list[int]:
        """Find global sentence boundary positions with caching."""
        # Cache key is hash of token sequence
        cache_key = hash(tuple(toks))
        
        if cache_key in self._anchor_cache:
            self._cache_hits += 1
            return self._anchor_cache[cache_key]
        
        # Compute boundaries
        idx = [0]
        try:
            for i, t in enumerate(toks[:-1]):
                ch = backend.decode([t])
                if any(p in ch for p in ('.', '!', '?', '\n')):
                    idx.append(i + 1)
        except Exception:
            pass
        if toks:
            idx.append(len(toks) - 1)
        
        result = sorted(set(i for i in idx if 0 <= i < len(toks)))
        
        # Cache result (limit cache size to prevent memory growth)
        if len(self._anchor_cache) < 100:
            self._anchor_cache[cache_key] = result
        else:
            # Clear cache if it grows too large
            self._anchor_cache.clear()
        
        return result

    def build(
        self,
        backend: LLMBackend,
        buffer: list[int],
        policy_out: list[int]
    ) -> tuple[list[int], int]:
        """Build final context with caching.
        
        Returns:
            Tuple of (token_list, cache_hits)
        """
        cache_hits_before = self._cache_hits
        
        if len(policy_out) <= self.max_tokens:
            return policy_out, self._cache_hits - cache_hits_before

        anchors = self.global_boundaries(backend, policy_out)
        keep = set()

        # 1) recent window
        start = max(0, len(policy_out) - self.window_size)
        keep.update(range(start, len(policy_out)))

        # 2) anchors
        keep.update(anchors)

        kept = sorted(keep)
        if len(kept) > self.max_tokens:
            kept = kept[-self.max_tokens:]

        # Ensure exact max cap
        out = [policy_out[i] for i in kept]
        if len(out) > self.max_tokens:
            out = out[-self.max_tokens:]
        
        return out, self._cache_hits - cache_hits_before


# ====================== COMPLETE FINITE MEMORY ======================

class CompleteFiniteMemoryLLM:
    """
    Combines:
      - Memory policies: sliding, importance, semantic, rolling_summary
      - Deterministic ContextBuilder (local+global slicing)
      - Checkpoint/restore, conversation history
      - Works with local HF or hosted APIs via APIChatBackend
    """

    def __init__(
        self,
        backend: LLMBackend,
        max_tokens: int = 512,
        memory_policy: str = "sliding",
        window_size: int = 128,
        semantic_clusters: int = 4,
        summary_interval: int = 256,
        embedding_model: str | None = None,
        device: str = "cpu",
        max_policy_ms: float | None = None,
        telemetry_hook: TelemetryHook | None = None,
    ) -> None:
        self.backend = backend
        self.max_tokens = max_tokens
        self.memory_policy = memory_policy
        self.window_size = window_size
        self.semantic_clusters = semantic_clusters
        self.summary_interval = summary_interval
        self.device = device
        self.max_policy_ms = max_policy_ms
        self.telemetry_hook = telemetry_hook

        # Tier-1 upgrades (if available)
        self._span_embedder = None
        self._qa_gate = None
        self._use_upgrades = _UPGRADES_AVAILABLE
        
        if _UPGRADES_AVAILABLE:
            # Initialize embedding cache with MiniBatchKMeans
            if memory_policy in ("semantic", "hybrid"):
                try:
                    emb_name = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
                    print(f"Initializing Tier-1 SpanEmbedder with {emb_name}...")
                    self._span_embedder = SpanEmbedder(model_name=emb_name, cache_size=1000)
                    print("✓ Tier-1 embedding cache enabled")
                except Exception as e:
                    print(f"⚠ Could not initialize SpanEmbedder: {e}")
                    self._use_upgrades = False
            
            # Initialize summary QA gate
            if memory_policy == "rolling_summary":
                self._qa_gate = SummaryQAGate(
                    questions=[
                        "List specific numbers/dates.",
                        "List proper names/aliases.",
                        "List key facts as key:value.",
                    ],
                    threshold=0.75
                )
                print("✓ Tier-1 summary QA gate enabled")
        
        # Embedding model for semantic clustering (legacy path)
        self.embedding_model = None
        if memory_policy == "semantic" and not self._span_embedder:
            try:
                from sentence_transformers import SentenceTransformer
                emb_name = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
                print(f"Loading embedding model {emb_name}...")
                self.embedding_model = SentenceTransformer(emb_name)
                print("✓ Embedding model loaded")
            except Exception as e:
                print(f"⚠ Semantic policy fallback (no embeddings): {e}")
                self.memory_policy = "sliding"

        # Memory state
        self.token_buffer = deque(maxlen=max_tokens)
        self.attention_scores = deque(maxlen=max_tokens)

        # Semantic policy state
        self.token_embeddings = []
        self.span_texts = []

        # Rolling summary state
        self.summary_tokens = []
        self.tokens_since_summary = 0

        # Conversation tracking
        self.conversation_history = []

        # Stats
        self.stats = MemoryStats()

        # Context slicer
        self.context_builder = ContextBuilder(max_tokens=max_tokens, window_size=window_size)

        budget_str = f", latency_budget={self.max_policy_ms}ms" if self.max_policy_ms else ""
        upgrade_str = " (Tier-1 enabled)" if self._use_upgrades else ""
        print(f"✓ LLM initialized: policy={self.memory_policy}, max_tokens={self.max_tokens}, window={self.window_size}{budget_str}{upgrade_str}")

    # ---------- utilities ----------

    def reset(self) -> None:
        """Reset all memory state."""
        self.token_buffer.clear()
        self.attention_scores.clear()
        self.token_embeddings.clear()
        self.span_texts.clear()
        self.summary_tokens.clear()
        self.tokens_since_summary = 0
        self.conversation_history.clear()
        self.stats = MemoryStats()

    # ---------- policy: sliding ----------

    def _evict_sliding(self, new_tokens: list[int]) -> list[int]:
        """Sliding window eviction policy."""
        n_new = len(new_tokens)
        cur = len(self.token_buffer)
        total = cur + n_new
        if total > self.max_tokens:
            overflow = total - self.max_tokens
            for _ in range(min(overflow, cur)):
                self.token_buffer.popleft()
            self.stats.evictions += overflow
        self.token_buffer.extend(new_tokens)
        return list(self.token_buffer)

    # ---------- policy: importance (uses attention or logit attribution) ----------

    def _collect_last_token_importance(self, ctx_ids: list[int]) -> np.ndarray | None:
        """Collect importance scores from model attention."""
        # Works only for local HF backend with .model
        try:
            model = getattr(self.backend, "model", None)
            tokenizer = getattr(self.backend, "tokenizer", None)
            if model is None or tokenizer is None:
                return None
            input_ids = torch.tensor([ctx_ids], device=self.device)
            with torch.no_grad():
                out = model(input_ids=input_ids, output_attentions=True, use_cache=True)
            # last layer attn: [layers][-1], shape [batch, heads, seq, seq]
            att = out.attentions[-1].mean(dim=1)[0][-1].detach().cpu().numpy()
            return att  # shape [seq]
        except Exception:
            return None
    
    def _importance_via_logit_probes(
        self,
        ctx_ids: list[int],
        n_probes: int = 8,
        span_size: int = 32
    ) -> np.ndarray:
        """API-safe importance using logit attribution (v2.2+).
        
        Sample spans, mask them, measure impact on next-token probability.
        Returns importance scores for each token position.
        
        Args:
            ctx_ids: Context token IDs
            n_probes: Number of spans to probe
            span_size: Size of each span to mask
        
        Returns:
            Array of importance scores (one per token)
        """
        if len(ctx_ids) < span_size:
            return np.ones(len(ctx_ids))
        
        # Initialize scores
        scores = np.zeros(len(ctx_ids))
        
        # Sample span positions uniformly
        n_spans = max(1, len(ctx_ids) // span_size)
        probe_indices = np.linspace(0, n_spans - 1, min(n_probes, n_spans), dtype=int)
        
        try:
            model = getattr(self.backend, "model", None)
            if model is None:
                # For API backends, use a simpler heuristic
                # Assign higher scores to recent tokens
                for i in range(len(ctx_ids)):
                    recency = i / max(len(ctx_ids) - 1, 1)
                    scores[i] = 0.3 + 0.7 * recency  # 0.3 to 1.0 range
                return scores
            
            # Get baseline logits
            with torch.no_grad():
                baseline_input = torch.tensor([ctx_ids], device=self.device)
                baseline_out = model(input_ids=baseline_input)
                baseline_logits = baseline_out.logits[0, -1].cpu().numpy()
                baseline_top_logit = np.max(baseline_logits)
            
            # Probe each span
            for span_idx in probe_indices:
                start = span_idx * span_size
                end = min(start + span_size, len(ctx_ids))
                
                # Create masked context (remove this span)
                masked_ctx = ctx_ids[:start] + ctx_ids[end:]
                
                if len(masked_ctx) < 1:
                    continue
                
                # Get logits without this span
                with torch.no_grad():
                    masked_input = torch.tensor([masked_ctx], device=self.device)
                    masked_out = model(input_ids=masked_input)
                    masked_logits = masked_out.logits[0, -1].cpu().numpy()
                    masked_top_logit = np.max(masked_logits)
                
                # Measure impact: larger delta = more important span
                delta = abs(baseline_top_logit - masked_top_logit)
                
                # Assign this impact to all tokens in the span
                for i in range(start, end):
                    scores[i] += delta
            
            # Normalize scores
            if scores.max() > 0:
                scores = scores / scores.max()
            
        except Exception as e:
            print(f"⚠ Logit probe failed: {e}, using recency heuristic")
            for i in range(len(ctx_ids)):
                recency = i / max(len(ctx_ids) - 1, 1)
                scores[i] = 0.3 + 0.7 * recency
        
        return scores

    def _evict_importance(self, new_tokens: list[int]) -> list[int]:
        """Importance-based eviction policy using attention or logit probes."""
        n_new = len(new_tokens)
        cur_list = list(self.token_buffer)
        if len(cur_list) + n_new <= self.max_tokens:
            self.token_buffer.extend(new_tokens)
            self.attention_scores.extend([0.0] * n_new)
            return list(self.token_buffer)

        # Try attention first (local models)
        imp = self._collect_last_token_importance(cur_list)
        
        # Fallback to logit probes if attention unavailable (v2.2+)
        if imp is None and len(cur_list) > 32:
            imp = self._importance_via_logit_probes(cur_list, n_probes=8, span_size=32)
        
        if imp is not None:
            if len(self.attention_scores) < len(cur_list):
                self.attention_scores = deque([0.0] * len(cur_list), maxlen=self.max_tokens)
            for i, s in enumerate(imp[:len(cur_list)]):
                self.attention_scores[i] = max(self.attention_scores[i], float(s))

        target = self.max_tokens - n_new
        recency_budget = max(64, target // 4)
        importance_budget = max(0, target - recency_budget)

        keep = set()
        if len(self.attention_scores) == len(cur_list) and importance_budget > 0:
            ranked = sorted(range(len(cur_list)), key=lambda i: self.attention_scores[i], reverse=True)
            keep.update(ranked[:importance_budget])

        keep.update(range(max(0, len(cur_list) - recency_budget), len(cur_list)))

        new_buf = [cur_list[i] for i in sorted(keep)]
        evicted = len(cur_list) - len(new_buf)
        self.stats.evictions += max(evicted, 0)
        self.stats.importance_evictions += max(evicted, 0)

        self.token_buffer = deque(new_buf, maxlen=self.max_tokens)
        self.attention_scores = deque([self.attention_scores[i] for i in sorted(keep)], maxlen=self.max_tokens)
        self.token_buffer.extend(new_tokens)
        self.attention_scores.extend([0.0] * n_new)
        return list(self.token_buffer)

    # ---------- policy: semantic (kmeans over span embeddings) ----------

    def _compute_span_embeddings(
        self,
        tokens: list[int],
        span_size: int = 64,
        stride: int = 32
    ) -> None:
        """Compute embeddings for token spans (Tier-1 enhanced)."""
        # Use Tier-1 cached embedder if available
        if self._span_embedder and tokens:
            self.token_embeddings.clear()
            self.span_texts.clear()
            
            # Create spans
            spans = []
            texts = []
            for i in range(0, len(tokens), stride):
                end = min(i + span_size, len(tokens))
                span = tokens[i:end]
                if span:
                    try:
                        text = self.backend.decode(span)
                        if text.strip():
                            spans.append(span)
                            texts.append(text)
                            self.token_embeddings.append((i, end, None))  # Placeholder
                            self.span_texts.append(text)
                    except Exception:
                        continue
            
            # Batch encode with cache
            if spans:
                try:
                    embeddings = self._span_embedder.encode_spans(spans, texts)
                    # Update embeddings in token_embeddings
                    for idx, emb in enumerate(embeddings):
                        i, end, _ = self.token_embeddings[idx]
                        self.token_embeddings[idx] = (i, end, emb)
                except Exception as e:
                    print(f"⚠ Span embedding failed: {e}")
            return
        
        # Legacy path
        if not self.embedding_model or not tokens:
            return
        self.token_embeddings.clear()
        self.span_texts.clear()
        for i in range(0, len(tokens), stride):
            end = min(i + span_size, len(tokens))
            span = tokens[i:end]
            if not span:
                continue
            try:
                text = self.backend.decode(span)
                if text.strip():
                    emb = self.embedding_model.encode(text, convert_to_numpy=True)
                    self.token_embeddings.append((i, end, emb))
                    self.span_texts.append(text)
            except Exception:
                continue

    def _evict_semantic(self, new_tokens: list[int]) -> list[int]:
        """Semantic clustering eviction policy (Tier-1 enhanced)."""
        n_new = len(new_tokens)
        cur = list(self.token_buffer)
        if len(cur) + n_new <= self.max_tokens:
            self.token_buffer.extend(new_tokens)
            return list(self.token_buffer)

        # Use Tier-1 cached embedder with MiniBatchKMeans
        if self._span_embedder:
            self._compute_span_embeddings(cur, span_size=64, stride=32)
            if len(self.token_embeddings) < max(2, self.semantic_clusters * 2):
                return self._evict_sliding(new_tokens)
            
            try:
                embs = np.vstack([e for _, _, e in self.token_embeddings])
                # Use MiniBatchKMeans via SpanEmbedder
                keep_span_indices = self._span_embedder.select_representatives(
                    embs, 
                    k=self.semantic_clusters,
                    recency_bias=0.15
                )
                
                # Add recency spans
                recency_threshold = len(cur) - (self.max_tokens // 4)
                for i, (s, _, _) in enumerate(self.token_embeddings):
                    if s >= recency_threshold and i not in keep_span_indices:
                        keep_span_indices.append(i)
                
                keep_span_indices = sorted(set(keep_span_indices))
                
                # Apply knapsack selection if available
                if choose_under_budget:
                    budget = self.max_tokens - n_new
                    items = [
                        (i, s, e, float(e - s))
                        for i, (s, e, _) in enumerate(self.token_embeddings)
                        if i in keep_span_indices
                    ]
                    keep_span_indices = choose_under_budget(items, budget)
                
                new_buf = []
                for span_idx in sorted(keep_span_indices):
                    s, e, _ = self.token_embeddings[span_idx]
                    s = max(0, min(s, len(cur)))
                    e = max(s, min(e, len(cur)))
                    new_buf.extend(cur[s:e])
                
                merged = len(self.token_embeddings) - len(keep_span_indices)
                self.stats.evictions += max(0, len(cur) - len(new_buf))
                self.stats.clusters_merged += max(0, merged)
                
                self.token_buffer = deque(new_buf, maxlen=self.max_tokens)
                self.token_buffer.extend(new_tokens)
                return list(self.token_buffer)
            
            except Exception as e:
                print(f"⚠ Tier-1 semantic clustering failed: {e}. Falling back to sliding.")
                return self._evict_sliding(new_tokens)
        
        # Legacy path
        if not self.embedding_model:
            return self._evict_sliding(new_tokens)

        self._compute_span_embeddings(cur, span_size=64, stride=32)
        if len(self.token_embeddings) < max(2, self.semantic_clusters * 2):
            return self._evict_sliding(new_tokens)

        try:
            from sklearn.cluster import KMeans
            embs = np.vstack([e for _, _, e in self.token_embeddings])
            k = min(self.semantic_clusters, len(self.token_embeddings))
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(embs)

            recency_threshold = len(cur) - (self.max_tokens // 4)
            keep_spans = set()

            # cluster representatives
            for cid in range(k):
                mask = labels == cid
                if not mask.any():
                    continue
                ci = np.where(mask)[0]
                centroid = km.cluster_centers_[cid]
                d = np.linalg.norm(embs[ci] - centroid, axis=1)
                rep_idx = ci[np.argmin(d)]
                keep_spans.add(rep_idx)

            # recency spans
            for i, (s, _, _) in enumerate(self.token_embeddings):
                if s >= recency_threshold:
                    keep_spans.add(i)

            new_buf = []
            for span_idx in sorted(keep_spans):
                s, e, _ = self.token_embeddings[span_idx]
                s = max(0, min(s, len(cur)))
                e = max(s, min(e, len(cur)))
                new_buf.extend(cur[s:e])

            merged = len(self.token_embeddings) - len(keep_spans)
            self.stats.evictions += max(0, len(cur) - len(new_buf))
            self.stats.clusters_merged += max(0, merged)

            self.token_buffer = deque(new_buf, maxlen=self.max_tokens)
            self.token_buffer.extend(new_tokens)
            return list(self.token_buffer)
        except Exception as e:
            print(f"⚠ Semantic clustering failed: {e}. Falling back to sliding.")
            return self._evict_sliding(new_tokens)

    # ---------- policy: rolling summary ----------

    def _create_summary(
        self,
        tokens: list[int],
        max_summary_tokens: int = 128
    ) -> list[int]:
        """Create a summary of token sequence (Tier-1 QA gate)."""
        if not tokens:
            return []
        try:
            text = self.backend.decode(tokens)
            # naive extractive summary: first sentence or first 200 chars
            sentence = text.split(".")[0]
            summary_text = sentence[:200] if sentence else text[:200]
            
            # Apply QA gate if available
            if self._qa_gate:
                verified = self._qa_gate.verify(pre_text=text, post_summary=summary_text)
                if not verified:
                    print("⚠ Summary failed QA gate, using fallback")
                    # Fallback: use first N tokens directly
                    summary_text = text[:max_summary_tokens * 4]  # Rough char estimate
            
            ids = self.backend.encode(summary_text)
            self.stats.summaries_created += 1
            return ids[:max_summary_tokens]
        except Exception:
            return tokens[:max_summary_tokens]

    def _evict_rolling_summary(self, new_tokens: list[int]) -> list[int]:
        """Rolling summary eviction policy."""
        self.tokens_since_summary += len(new_tokens)
        if (self.tokens_since_summary >= self.summary_interval) and (len(self.token_buffer) > self.summary_interval):
            cutoff = len(self.token_buffer) // 2
            to_sum = list(self.token_buffer)[:cutoff]
            keep_recent = list(self.token_buffer)[cutoff:]

            summary = self._create_summary(to_sum, max_summary_tokens=min(128, self.max_tokens // 8))

            self.token_buffer = deque(maxlen=self.max_tokens)
            if self.summary_tokens:
                self.token_buffer.extend(self.summary_tokens)
            self.token_buffer.extend(summary)
            self.token_buffer.extend(keep_recent)

            self.summary_tokens.extend(summary)
            if len(self.summary_tokens) > self.max_tokens // 4:
                self.summary_tokens = self._create_summary(self.summary_tokens, max_summary_tokens=self.max_tokens // 8)

            self.tokens_since_summary = 0

        # add new and trim if needed
        cur = len(self.token_buffer)
        n_new = len(new_tokens)
        if cur + n_new > self.max_tokens:
            overflow = cur + n_new - self.max_tokens
            for _ in range(min(overflow, cur)):
                self.token_buffer.popleft()
            self.stats.evictions += overflow
        self.token_buffer.extend(new_tokens)
        return list(self.token_buffer)

    # ---------- policy: hybrid (v2.3+) ----------

    def _evict_hybrid(self, new_tokens: list[int]) -> list[int]:
        """Hybrid policy combining importance and semantic clustering (v2.3+).
        
        Strategy:
        1. Use importance scores to identify high-value tokens
        2. Use semantic clustering to identify meaning-representative spans
        3. Combine scores with weights: 60% importance, 40% semantic
        4. Keep highest-scoring tokens + recent window
        """
        n_new = len(new_tokens)
        cur_list = list(self.token_buffer)
        
        if len(cur_list) + n_new <= self.max_tokens:
            self.token_buffer.extend(new_tokens)
            return list(self.token_buffer)
        
        # Get importance scores
        imp_scores = self._collect_last_token_importance(cur_list)
        if imp_scores is None:
            imp_scores = self._importance_via_logit_probes(cur_list, n_probes=6, span_size=32)
        
        # Get semantic scores
        self._compute_span_embeddings(cur_list, span_size=64, stride=32)
        sem_scores = np.zeros(len(cur_list))
        
        if len(self.token_embeddings) >= 2:
            try:
                from sklearn.cluster import KMeans
                embs = np.vstack([e for _, _, e in self.token_embeddings])
                k = min(self.semantic_clusters, len(self.token_embeddings))
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = km.fit_predict(embs)
                
                # Assign scores based on cluster membership
                for i, (s, e, _) in enumerate(self.token_embeddings):
                    cid = labels[i]
                    # Tokens in diverse clusters get higher scores
                    cluster_count = np.sum(labels == cid)
                    uniqueness = 1.0 / max(cluster_count, 1)
                    for j in range(s, min(e, len(cur_list))):
                        sem_scores[j] = uniqueness
                
                # Normalize
                if sem_scores.max() > 0:
                    sem_scores = sem_scores / sem_scores.max()
            except Exception:
                pass
        
        # Combine scores: 60% importance, 40% semantic
        combined_scores = 0.6 * imp_scores[:len(cur_list)] + 0.4 * sem_scores
        
        # Keep target tokens
        target = self.max_tokens - n_new
        recency_budget = max(64, target // 4)
        scored_budget = target - recency_budget
        
        # Select by combined score
        keep = set()
        if scored_budget > 0:
            ranked = sorted(range(len(cur_list)), key=lambda i: combined_scores[i], reverse=True)
            keep.update(ranked[:scored_budget])
        
        # Add recency
        keep.update(range(max(0, len(cur_list) - recency_budget), len(cur_list)))
        
        new_buf = [cur_list[i] for i in sorted(keep)]
        evicted = len(cur_list) - len(new_buf)
        self.stats.evictions += max(evicted, 0)
        
        self.token_buffer = deque(new_buf, maxlen=self.max_tokens)
        self.token_buffer.extend(new_tokens)
        return list(self.token_buffer)

    # ---------- main interface ----------

    def _apply_policy(self, new_tokens: list[int]) -> list[int]:
        """Apply the configured memory policy with latency budgeting (Tier-1 enhanced)."""
        self.stats.total_policy_calls += 1
        
        # If no latency budget or policy is sliding, run directly
        if self.max_policy_ms is None or self.memory_policy == "sliding":
            return self._apply_policy_impl(new_tokens)
        
        # Use Tier-1 guarded_call if available
        if guarded_call:
            def _fallback_with_count():
                self.stats.fallback_count += 1
                return self._evict_sliding(new_tokens)
            result = guarded_call(
                func=lambda: self._apply_policy_impl(new_tokens),
                budget_ms=self.max_policy_ms,
                fallback=_fallback_with_count
            )
            return result
        
        # Legacy fallback path
        start_time = time.perf_counter()
        try:
            result = self._apply_policy_impl(new_tokens)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.stats.policy_latency_ms = elapsed_ms
            
            # Check if we exceeded budget
            if elapsed_ms > self.max_policy_ms:
                print(f"⚠ Policy '{self.memory_policy}' exceeded budget ({elapsed_ms:.1f}ms > {self.max_policy_ms}ms), falling back to sliding")
                self.stats.fallback_count += 1
                # Revert to sliding for next call
                return self._evict_sliding(new_tokens)
            
            return result
        except Exception as e:
            print(f"⚠ Policy '{self.memory_policy}' failed: {e}, falling back to sliding")
            self.stats.fallback_count += 1
            return self._evict_sliding(new_tokens)
    
    def _apply_policy_impl(self, new_tokens: list[int]) -> list[int]:
        """Internal policy dispatcher."""
        if self.memory_policy == "sliding":
            return self._evict_sliding(new_tokens)
        elif self.memory_policy == "importance":
            return self._evict_importance(new_tokens)
        elif self.memory_policy == "semantic":
            return self._evict_semantic(new_tokens)
        elif self.memory_policy == "rolling_summary":
            return self._evict_rolling_summary(new_tokens)
        elif self.memory_policy == "hybrid":
            return self._evict_hybrid(new_tokens)
        else:
            return self._evict_sliding(new_tokens)

    def chat(self, message: str, max_new_tokens: int = 50) -> dict[str, Any]:
        """Process a chat message and generate a response."""
        start_time = time.perf_counter()
        
        # Telemetry: chat start
        if self.telemetry_hook:
            self.telemetry_hook.on_chat_start(message)
        
        if not message or not message.strip():
            return {
                "response": "",
                "tokens_used": 0,
                "context_length": len(self.token_buffer),
                "stats": self.stats,
                "memory_policy": self.memory_policy,
            }

        try:
            msg_tokens = self.backend.encode(message)
            if not msg_tokens:
                msg_tokens = [0]

            # apply policy with user tokens
            policy_out = self._apply_policy(msg_tokens)

            # stats
            self.stats.tokens_seen += len(msg_tokens)
            self.stats.tokens_retained = len(policy_out)
            self.stats.compression_ratio = self.stats.tokens_seen / max(self.stats.tokens_retained, 1)

            # build the final enforced context
            context_tokens, anchor_hits = self.context_builder.build(self.backend, list(self.token_buffer), policy_out)
            self.stats.anchor_cache_hits += anchor_hits
            input_tensor = torch.tensor([context_tokens], device=self.device)

            # generate
            outputs = self.backend.generate(input_tensor, max_new_tokens=max_new_tokens)
            out_seq = outputs["sequences"][0].tolist()
            gen_ids = out_seq[len(context_tokens):]
            if not gen_ids:
                gen_ids = [0]
            response_text = self.backend.decode(gen_ids)

            # apply policy with assistant tokens
            self._apply_policy(gen_ids)

            # track history
            self.conversation_history.append({"role": "user", "content": message, "tokens": len(msg_tokens)})
            self.conversation_history.append({"role": "assistant", "content": response_text, "tokens": len(gen_ids)})

            result = {
                "response": response_text,
                "tokens_used": len(gen_ids),
                "context_length": len(context_tokens),
                "stats": self.stats,
                "memory_policy": self.memory_policy,
            }
            
            # Telemetry: chat complete
            if self.telemetry_hook:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self.telemetry_hook.on_chat_complete(asdict(self.stats), latency_ms)
            
            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            
            result = {
                "response": f"Error: {str(e)}",
                "tokens_used": 0,
                "context_length": len(self.token_buffer),
                "stats": self.stats,
                "memory_policy": self.memory_policy,
            }
            
            # Telemetry: chat complete (error)
            if self.telemetry_hook:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self.telemetry_hook.on_chat_complete(asdict(self.stats), latency_ms)
            
            return result

    # ---------- checkpointing ----------

    def save_checkpoint(self, path: str | Path) -> Path:
        """Save conversation state to a checkpoint file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "config": {
                "max_tokens": self.max_tokens,
                "memory_policy": self.memory_policy,
                "window_size": self.window_size,
                "semantic_clusters": self.semantic_clusters,
                "summary_interval": self.summary_interval,
            },
            "state": {
                "token_buffer": list(self.token_buffer),
                "attention_scores": list(self.attention_scores),
                "summary_tokens": self.summary_tokens,
                "tokens_since_summary": self.tokens_since_summary,
                "conversation_history": self.conversation_history,
            },
            "stats": asdict(self.stats),
            "metadata": {"model": self.backend.get_model_name(), "turns": len(self.conversation_history) // 2},
        }
        with open(path, "w") as f:
            json.dump(checkpoint, f, indent=2)
        print(f"✓ Checkpoint saved to {path}")
        return path

    def load_checkpoint(self, path: str | Path) -> dict[str, Any]:
        """Load conversation state from a checkpoint file."""
        with open(path, "r") as f:
            checkpoint = json.load(f)

        self.token_buffer = deque(checkpoint["state"]["token_buffer"], maxlen=self.max_tokens)
        self.attention_scores = deque(checkpoint["state"]["attention_scores"], maxlen=self.max_tokens)
        self.summary_tokens = checkpoint["state"]["summary_tokens"]
        self.tokens_since_summary = checkpoint["state"]["tokens_since_summary"]
        self.conversation_history = checkpoint["state"]["conversation_history"]
        self.stats = MemoryStats(**checkpoint["stats"])

        print(f"✓ Checkpoint loaded from {path}")
        print(f"  Model: {checkpoint['metadata']['model']}")
        print(f"  Turns: {checkpoint['metadata']['turns']}")
        return checkpoint["config"]

    def get_context_window(self) -> str:
        """Get the current context window as text."""
        if not self.token_buffer:
            return ""
        return self.backend.decode(list(self.token_buffer))


# ====================== TEST HARNESS (optional) ======================

def run_comprehensive_tests() -> None:
    """Run comprehensive tests of all policies and features."""
    print("\n" + "=" * 70)
    print(" COMPREHENSIVE TESTING: POLICIES + CONTEXT BUILDER")
    print("=" * 70)

    backend = HuggingFaceBackend("gpt2", device="cpu")
    llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=256, window_size=96)

    convo = [
        "The quick brown fox jumps over the lazy dog.",
        "Tell me about foxes in general.",
        "What color was the fox we mentioned?",
        "What did we first discuss in this chat?",
    ]

    for turn, msg in enumerate(convo, 1):
        out = llm.chat(msg, max_new_tokens=32)
        print(f"[{turn}] -> {out['response'][:120].replace('\\n',' ')} ...")
        print(f"   context_len={out['context_length']}  seen={out['stats'].tokens_seen}  kept={out['stats'].tokens_retained}")

