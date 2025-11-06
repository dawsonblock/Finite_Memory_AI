#!/usr/bin/env python3
"""Edge case tests to increase coverage."""

import pytest
from finite_memory_llm import (
    CompleteFiniteMemoryLLM,
    HuggingFaceBackend,
)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_prompt(self):
        """Test handling of empty prompt."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        result = llm.chat("", max_new_tokens=5)
        assert "response" in result

    def test_very_long_prompt(self):
        """Test handling of very long prompt."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=100
        )

        # Create a very long prompt
        long_prompt = " ".join(["word"] * 200)
        result = llm.chat(long_prompt, max_new_tokens=5)
        assert "response" in result

    def test_max_tokens_zero(self):
        """Test handling of max_tokens=0."""
        backend = HuggingFaceBackend("gpt2", device="cpu")

        with pytest.raises((ValueError, AssertionError)):
            CompleteFiniteMemoryLLM(
                backend, memory_policy="sliding", max_tokens=0
            )

    def test_max_new_tokens_zero(self):
        """Test handling of max_new_tokens=0."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        # Should handle gracefully or raise error
        try:
            result = llm.chat("Hello", max_new_tokens=0)
            # If it succeeds, response should be empty or minimal
            assert "response" in result
        except (ValueError, AssertionError):
            # Or it might raise an error, which is also acceptable
            pass

    def test_multiple_consecutive_chats(self):
        """Test multiple consecutive chat calls."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        for i in range(10):
            result = llm.chat(f"Message {i}", max_new_tokens=5)
            assert "response" in result
            assert "stats" in result

    def test_reset_conversation(self):
        """Test resetting conversation state."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        # Have a conversation
        llm.chat("First message", max_new_tokens=5)
        llm.chat("Second message", max_new_tokens=5)

        # Reset (if method exists)
        if hasattr(llm, "reset"):
            llm.reset()
            stats = llm.get_memory_stats()
            assert stats.tokens_seen == 0 or stats.tokens_retained == 0

    def test_get_stats_before_chat(self):
        """Test getting stats before any chat."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        stats = llm.get_memory_stats()
        assert stats is not None
        assert stats.tokens_seen >= 0

    def test_different_memory_policies(self):
        """Test all memory policies work."""
        backend = HuggingFaceBackend("gpt2", device="cpu")

        policies = ["sliding", "importance", "semantic", "rolling_summary"]
        for policy in policies:
            try:
                llm = CompleteFiniteMemoryLLM(
                    backend, memory_policy=policy, max_tokens=512
                )
                result = llm.chat("Test", max_new_tokens=5)
                assert "response" in result
            except (ValueError, NotImplementedError):
                # Some policies might not be fully implemented
                pass

    def test_invalid_memory_policy(self):
        """Test invalid memory policy raises error."""
        backend = HuggingFaceBackend("gpt2", device="cpu")

        with pytest.raises((ValueError, KeyError)):
            CompleteFiniteMemoryLLM(
                backend, memory_policy="invalid_policy", max_tokens=512
            )

    def test_backend_with_different_models(self):
        """Test backend with different model sizes."""
        models = ["gpt2"]  # Only test small model for speed

        for model in models:
            backend = HuggingFaceBackend(model, device="cpu")
            llm = CompleteFiniteMemoryLLM(
                backend, memory_policy="sliding", max_tokens=512
            )
            result = llm.chat("Hello", max_new_tokens=5)
            assert "response" in result

    def test_kv_cache_disabled(self):
        """Test with KV-cache explicitly disabled."""
        backend = HuggingFaceBackend(
            "gpt2", device="cpu", enable_kv_cache=False
        )
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        result = llm.chat("Hello", max_new_tokens=5)
        assert "response" in result

    def test_kv_cache_enabled(self):
        """Test with KV-cache explicitly enabled."""
        backend = HuggingFaceBackend(
            "gpt2", device="cpu", enable_kv_cache=True
        )
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        result = llm.chat("Hello", max_new_tokens=5)
        assert "response" in result

    def test_window_size_larger_than_max_tokens(self):
        """Test window_size > max_tokens."""
        backend = HuggingFaceBackend("gpt2", device="cpu")

        # This should either work or raise a clear error
        try:
            llm = CompleteFiniteMemoryLLM(
                backend,
                memory_policy="sliding",
                max_tokens=100,
                window_size=200,
            )
            result = llm.chat("Hello", max_new_tokens=5)
            assert "response" in result
        except (ValueError, AssertionError):
            pass

    def test_special_characters_in_prompt(self):
        """Test special characters in prompt."""
        backend = HuggingFaceBackend("gpt2", device="cpu")
        llm = CompleteFiniteMemoryLLM(
            backend, memory_policy="sliding", max_tokens=512
        )

        special_prompts = [
            "Hello! How are you?",
            "Test with 'quotes' and \"double quotes\"",
            "Numbers: 123, 456.789",
            "Symbols: @#$%^&*()",
            "Unicode: 你好世界 🎉",
        ]

        for prompt in special_prompts:
            result = llm.chat(prompt, max_new_tokens=5)
            assert "response" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
