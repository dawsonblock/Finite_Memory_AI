#!/usr/bin/env python3
"""
Latency Budgeting Demo - v2.1+

Demonstrates how to use max_policy_ms to enforce latency budgets
and ensure predictable response times in production environments.

Run with:
    python examples/latency_budgeting_demo.py
"""

from __future__ import annotations

import time
from typing import Any

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend


def print_stats(result: dict[str, Any], label: str) -> None:
    """Pretty print statistics."""
    stats = result["stats"]
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"Response: {result['response'][:80]}...")
    print(f"Policy latency: {stats.policy_latency_ms:.2f}ms")
    print(f"Total policy calls: {stats.total_policy_calls}")
    print(f"Fallback count: {stats.fallback_count}")
    print(f"Anchor cache hits: {stats.anchor_cache_hits}")
    print(f"Compression ratio: {stats.compression_ratio:.2f}x")


def demo_no_budget() -> None:
    """Demo 1: No latency budget (baseline)."""
    print("\n" + "=" * 60)
    print("DEMO 1: No Latency Budget (Baseline)")
    print("=" * 60)

    backend = HuggingFaceBackend("gpt2", device="cpu")
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="importance",  # Can be slow with attention extraction
        max_tokens=512,
        window_size=128,
        max_policy_ms=None,  # No limit
    )

    # Run several turns
    messages = [
        "What is machine learning?",
        "Explain neural networks in detail.",
        "How do transformers work?",
        "What about GPT models?",
    ]

    for i, msg in enumerate(messages, 1):
        start = time.perf_counter()
        result = llm.chat(msg, max_new_tokens=20)
        total_ms = (time.perf_counter() - start) * 1000

        print(f"\nTurn {i}: '{msg}'")
        print(f"  Policy: {result['stats'].policy_latency_ms:.1f}ms")
        print(f"  Total: {total_ms:.1f}ms")


def demo_with_budget() -> None:
    """Demo 2: With latency budget and fallback."""
    print("\n" + "=" * 60)
    print("DEMO 2: With Latency Budget (50ms)")
    print("=" * 60)

    backend = HuggingFaceBackend("gpt2", device="cpu")
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="importance",
        max_tokens=512,
        window_size=128,
        max_policy_ms=50.0,  # 50ms budget
    )

    messages = [
        "What is machine learning?",
        "Explain neural networks in detail.",
        "How do transformers work?",
        "What about GPT models?",
    ]

    for i, msg in enumerate(messages, 1):
        start = time.perf_counter()
        result = llm.chat(msg, max_new_tokens=20)
        total_ms = (time.perf_counter() - start) * 1000

        print(f"\nTurn {i}: '{msg}'")
        print(f"  Policy: {result['stats'].policy_latency_ms:.1f}ms")
        print(f"  Total: {total_ms:.1f}ms")
        print(f"  Fallbacks: {result['stats'].fallback_count}")

        if result["stats"].fallback_count > 0:
            print("  ⚠️  Policy exceeded budget, fell back to sliding")


def demo_policy_comparison() -> None:
    """Demo 3: Compare latency across different policies."""
    print("\n" + "=" * 60)
    print("DEMO 3: Policy Latency Comparison")
    print("=" * 60)

    backend = HuggingFaceBackend("gpt2", device="cpu")
    policies = ["sliding", "importance", "rolling_summary"]

    test_message = "Explain the history of artificial intelligence in detail."

    for policy in policies:
        print(f"\n--- Testing '{policy}' policy ---")

        llm = CompleteFiniteMemoryLLM(
            backend,
            memory_policy=policy,
            max_tokens=512,
            window_size=128,
            max_policy_ms=None,  # No limit for fair comparison
        )

        # Build up some context first
        for _ in range(3):
            llm.chat("Tell me about AI.", max_new_tokens=20)

        # Measure policy latency
        start = time.perf_counter()
        result = llm.chat(test_message, max_new_tokens=20)
        total_ms = (time.perf_counter() - start) * 1000

        print(f"  Policy latency: {result['stats'].policy_latency_ms:.2f}ms")
        print(f"  Total latency: {total_ms:.1f}ms")
        print(f"  Compression: {result['stats'].compression_ratio:.2f}x")


def demo_anchor_caching() -> None:
    """Demo 4: Show anchor caching benefits."""
    print("\n" + "=" * 60)
    print("DEMO 4: Anchor Caching Performance")
    print("=" * 60)

    backend = HuggingFaceBackend("gpt2", device="cpu")
    llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=512, window_size=128)

    # First call - cold cache
    print("\nFirst call (cold cache):")
    result1 = llm.chat("Hello! How are you today?", max_new_tokens=20)
    print(f"  Cache hits: {result1['stats'].anchor_cache_hits}")

    # Second call - should hit cache for overlapping context
    print("\nSecond call (warm cache):")
    result2 = llm.chat("What's the weather like?", max_new_tokens=20)
    print(f"  Cache hits: {result2['stats'].anchor_cache_hits}")

    # Third call - more cache hits
    print("\nThird call (warmer cache):")
    result3 = llm.chat("Tell me a joke.", max_new_tokens=20)
    print(f"  Cache hits: {result3['stats'].anchor_cache_hits}")

    print(f"\nTotal cache hits: {result3['stats'].anchor_cache_hits}")
    print("✅ Anchor caching reduces redundant tokenization!")


def demo_production_config() -> None:
    """Demo 5: Production-ready configuration."""
    print("\n" + "=" * 60)
    print("DEMO 5: Production Configuration")
    print("=" * 60)

    backend = HuggingFaceBackend("gpt2", device="cpu")

    # Production config with tight latency budget
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="importance",
        max_tokens=2048,
        window_size=512,
        max_policy_ms=100.0,  # 100ms SLA
    )

    print("\n✅ Production Configuration:")
    print(f"  Policy: importance (with sliding fallback)")
    print(f"  Max tokens: 2048")
    print(f"  Window size: 512")
    print(f"  Latency budget: 100ms")
    print(f"  Anchor caching: enabled")

    # Simulate production load
    print("\nSimulating 10 turns...")

    for i in range(10):
        result = llm.chat(f"Message {i}: Tell me about AI.", max_new_tokens=15)

        if i % 3 == 0:  # Print every 3rd turn
            stats = result["stats"]
            print(f"\n  Turn {i+1}:")
            print(f"    Policy latency: {stats.policy_latency_ms:.1f}ms")
            print(f"    Fallbacks: {stats.fallback_count}")
            print(f"    Cache hits: {stats.anchor_cache_hits}")

    final_stats = result["stats"]
    print(f"\n📊 Final Statistics:")
    print(f"  Total policy calls: {final_stats.total_policy_calls}")
    print(f"  Total fallbacks: {final_stats.fallback_count}")
    print(f"  Fallback rate: {final_stats.fallback_count/final_stats.total_policy_calls*100:.1f}%")
    print(f"  Total cache hits: {final_stats.anchor_cache_hits}")


def main() -> None:
    """Run all demos."""
    print("=" * 60)
    print("  LATENCY BUDGETING DEMO - Finite Memory AI v2.1+")
    print("=" * 60)
    print("\nThis demo shows:")
    print("  1. Baseline performance without budget")
    print("  2. Budget enforcement with automatic fallback")
    print("  3. Policy latency comparison")
    print("  4. Anchor caching benefits")
    print("  5. Production-ready configuration")

    try:
        demo_no_budget()
        demo_with_budget()
        demo_policy_comparison()
        demo_anchor_caching()
        demo_production_config()

        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
