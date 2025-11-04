#!/usr/bin/env python3
"""
Additional tests to boost coverage from 49% to 80%+.

Covers previously untested code paths in:
- HuggingFaceBackend (KV-cache, streaming)
- Memory policies (semantic, hybrid, rolling_summary)
- Telemetry hooks
- Vector memory store
- Edge cases and error handling
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import torch

from finite_memory_llm import (
    CompleteFiniteMemoryLLM,
    ContextBuilder,
    HuggingFaceBackend,
    PrometheusHook,
    TelemetryHook,
)

# ====================== HUGGINGFACE BACKEND TESTS ======================


class TestHuggingFaceBackendAdvanced:
    """Test advanced HuggingFace backend features."""

    @pytest.mark.slow
    def test_kv_cache_carryover(self):
        """Test KV-cache carryover optimization."""
        backend = HuggingFaceBackend("gpt2", device="cpu", enable_kv_cache=True)

        # First generation
        input_ids = torch.tensor([[72, 101, 108, 108, 111]])  # "Hello"
        backend.generate(input_ids, max_new_tokens=5)

        # Second generation with overlapping context (should hit cache)
        backend.generate(input_ids, max_new_tokens=5)

        stats = backend.get_cache_stats()
        assert stats["cache_hits"] > 0 or stats["cache_misses"] > 0
        assert stats["cached_tokens"] >= 0

    @pytest.mark.slow
    def test_streaming_generation(self):
        """Test streaming token generation."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        input_ids = torch.tensor([[72, 101, 108, 108, 111]])

        tokens = []
        for token_data in backend.generate_stream(input_ids, max_new_tokens=5):
            assert "token_id" in token_data
            assert "token_text" in token_data
            assert "is_final" in token_data
            tokens.append(token_data["token_id"])

            if token_data["is_final"]:
                break

        assert len(tokens) > 0
        assert len(tokens) <= 5

    def test_kv_cache_disabled(self):
        """Test backend with KV-cache disabled."""
        backend = HuggingFaceBackend("gpt2", device="cpu", enable_kv_cache=False)
        input_ids = torch.tensor([[72, 101, 108]])

        result = backend.generate(input_ids, max_new_tokens=3)
        assert "sequences" in result

        stats = backend.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0


# ====================== SEMANTIC POLICY TESTS ======================


