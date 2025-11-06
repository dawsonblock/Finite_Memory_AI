#!/usr/bin/env python3
"""Real integration tests for v2.4.0 features.

Tests actual functionality, not just imports.
"""

import pytest

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend


class TestLazyLoadingIntegration:
    """Test lazy loading actually works."""

    def test_interfaces_import_fast(self):
        """Test that interfaces module imports without torch."""
        import time
        
        start = time.perf_counter()
        from finite_memory_llm.interfaces import LLMBackend, MemoryStats
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.1, f"Interfaces import too slow: {elapsed:.3f}s"
        assert LLMBackend is not None
        assert MemoryStats is not None

    def test_lazy_backends_import_fast(self):
        """Test that lazy backends module imports without torch."""
        import time
        
        start = time.perf_counter()
        from finite_memory_llm.backends_lazy import (
            HuggingFaceBackendLazy,
            APIChatBackendLazy,
        )
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.1, f"Lazy backends import too slow: {elapsed:.3f}s"
        assert HuggingFaceBackendLazy is not None
        assert APIChatBackendLazy is not None

    @pytest.mark.slow
    def test_lazy_backend_instantiation_loads_torch(self):
        """Test that torch loads only when backend is instantiated."""
        import sys
        
        # Remove torch if already loaded
        torch_modules = [k for k in sys.modules.keys() if k.startswith('torch')]
        for mod in torch_modules:
            del sys.modules[mod]
        
        # Import lazy backend (should not load torch)
        from finite_memory_llm.backends_lazy import HuggingFaceBackendLazy
        
        assert 'torch' not in sys.modules, "Torch loaded on import!"
        
        # Now instantiate (should load torch)
        backend = HuggingFaceBackendLazy("gpt2", device="cpu")
        
        assert 'torch' in sys.modules, "Torch not loaded on instantiation!"
        assert backend is not None


class TestAsyncIntegration:
    """Test async features actually work."""

    @pytest.mark.asyncio
    async def test_async_chat_basic(self):
        """Test basic async chat functionality."""
        try:
            from finite_memory_llm import AsyncCompleteFiniteMemoryLLM
            from finite_memory_llm.async_core import AsyncHuggingFaceBackend
            
            backend = AsyncHuggingFaceBackend("gpt2", device="cpu")
            llm = AsyncCompleteFiniteMemoryLLM(
                backend, memory_policy="sliding", max_tokens=512
            )
            
            result = await llm.chat_async("Hello!", max_new_tokens=10)
            
            assert "response" in result
            assert isinstance(result["response"], str)
            assert len(result["response"]) > 0
            
        except ImportError:
            pytest.skip("Async features not available")

    @pytest.mark.asyncio
    async def test_async_streaming(self):
        """Test async streaming generation."""
        try:
            from finite_memory_llm import AsyncCompleteFiniteMemoryLLM
            from finite_memory_llm.async_core import AsyncHuggingFaceBackend
            
            backend = AsyncHuggingFaceBackend("gpt2", device="cpu")
            llm = AsyncCompleteFiniteMemoryLLM(backend, memory_policy="sliding")
            
            tokens = []
            async for chunk in llm.chat_stream_async("Test", max_new_tokens=5):
                if "token_text" in chunk:
                    tokens.append(chunk["token_text"])
            
            assert len(tokens) > 0, "No tokens generated"
            
        except ImportError:
            pytest.skip("Async features not available")


class TestMultilingualIntegration:
    """Test multilingual features actually work."""

    def test_language_detection_basic(self):
        """Test basic language detection."""
        try:
            from finite_memory_llm import LanguageDetector
            
            detector = LanguageDetector()
            
            # Test English
            lang = detector.detect_language("Hello, how are you?")
            assert lang.code == "en"
            assert lang.confidence > 0.9
            
            # Test Spanish
            lang = detector.detect_language("Hola, ¿cómo estás?")
            assert lang.code == "es"
            assert lang.confidence > 0.9
            
        except ImportError:
            pytest.skip("Multilingual features not available")

    def test_multilingual_memory_policy(self):
        """Test multilingual memory policy recommendations."""
        try:
            from finite_memory_llm import MultilingualMemoryPolicy
            
            policy_advisor = MultilingualMemoryPolicy()
            
            # English text
            policy = policy_advisor.get_recommended_policy("Hello world")
            assert policy in ["sliding", "importance", "semantic"]
            
            # Chinese text (more tokens per character)
            policy = policy_advisor.get_recommended_policy("你好世界")
            assert policy in ["sliding", "importance", "semantic"]
            
        except ImportError:
            pytest.skip("Multilingual features not available")


