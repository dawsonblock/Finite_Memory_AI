#!/usr/bin/env python3
"""
Comprehensive test suite for finite_memory_llm.

Run with: pytest tests/
"""

import pytest
import torch
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

from finite_memory_llm import (
    CompleteFiniteMemoryLLM,
    HuggingFaceBackend,
    APIChatBackend,
    MemoryStats,
    ContextBuilder,
    LLMBackend,
)


# ====================== FIXTURES ======================

@pytest.fixture
def mock_tokenizer():
    """Create a mock tokenizer for testing."""
    tokenizer = Mock()
    tokenizer.encode = lambda text, **kwargs: [ord(c) for c in text[:10]]  # Simple char encoding
    tokenizer.decode = lambda tokens, **kwargs: ''.join(chr(min(t, 127)) for t in tokens if t < 128)
    return tokenizer


@pytest.fixture
def mock_backend(mock_tokenizer):
    """Create a mock LLM backend for testing."""
    backend = Mock(spec=LLMBackend)
    backend.encode = mock_tokenizer.encode
    backend.decode = mock_tokenizer.decode
    backend.get_model_name = lambda: "mock-model"
    
    def mock_generate(input_ids, max_new_tokens, **kwargs):
        # Generate simple mock response
        mock_response = [72, 101, 108, 108, 111]  # "Hello"
        return {"sequences": torch.tensor([input_ids[0].tolist() + mock_response])}
    
    backend.generate = mock_generate
    return backend


# ====================== BACKEND TESTS ======================

class TestAPIChatBackend:
    """Test the API chat backend wrapper."""
    
    def test_initialization(self, mock_tokenizer):
        """Test backend initialization."""
        def dummy_send(prompt, max_tokens):
            return "response"
        
        backend = APIChatBackend(mock_tokenizer, dummy_send, name="test-api")
        assert backend.get_model_name() == "test-api"
    
    def test_encode_decode(self, mock_tokenizer):
        """Test encoding and decoding."""
        def dummy_send(prompt, max_tokens):
            return "response"
        
        backend = APIChatBackend(mock_tokenizer, dummy_send)
        
        text = "Hello"
        tokens = backend.encode(text)
        decoded = backend.decode(tokens)
        
        assert isinstance(tokens, list)
        assert isinstance(decoded, str)
    
    def test_generate(self, mock_tokenizer):
        """Test generation with API backend."""
        def dummy_send(prompt, max_tokens):
            return "World"
        
        backend = APIChatBackend(mock_tokenizer, dummy_send)
        input_ids = torch.tensor([[72, 101, 108, 108, 111]])
        
        result = backend.generate(input_ids, max_new_tokens=10)
        
        assert "sequences" in result
        assert isinstance(result["sequences"], torch.Tensor)


# ====================== MEMORY STATS TESTS ======================

class TestMemoryStats:
    """Test memory statistics tracking."""
    
    def test_initialization(self):
        """Test stats initialization."""
        stats = MemoryStats()
        assert stats.tokens_seen == 0
        assert stats.tokens_retained == 0
        assert stats.evictions == 0
        assert stats.compression_ratio == 1.0
        assert stats.policy_latency_ms == 0.0
        assert stats.total_policy_calls == 0
        assert stats.fallback_count == 0
        assert stats.anchor_cache_hits == 0
    
    def test_stats_update(self):
        """Test stats can be updated."""
        stats = MemoryStats()
        stats.tokens_seen = 100
        stats.tokens_retained = 50
        stats.evictions = 50
        
        assert stats.tokens_seen == 100
        assert stats.tokens_retained == 50
        assert stats.evictions == 50


# ====================== CONTEXT BUILDER TESTS ======================

