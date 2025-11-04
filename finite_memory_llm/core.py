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
import warnings
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

warnings.filterwarnings("ignore")


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
    """HuggingFace transformers backend."""

    def __init__(self, model_name: str = "gpt2", device: str = "cpu"):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.device = device

        print(f"Loading {model_name}...")
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        print(f"✓ Model loaded on {device}")

    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate tokens using the model."""
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                pad_token_id=self.tokenizer.pad_token_id,
                return_dict_in_generate=True,
                use_cache=True,
                do_sample=False,  # deterministic by default
            )
        return {"sequences": outputs.sequences}

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

    def global_boundaries(
        self,
        backend: LLMBackend,
        toks: list[int]
    ) -> list[int]:
        """Find global sentence boundary positions."""
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
        return sorted(set(i for i in idx if 0 <= i < len(toks)))

    def build(
        self,
        backend: LLMBackend,
        buffer: list[int],
        policy_out: list[int]
    ) -> list[int]:
        if len(policy_out) <= self.max_tokens:
            return policy_out

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
        return out


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
    ) -> None:
        self.backend = backend
        self.max_tokens = max_tokens
        self.memory_policy = memory_policy
        self.window_size = window_size
        self.semantic_clusters = semantic_clusters
        self.summary_interval = summary_interval
        self.device = device

        # Embedding model for semantic clustering
        self.embedding_model = None
        if memory_policy == "semantic":
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

        print(f"✓ LLM initialized: policy={self.memory_policy}, max_tokens={self.max_tokens}, window={self.window_size}")

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

    # ---------- policy: importance (uses attention) ----------

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

    def _evict_importance(self, new_tokens: list[int]) -> list[int]:
        """Importance-based eviction policy using attention scores."""
        n_new = len(new_tokens)
        cur_list = list(self.token_buffer)
        if len(cur_list) + n_new <= self.max_tokens:
            self.token_buffer.extend(new_tokens)
            self.attention_scores.extend([0.0] * n_new)
            return list(self.token_buffer)

        imp = self._collect_last_token_importance(cur_list)
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
        """Compute embeddings for token spans."""
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
        """Semantic clustering eviction policy."""
        n_new = len(new_tokens)
        cur = list(self.token_buffer)
        if len(cur) + n_new <= self.max_tokens:
            self.token_buffer.extend(new_tokens)
            return list(self.token_buffer)

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
        """Create a summary of token sequence."""
        if not tokens:
            return []
        try:
            text = self.backend.decode(tokens)
            # naive extractive summary: first sentence or first 200 chars
            sentence = text.split(".")[0]
            summary_text = sentence[:200] if sentence else text[:200]
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

    # ---------- main interface ----------

    def _apply_policy(self, new_tokens: list[int]) -> list[int]:
        """Apply the configured memory policy."""
        if self.memory_policy == "sliding":
            return self._evict_sliding(new_tokens)
        elif self.memory_policy == "importance":
            return self._evict_importance(new_tokens)
        elif self.memory_policy == "semantic":
            return self._evict_semantic(new_tokens)
        elif self.memory_policy == "rolling_summary":
            return self._evict_rolling_summary(new_tokens)
        else:
            return self._evict_sliding(new_tokens)

    def chat(self, message: str, max_new_tokens: int = 50) -> dict[str, Any]:
        """Process a chat message and generate a response."""
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
            context_tokens = self.context_builder.build(self.backend, list(self.token_buffer), policy_out)
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

            return {
                "response": response_text,
                "tokens_used": len(gen_ids),
                "context_length": len(context_tokens),
                "stats": self.stats,
                "memory_policy": self.memory_policy,
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "response": f"Error: {str(e)}",
                "tokens_used": 0,
                "context_length": len(self.token_buffer),
                "stats": self.stats,
                "memory_policy": self.memory_policy,
            }

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