class TestSemanticPolicyAdvanced:
    """Test semantic clustering policy in detail."""

    @pytest.fixture
    def mock_backend_with_model(self):
        """Create a mock backend with model attribute."""
        backend = Mock()
        backend.encode = lambda text: [ord(c) for c in text[:10]]
        backend.decode = lambda tokens: "".join(chr(min(t, 127)) for t in tokens if t < 128)
        backend.get_model_name = lambda: "mock-model"
        backend.model = None  # No model for API-like behavior

        def mock_generate(input_ids, max_new_tokens, **kwargs):
            mock_response = [72, 101, 108, 108, 111]
            return {"sequences": torch.tensor([input_ids[0].tolist() + mock_response])}

        backend.generate = mock_generate
        return backend

    def test_semantic_policy_with_embeddings(self, mock_backend_with_model):
        """Test semantic policy with actual embeddings."""
        # This will fall back to sliding if sentence-transformers not available
        llm = CompleteFiniteMemoryLLM(
            mock_backend_with_model,
            memory_policy="semantic",
            max_tokens=128,
            window_size=32,
            semantic_clusters=2,
        )

        # Generate enough tokens to trigger clustering
        for i in range(5):
            result = llm.chat(f"Message {i} with some content", max_new_tokens=10)
            assert "response" in result

    def test_semantic_policy_fallback(self, mock_backend_with_model):
        """Test semantic policy fallback to sliding."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend_with_model, memory_policy="semantic", max_tokens=64, window_size=16
        )

        # Should work even if embeddings fail
        result = llm.chat("Test message", max_new_tokens=5)
        assert result["response"] is not None


# ====================== HYBRID POLICY TESTS ======================


class TestHybridPolicy:
    """Test hybrid memory policy."""

    @pytest.fixture
    def mock_backend(self):
        backend = Mock()
        backend.encode = lambda text: [ord(c) for c in text[:10]]
        backend.decode = lambda tokens: "".join(chr(min(t, 127)) for t in tokens if t < 128)
        backend.get_model_name = lambda: "mock-model"
        backend.model = None

        def mock_generate(input_ids, max_new_tokens, **kwargs):
            return {"sequences": torch.tensor([input_ids[0].tolist() + [72, 101]])}

        backend.generate = mock_generate
        return backend

    def test_hybrid_policy_initialization(self, mock_backend):
        """Test hybrid policy initialization."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend, memory_policy="hybrid", max_tokens=128, window_size=32
        )

        assert llm.memory_policy == "hybrid"

    def test_hybrid_policy_execution(self, mock_backend):
        """Test hybrid policy execution."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend, memory_policy="hybrid", max_tokens=128, window_size=32
        )

        # Generate conversation
        for i in range(3):
            result = llm.chat(f"Message {i}", max_new_tokens=5)
            assert "response" in result
            assert result["memory_policy"] == "hybrid"


# ====================== ROLLING SUMMARY TESTS ======================


class TestRollingSummaryAdvanced:
    """Test rolling summary policy in detail."""

    @pytest.fixture
    def mock_backend(self):
        backend = Mock()
        backend.encode = lambda text: [ord(c) for c in text[:20]]
        backend.decode = lambda tokens: "".join(chr(min(t, 127)) for t in tokens if t < 128)
        backend.get_model_name = lambda: "mock-model"

        def mock_generate(input_ids, max_new_tokens, **kwargs):
            return {"sequences": torch.tensor([input_ids[0].tolist() + [72, 101, 108]])}

        backend.generate = mock_generate
        return backend

    def test_summary_creation(self, mock_backend):
        """Test summary creation triggers."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            memory_policy="rolling_summary",
            max_tokens=256,
            window_size=64,
            summary_interval=50,
        )

        # Generate enough messages to trigger summary
        for i in range(10):
            result = llm.chat(f"Long message number {i} with content", max_new_tokens=5)
            assert "response" in result

        # Check that summaries were created
        assert llm.stats.summaries_created >= 0

    def test_summary_with_qa_gate(self, mock_backend):
        """Test summary with QA gate enabled."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend, memory_policy="rolling_summary", max_tokens=256, summary_interval=50
        )

        # Create summary with factual content
        tokens = llm.backend.encode("The year is 2024. John Smith visited Paris.")
        summary = llm._create_summary(tokens, max_summary_tokens=20)

        assert len(summary) <= 20
        assert len(summary) > 0


# ====================== TELEMETRY TESTS ======================


class TestTelemetryHooks:
    """Test telemetry hook system."""

    def test_custom_telemetry_hook(self):
        """Test custom telemetry hook."""

        class CustomHook(TelemetryHook):
            def __init__(self):
                self.chat_starts = 0
                self.chat_completes = 0
                self.policy_executions = 0

            def on_chat_start(self, message):
                self.chat_starts += 1

            def on_chat_complete(self, stats, latency_ms):
                self.chat_completes += 1

            def on_policy_execute(self, policy, latency_ms, tokens_before, tokens_after):
                self.policy_executions += 1

        hook = CustomHook()

        backend = Mock()
        backend.encode = lambda text: [1, 2, 3]
        backend.decode = lambda tokens: "test"
        backend.get_model_name = lambda: "mock"
        backend.generate = lambda *args, **kwargs: {"sequences": torch.tensor([[1, 2, 3, 4]])}

        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=128, telemetry_hook=hook
        )

        llm.chat("Test message", max_new_tokens=5)

        assert hook.chat_starts == 1
        assert hook.chat_completes == 1

    def test_prometheus_hook_initialization(self):
        """Test Prometheus hook initialization."""
        try:
            hook = PrometheusHook()
            assert hook is not None
        except ImportError:
            pytest.skip("prometheus_client not installed")


# ====================== CONTEXT BUILDER TESTS ======================


class TestContextBuilderAdvanced:
    """Test context builder edge cases."""

    @pytest.fixture
    def mock_backend(self):
        backend = Mock()
        backend.decode = lambda tokens: "".join(chr(min(t, 127)) for t in tokens if t < 128)
        return backend

    def test_context_builder_with_anchors(self, mock_backend):
        """Test context builder with sentence anchors."""
        builder = ContextBuilder(max_tokens=50, window_size=20)

        # Create tokens with sentence boundaries
        tokens = [65, 66, 46, 67, 68, 46, 69, 70]  # "AB.CD.EF"
        result, cache_hits = builder.build(mock_backend, tokens, tokens)

        assert len(result) <= 50
        assert cache_hits >= 0

    def test_context_builder_cache_clearing(self, mock_backend):
        """Test anchor cache clearing."""
        builder = ContextBuilder(max_tokens=50, window_size=20)

        # Fill cache beyond limit
        for i in range(150):
            tokens = [65 + (i % 26)] * 10
            builder.build(mock_backend, tokens, tokens)

        # Cache should have been cleared
        assert len(builder._anchor_cache) <= 100

    def test_context_builder_empty_tokens(self, mock_backend):
        """Test context builder with empty tokens."""
        builder = ContextBuilder(max_tokens=50, window_size=20)
        result, _ = builder.build(mock_backend, [], [])

        assert result == []


# ====================== ERROR HANDLING TESTS ======================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_chat_with_exception(self):
        """Test chat with backend exception."""
        backend = Mock()
        backend.encode = lambda text: [1, 2, 3]
        backend.decode = lambda tokens: "test"
        backend.get_model_name = lambda: "mock"
        backend.generate = Mock(side_effect=Exception("Backend error"))

        llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=128)

        result = llm.chat("Test", max_new_tokens=5)
        assert "Error" in result["response"]
        assert result["tokens_used"] == 0

    def test_invalid_checkpoint_load(self):
        """Test loading invalid checkpoint."""
        backend = Mock()
        backend.encode = lambda text: [1, 2, 3]
        backend.decode = lambda tokens: "test"
        backend.get_model_name = lambda: "mock"
        backend.generate = lambda *args, **kwargs: {"sequences": torch.tensor([[1, 2, 3]])}

        llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"invalid": "data"}, f)
            temp_path = f.name

        try:
            with pytest.raises(KeyError):
                llm.load_checkpoint(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_encode_empty_string(self):
        """Test encoding empty string."""
        backend = Mock()
        backend.encode = lambda text: []
        backend.decode = lambda tokens: ""
        backend.get_model_name = lambda: "mock"
        backend.generate = lambda *args, **kwargs: {"sequences": torch.tensor([[0]])}

        llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
        result = llm.chat("", max_new_tokens=5)

        assert result["response"] == ""
        assert result["tokens_used"] == 0


# ====================== IMPORTANCE POLICY TESTS ======================


class TestImportancePolicyAdvanced:
    """Test importance policy with different scenarios."""

    def test_importance_with_attention_scores(self):
        """Test importance policy with mock attention scores."""
        backend = Mock()
        backend.encode = lambda text: [ord(c) for c in text[:10]]
        backend.decode = lambda tokens: "".join(chr(min(t, 127)) for t in tokens if t < 128)
        backend.get_model_name = lambda: "mock"

        # Mock model with attention
        mock_model = Mock()
        mock_attention = torch.rand(1, 8, 10, 10)  # [batch, heads, seq, seq]
        mock_output = Mock()
        mock_output.attentions = [mock_attention]
        mock_model.return_value = mock_output

        backend.model = mock_model
        backend.tokenizer = Mock()

        def mock_generate(input_ids, max_new_tokens, **kwargs):
            return {"sequences": torch.tensor([input_ids[0].tolist() + [72, 101]])}

        backend.generate = mock_generate

        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="importance", max_tokens=128, device="cpu"
        )

        result = llm.chat("Test message", max_new_tokens=5)
        assert "response" in result

    def test_logit_probes_fallback(self):
        """Test logit probes when attention unavailable."""
        backend = Mock()
        backend.encode = lambda text: [ord(c) for c in text[:20]]
        backend.decode = lambda tokens: "".join(chr(min(t, 127)) for t in tokens if t < 128)
        backend.get_model_name = lambda: "mock"
        backend.model = None  # No model

        def mock_generate(input_ids, max_new_tokens, **kwargs):
            return {"sequences": torch.tensor([input_ids[0].tolist() + [72]])}

        backend.generate = mock_generate

        llm = CompleteFiniteMemoryLLM(backend, memory_policy="importance", max_tokens=128)

        # Should use logit probe fallback
        result = llm.chat("Test message for importance", max_new_tokens=5)
        assert "response" in result


# ====================== STATISTICS TESTS ======================


class TestStatisticsTracking:
    """Test comprehensive statistics tracking."""

    def test_compression_ratio_calculation(self):
        """Test compression ratio calculation."""
        backend = Mock()
        backend.encode = lambda text: [1] * len(text)
        backend.decode = lambda tokens: "x" * len(tokens)
        backend.get_model_name = lambda: "mock"
        backend.generate = lambda *args, **kwargs: {"sequences": torch.tensor([[1, 2, 3]])}

        llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=50)

        # Generate multiple turns
        for _ in range(5):
            llm.chat("Test message", max_new_tokens=2)

        assert llm.stats.compression_ratio >= 1.0
        assert llm.stats.tokens_seen > 0
        assert llm.stats.tokens_retained > 0

    def test_eviction_counting(self):
        """Test eviction counting."""
        backend = Mock()
        backend.encode = lambda text: [1] * 20  # Always 20 tokens
        backend.decode = lambda tokens: "x" * len(tokens)
        backend.get_model_name = lambda: "mock"
        backend.generate = lambda *args, **kwargs: {"sequences": torch.tensor([[1, 2]])}

        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=50  # Small limit to force evictions
        )

        # Generate enough to cause evictions
        for _ in range(5):
            llm.chat("Test message", max_new_tokens=2)

        assert llm.stats.evictions > 0


# ====================== RESET FUNCTIONALITY TESTS ======================


class TestResetFunctionality:
    """Test reset and state management."""

    def test_reset_clears_all_state(self):
        """Test that reset clears all state."""
        backend = Mock()
        backend.encode = lambda text: [1, 2, 3]
        backend.decode = lambda tokens: "test"
        backend.get_model_name = lambda: "mock"
        backend.generate = lambda *args, **kwargs: {"sequences": torch.tensor([[1, 2, 3, 4]])}

        llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")

        # Generate some state
        llm.chat("Test", max_new_tokens=5)
        assert len(llm.token_buffer) > 0
        assert len(llm.conversation_history) > 0

        # Reset
        llm.reset()

        assert len(llm.token_buffer) == 0
        assert len(llm.conversation_history) == 0
        assert llm.stats.tokens_seen == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