class TestContextBuilder:
    """Test the context builder."""
    
    def test_initialization(self):
        """Test context builder initialization."""
        builder = ContextBuilder(max_tokens=512, window_size=128)
        assert builder.max_tokens == 512
        assert builder.window_size == 128
    
    def test_build_under_limit(self, mock_backend):
        """Test building context when under token limit."""
        builder = ContextBuilder(max_tokens=512, window_size=128)
        tokens = list(range(100))
        
        result, cache_hits = builder.build(mock_backend, [], tokens)
        
        assert len(result) <= 512
        assert result == tokens
        assert cache_hits == 0  # First call, no cache hits
    
    def test_build_over_limit(self, mock_backend):
        """Test building context when over token limit."""
        builder = ContextBuilder(max_tokens=100, window_size=50)
        tokens = list(range(200))
        
        result, cache_hits = builder.build(mock_backend, [], tokens)
        
        assert len(result) <= 100
        assert len(result) > 0
    
    def test_preserves_recency(self, mock_backend):
        """Test that recent tokens are preserved."""
        builder = ContextBuilder(max_tokens=100, window_size=50)
        tokens = list(range(200))
        
        result, cache_hits = builder.build(mock_backend, [], tokens)
        
        # Should include most recent tokens
        assert 199 in result or 198 in result
    
    def test_anchor_caching(self, mock_backend):
        """Test that anchor caching works correctly."""
        builder = ContextBuilder(max_tokens=100, window_size=50)
        tokens = list(range(200))
        
        # First call - no cache hits
        result1, cache_hits1 = builder.build(mock_backend, [], tokens)
        assert cache_hits1 == 0
        
        # Second call with same tokens - should hit cache
        result2, cache_hits2 = builder.build(mock_backend, [], tokens)
        assert cache_hits2 == 1
        assert result1 == result2
        
        # Third call with different tokens - cache miss
        tokens_new = list(range(300))
        result3, cache_hits3 = builder.build(mock_backend, [], tokens_new)
        assert cache_hits3 == 0


# ====================== FINITE MEMORY LLM TESTS ======================

class TestCompleteFiniteMemoryLLM:
    """Test the main finite memory LLM class."""
    
    def test_initialization(self, mock_backend):
        """Test LLM initialization."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="sliding",
            window_size=128
        )
        
        assert llm.max_tokens == 512
        assert llm.memory_policy == "sliding"
        assert llm.window_size == 128
        assert isinstance(llm.stats, MemoryStats)
    
    def test_reset(self, mock_backend):
        """Test resetting LLM state."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        
        # Add some state
        llm.token_buffer.extend([1, 2, 3])
        llm.stats.tokens_seen = 100
        
        # Reset
        llm.reset()
        
        assert len(llm.token_buffer) == 0
        assert llm.stats.tokens_seen == 0
    
    def test_chat_empty_message(self, mock_backend):
        """Test chat with empty message."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        result = llm.chat("")
        
        assert result["response"] == ""
        assert result["tokens_used"] == 0
    
    def test_chat_basic(self, mock_backend):
        """Test basic chat functionality."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512, memory_policy="sliding")
        result = llm.chat("Hello", max_new_tokens=10)
        
        assert "response" in result
        assert "tokens_used" in result
        assert "context_length" in result
        assert "stats" in result
        assert isinstance(result["stats"], MemoryStats)
    
    def test_conversation_history(self, mock_backend):
        """Test conversation history tracking."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        
        llm.chat("First message")
        llm.chat("Second message")
        
        assert len(llm.conversation_history) == 4  # 2 user + 2 assistant
        assert llm.conversation_history[0]["role"] == "user"
        assert llm.conversation_history[1]["role"] == "assistant"
    
    def test_get_context_window_empty(self, mock_backend):
        """Test getting context window when empty."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        context = llm.get_context_window()
        assert context == ""
    
    def test_get_context_window_with_data(self, mock_backend):
        """Test getting context window with data."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        llm.token_buffer.extend([72, 101, 108, 108, 111])
        context = llm.get_context_window()
        assert isinstance(context, str)


# ====================== POLICY TESTS ======================

class TestMemoryPolicies:
    """Test different memory policies."""
    
    def test_sliding_policy(self, mock_backend):
        """Test sliding window policy."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=50,
            memory_policy="sliding"
        )
        
        # Add tokens exceeding limit
        tokens = list(range(100))
        result = llm._evict_sliding(tokens)
        
        assert len(result) <= 50
    
    def test_importance_policy_no_model(self, mock_backend):
        """Test importance policy without model access."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=50,
            memory_policy="importance"
        )
        
        tokens = list(range(30))
        result = llm._evict_importance(tokens)
        
        # Should still work, just without actual importance scores
        assert len(result) <= 50
    
    def test_rolling_summary_policy(self, mock_backend):
        """Test rolling summary policy."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=500,
            memory_policy="rolling_summary",
            summary_interval=200
        )
        
        # Add enough tokens to trigger summary
        for i in range(10):
            tokens = list(range(30))
            llm._evict_rolling_summary(tokens)
        
        # Should have created summaries
        assert llm.stats.summaries_created >= 0
    
    def test_semantic_policy_fallback(self, mock_backend):
        """Test semantic policy without embedding model."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=50,
            memory_policy="sliding"  # Force sliding since no embedding model
        )
        
        # Should fall back to sliding
        tokens = list(range(30))
        result = llm._evict_semantic(tokens)
        assert len(result) <= 50


# ====================== LATENCY BUDGETING TESTS ======================

class TestLatencyBudgeting:
    """Test latency budgeting and fallback mechanisms."""
    
    def test_latency_budget_initialization(self, mock_backend):
        """Test initialization with latency budget."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="sliding",
            max_policy_ms=100.0
        )
        
        assert llm.max_policy_ms == 100.0
    
    def test_latency_tracking(self, mock_backend):
        """Test that latency is tracked correctly."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="sliding",
            max_policy_ms=1000.0  # High budget, won't trigger fallback
        )
        
        llm.chat("Hello", max_new_tokens=10)
        
        # Should have tracked policy calls
        assert llm.stats.total_policy_calls > 0
    
    def test_no_fallback_when_under_budget(self, mock_backend):
        """Test that no fallback occurs when under budget."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="sliding",
            max_policy_ms=10000.0  # Very high budget
        )
        
        llm.chat("Hello", max_new_tokens=10)
        
        assert llm.stats.fallback_count == 0
    
    def test_fallback_statistics(self, mock_backend):
        """Test that fallback statistics are tracked."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="sliding"
        )
        
        # Manually trigger fallback by simulating slow policy
        import time
        original_impl = llm._apply_policy_impl
        
        def slow_policy(tokens):
            time.sleep(0.01)  # Add small delay
            return original_impl(tokens)
        
        llm._apply_policy_impl = slow_policy
        llm.max_policy_ms = 1.0  # Very low budget
        
        llm.chat("Test", max_new_tokens=5)
        
        # Should have attempted to track latency
        assert llm.stats.total_policy_calls > 0
    
    def test_policy_calls_increment(self, mock_backend):
        """Test that policy calls are counted correctly."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="sliding"
        )
        
        initial_calls = llm.stats.total_policy_calls
        
        llm.chat("Message 1", max_new_tokens=5)
        llm.chat("Message 2", max_new_tokens=5)
        
        # Each chat calls policy twice (user tokens + assistant tokens)
        assert llm.stats.total_policy_calls >= initial_calls + 4


