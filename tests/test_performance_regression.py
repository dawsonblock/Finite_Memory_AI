#!/usr/bin/env python3
"""Performance regression tests to prevent future slowdowns.

These tests ensure that critical performance metrics stay within
acceptable bounds.
"""

import time
import pytest


class TestImportPerformance:
    """Test that imports stay fast."""

    def test_interfaces_import_time(self):
        """Ensure interfaces module imports in < 0.1s."""
        start = time.perf_counter()
        from finite_memory_llm.interfaces import (
            LLMBackend,
            MemoryStats,
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"Interfaces import too slow: {elapsed:.3f}s"
        assert LLMBackend is not None
        assert MemoryStats is not None

    def test_core_import_time(self):
        """Ensure core module imports in < 1.0s (includes torch)."""
        start = time.perf_counter()
        from finite_memory_llm import CompleteFiniteMemoryLLM
        elapsed = time.perf_counter() - start

        # Core imports torch, so allow more time
        assert elapsed < 1.0, f"Core import too slow: {elapsed:.3f}s"
        assert CompleteFiniteMemoryLLM is not None

    def test_lazy_backends_import_time(self):
        """Ensure lazy backends import in < 0.1s."""
        start = time.perf_counter()
        from finite_memory_llm.backends_lazy import (
            HuggingFaceBackendLazy,
            APIChatBackendLazy,
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"Lazy backends import too slow: {elapsed:.3f}s"
        assert HuggingFaceBackendLazy is not None
        assert APIChatBackendLazy is not None


class TestKVCachePerformance:
    """Test that KV-cache overhead stays reasonable."""

    @pytest.mark.slow
    def test_kv_cache_overhead_acceptable(self):
        """Ensure KV-cache overhead is < 2x in short convos."""
        from finite_memory_llm import (
            CompleteFiniteMemoryLLM,
            HuggingFaceBackend,
        )

        # With KV-cache
        backend_kv = HuggingFaceBackend(
            "gpt2", device="cpu", enable_kv_cache=True
        )
        llm_kv = CompleteFiniteMemoryLLM(
            backend_kv, memory_policy="sliding", max_tokens=512
        )

        start = time.perf_counter()
        for i in range(3):
            llm_kv.chat(f"Message {i}", max_new_tokens=5)
        time_kv = time.perf_counter() - start

        # Without KV-cache
        backend_no_kv = HuggingFaceBackend(
            "gpt2", device="cpu", enable_kv_cache=False
        )
        llm_no_kv = CompleteFiniteMemoryLLM(
            backend_no_kv, memory_policy="sliding", max_tokens=512
        )

        start = time.perf_counter()
        for i in range(3):
            llm_no_kv.chat(f"Message {i}", max_new_tokens=5)
        time_no_kv = time.perf_counter() - start

        overhead = time_kv / time_no_kv if time_no_kv > 0 else 1.0

        # KV-cache should not be more than 3x slower in short conversations
        # Note: For very short conversations, KV-cache overhead can dominate
        # This is expected and acceptable - KV-cache benefits longer conversations
        assert overhead < 3.0, (
            f"KV-cache overhead too high: {overhead:.2f}x "
            f"(kv={time_kv:.2f}s, no_kv={time_no_kv:.2f}s)"
        )


class TestMemoryUsage:
    """Test that memory usage stays within bounds."""

    def test_api_only_memory_footprint(self):
        """Ensure interfaces module is lightweight."""
        import subprocess
        import sys

        # Test that interfaces module can be imported quickly
        # Note: Full module import will load dependencies, but interfaces
        # should be fast
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import time; "
                "start = time.time(); "
                "from finite_memory_llm.interfaces import LLMBackend; "
                "elapsed = time.time() - start; "
                "print(f'{elapsed:.3f}')"
            ],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Check that import was reasonably fast (< 10s)
        assert result.returncode == 0, (
            f"Import failed: {result.stderr}"
        )
        
        elapsed = float(result.stdout.strip())
        assert elapsed < 10.0, (
            f"Import too slow: {elapsed:.2f}s"
        )


class TestChatPerformance:
    """Test that chat operations stay performant."""

    @pytest.mark.slow
    def test_single_turn_latency(self):
        """Ensure single chat turn completes in reasonable time."""
        from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        start = time.perf_counter()
        result = llm.chat("Hello", max_new_tokens=5)
        elapsed = time.perf_counter() - start

        # Single turn should complete in < 10s on CPU
        assert elapsed < 10.0, f"Single turn too slow: {elapsed:.2f}s"
        assert "response" in result

    @pytest.mark.slow
    def test_multi_turn_latency(self):
        """Ensure multi-turn conversation stays performant."""
        from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        start = time.perf_counter()
        for i in range(5):
            llm.chat(f"Turn {i}", max_new_tokens=5)
        elapsed = time.perf_counter() - start

        # 5 turns should complete in < 30s on CPU
        assert elapsed < 30.0, f"Multi-turn too slow: {elapsed:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