class TestBackendsIntegration:
    """Test additional backends actually work."""

    def test_cohere_backend_import(self):
        """Test Cohere backend can be imported."""
        try:
            from finite_memory_llm import CohereBackend
            
            assert CohereBackend is not None
            
        except ImportError:
            pytest.skip("Cohere backend not available")

    def test_anthropic_backend_import(self):
        """Test Anthropic backend can be imported."""
        try:
            from finite_memory_llm import AnthropicBackend
            
            assert AnthropicBackend is not None
            
        except ImportError:
            pytest.skip("Anthropic backend not available")


class TestKVCacheIntegration:
    """Test KV-cache actually provides speedup."""

    @pytest.mark.slow
    def test_kv_cache_speedup_real(self):
        """Test that KV-cache provides actual speedup."""
        import time
        
        # With KV-cache
        backend_cached = HuggingFaceBackend("gpt2", device="cpu", enable_kv_cache=True)
        llm_cached = CompleteFiniteMemoryLLM(
            backend_cached, memory_policy="sliding", max_tokens=512
        )
        
        start = time.perf_counter()
        for i in range(3):
            llm_cached.chat(f"Message {i}", max_new_tokens=5)
        time_cached = time.perf_counter() - start
        
        # Without KV-cache
        backend_uncached = HuggingFaceBackend("gpt2", device="cpu", enable_kv_cache=False)
        llm_uncached = CompleteFiniteMemoryLLM(
            backend_uncached, memory_policy="sliding", max_tokens=512
        )
        
        start = time.perf_counter()
        for i in range(3):
            llm_uncached.chat(f"Message {i}", max_new_tokens=5)
        time_uncached = time.perf_counter() - start
        
        speedup = time_uncached / time_cached if time_cached > 0 else 0
        
        # Should be at least 1.5x faster
        assert speedup > 1.5, f"KV-cache speedup too low: {speedup:.2f}x"


class TestMemoryPoliciesIntegration:
    """Test memory policies actually work end-to-end."""

    def test_sliding_policy_evicts(self):
        """Test sliding policy actually evicts old messages."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=100, window_size=50
        )
        
        # Add enough messages to trigger eviction
        for i in range(10):
            result = llm.chat(f"Message {i}", max_new_tokens=5)
        
        # Should have evicted some messages
        assert result["stats"].evictions > 0, "No evictions occurred"
        assert result["stats"].compression_ratio > 1.0, "No compression"

    def test_importance_policy_works(self):
        """Test importance policy can be used."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="importance", max_tokens=100
        )
        
        result = llm.chat("Test message", max_new_tokens=5)
        
        assert result["memory_policy"] == "importance"
        assert "response" in result

    def test_semantic_policy_works(self):
        """Test semantic policy can be used."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="semantic", max_tokens=100
        )
        
        result = llm.chat("Test message", max_new_tokens=5)
        
        assert result["memory_policy"] == "semantic"
        assert "response" in result


class TestProductionReadiness:
    """Test production-ready features."""

    def test_checkpointing_works(self):
        """Test checkpointing saves and restores state."""
        import tempfile
        import os
        
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
        
        # Have a conversation
        llm.chat("First message", max_new_tokens=5)
        llm.chat("Second message", max_new_tokens=5)
        
        # Save checkpoint
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = os.path.join(tmpdir, "checkpoint.json")
            saved_path = llm.save_checkpoint(checkpoint_path)
            
            assert os.path.exists(saved_path)
            
            # Create new LLM and load checkpoint
            llm2 = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
            llm2.load_checkpoint(saved_path)
            
            # Should have same state
            assert llm2.stats.turns == llm.stats.turns

    def test_telemetry_hooks_work(self):
        """Test telemetry hooks are called."""
        from finite_memory_llm import TelemetryHook
        
        class TestHook(TelemetryHook):
            def __init__(self):
                self.chat_starts = 0
                self.chat_ends = 0
                self.evictions = 0
            
            def on_chat_start(self, message):
                self.chat_starts += 1
            
            def on_chat_end(self, message, response, tokens_used, latency_ms, stats):
                self.chat_ends += 1
            
            def on_eviction(self, policy, tokens_before, tokens_after, latency_ms):
                self.evictions += 1
        
        hook = TestHook()
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", telemetry_hook=hook
        )
        
        llm.chat("Test", max_new_tokens=5)
        
        assert hook.chat_starts > 0, "Hook not called on chat start"
        assert hook.chat_ends > 0, "Hook not called on chat end"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