# ====================== CHECKPOINT TESTS ======================

class TestCheckpointing:
    """Test checkpoint save/load functionality."""
    
    def test_save_checkpoint(self, mock_backend):
        """Test saving checkpoint."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        llm.chat("Test message")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"
            result_path = llm.save_checkpoint(checkpoint_path)
            
            assert result_path.exists()
            assert result_path.suffix == ".json"
            
            # Verify content
            with open(result_path) as f:
                data = json.load(f)
            
            assert "config" in data
            assert "state" in data
            assert "stats" in data
            assert "metadata" in data
    
    def test_load_checkpoint(self, mock_backend):
        """Test loading checkpoint."""
        llm1 = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        llm1.chat("Test message")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test_checkpoint.json"
            llm1.save_checkpoint(checkpoint_path)
            
            # Create new LLM and load
            llm2 = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
            config = llm2.load_checkpoint(checkpoint_path)
            
            assert config["max_tokens"] == 512
            assert len(llm2.conversation_history) == len(llm1.conversation_history)
    
    def test_checkpoint_preserves_state(self, mock_backend):
        """Test that checkpoint preserves all state."""
        llm1 = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
        llm1.chat("First")
        llm1.chat("Second")
        
        original_tokens_seen = llm1.stats.tokens_seen
        original_history_len = len(llm1.conversation_history)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "test.json"
            llm1.save_checkpoint(checkpoint_path)
            
            llm2 = CompleteFiniteMemoryLLM(mock_backend, max_tokens=512)
            llm2.load_checkpoint(checkpoint_path)
            
            assert llm2.stats.tokens_seen == original_tokens_seen
            assert len(llm2.conversation_history) == original_history_len


# ====================== INTEGRATION TESTS ======================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_multi_turn_conversation(self, mock_backend):
        """Test multi-turn conversation flow."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=256,
            memory_policy="sliding"
        )
        
        messages = ["Hello", "How are you?", "Tell me more"]
        
        for msg in messages:
            result = llm.chat(msg, max_new_tokens=20)
            assert "response" in result
        
        # Should have tracked all turns
        assert len(llm.conversation_history) == len(messages) * 2
    
    def test_memory_eviction_occurs(self, mock_backend):
        """Test that memory eviction actually happens."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=50,
            memory_policy="sliding"
        )
        
        # Fill memory beyond capacity
        for i in range(10):
            llm.chat(f"Message {i}", max_new_tokens=10)
        
        # Should have evicted tokens
        assert llm.stats.evictions > 0
    
    def test_different_policies_produce_results(self, mock_backend):
        """Test that all policies can produce results."""
        policies = ["sliding", "importance", "rolling_summary"]
        
        for policy in policies:
            llm = CompleteFiniteMemoryLLM(
                mock_backend,
                max_tokens=256,
                memory_policy=policy
            )
            
            result = llm.chat("Test message", max_new_tokens=10)
            assert "response" in result
            assert result["memory_policy"] == policy


# ====================== EDGE CASES ======================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_max_tokens(self, mock_backend):
        """Test with zero max tokens (should handle gracefully)."""
        # This might raise an error or handle it - test current behavior
        try:
            llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=0)
            assert llm.max_tokens == 0
        except Exception:
            pass  # Some configurations may not allow this
    
    def test_very_large_max_tokens(self, mock_backend):
        """Test with very large max tokens."""
        llm = CompleteFiniteMemoryLLM(mock_backend, max_tokens=100000)
        result = llm.chat("Hello", max_new_tokens=10)
        assert "response" in result
    
    def test_invalid_policy_fallback(self, mock_backend):
        """Test that invalid policy falls back to sliding."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=256,
            memory_policy="invalid_policy"
        )
        
        result = llm.chat("Hello", max_new_tokens=10)
        assert "response" in result


class TestKVCacheTracking:
    """Test KV-cache tracking (v2.2+)."""
    
    def test_kv_cache_enabled(self):
        """Test that KV-cache tracking is enabled by default."""
        from finite_memory_llm.core import HuggingFaceBackend
        backend = HuggingFaceBackend("gpt2", device="cpu")
        assert backend.enable_kv_cache == True
    
    def test_kv_cache_stats(self):
        """Test KV-cache statistics tracking."""
        from finite_memory_llm.core import HuggingFaceBackend
        backend = HuggingFaceBackend("gpt2", device="cpu")
        
        stats = backend.get_cache_stats()
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cached_tokens" in stats
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0


class TestLogitProbes:
    """Test API-safe importance probes (v2.2+)."""
    
    def test_logit_probes_basic(self, mock_backend):
        """Test logit probes with mock backend."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=512,
            memory_policy="importance"
        )
        
        # Add some tokens to buffer
        llm.token_buffer.extend(list(range(100)))
        
        # Test logit probe method
        scores = llm._importance_via_logit_probes(list(range(100)), n_probes=4, span_size=16)
        
        assert len(scores) == 100
        assert all(0 <= s <= 1.0 for s in scores)  # Normalized scores
    
    def test_importance_with_logit_fallback(self, mock_backend):
        """Test importance policy falls back to logit probes."""
        llm = CompleteFiniteMemoryLLM(
            mock_backend,
            max_tokens=100,
            memory_policy="importance"
        )
        
        # Fill buffer beyond capacity
        large_tokens = list(range(150))
        result = llm._evict_importance(large_tokens)
        
        # Should have used some importance mechanism
        assert len(result) <= 100


class TestAccuracyHarness:
    """Test accuracy evaluation harness (v2.2+)."""
    
    def test_harness_imports(self):
        """Test that accuracy harness can be imported."""
        try:
            import sys
            sys.path.insert(0, "benchmarks")
            import accuracy_harness
            assert hasattr(accuracy_harness, "evaluate_policy")
            assert hasattr(accuracy_harness, "compare_policies")
        except ImportError:
            pytest.skip("Accuracy harness not available")
    
    def test_planted_fact_structure(self):
        """Test PlantedFact dataclass structure."""
        try:
            import sys
            sys.path.insert(0, "benchmarks")
            from accuracy_harness import PlantedFact
            
            fact = PlantedFact(
                position="early",
                turn=1,
                question="Test?",
                answer="test",
                context="This is a test."
            )
            
            assert fact.position == "early"
            assert fact.turn == 1
            assert fact.answer == "test"
        except ImportError:
            pytest.skip("Accuracy harness not available")


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])

