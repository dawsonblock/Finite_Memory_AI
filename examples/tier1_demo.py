"""Demo of Tier-1 upgraded features.

Shows:
- Embedding cache with MiniBatchKMeans
- Latency guard with automatic fallback
- Summary QA gate
- Enhanced telemetry
"""

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend


def demo_tier1_semantic():
    """Demo Tier-1 semantic policy with embedding cache."""
    print("\n" + "=" * 70)
    print("TIER-1 DEMO: Semantic Policy with Embedding Cache")
    print("=" * 70 + "\n")

    backend = HuggingFaceBackend("gpt2", device="cpu")

    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="semantic",
        max_tokens=512,
        window_size=128,
        semantic_clusters=6,
        max_policy_ms=2000,  # 2 second budget
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    )

    # Check if Tier-1 is enabled
    if llm._use_upgrades:
        print("✓ Tier-1 upgrades detected!")
        print(f"  - Embedding cache: {llm._span_embedder is not None}")
        print(f"  - QA gate: {llm._qa_gate is not None}")
    else:
        print("⚠ Tier-1 upgrades not available (missing dependencies)")

    print("\nRunning conversation with semantic clustering...\n")

    conversation = [
        "The project budget is $150,000 for Q1 2024.",
        "Alice is the lead engineer and Bob is the project manager.",
        "The deadline is March 31, 2024.",
        "Can you remind me of the budget and deadline?",
    ]

    for i, msg in enumerate(conversation, 1):
        print(f"[Turn {i}] User: {msg}")
        result = llm.chat(msg, max_new_tokens=40)
        print(f"[Turn {i}] Bot: {result['response']}")

        stats = result["stats"]
        print(f"  → Tokens: {stats.tokens_seen} seen, {stats.tokens_retained} retained")
        print(f"  → Compression: {stats.compression_ratio:.2f}x")
        print(f"  → Policy latency: {stats.policy_latency_ms:.1f}ms")

        if llm._span_embedder:
            cache_stats = llm._span_embedder.get_cache_stats()
            print(
                f"  → Embedding cache: {cache_stats['cache_size']} entries, "
                f"{cache_stats['hit_rate']:.1%} hit rate"
            )

        print()

    print("=" * 70)
    print(
        f"Final stats: {llm.stats.tokens_seen} tokens seen, "
        f"{llm.stats.evictions} evicted, "
        f"{llm.stats.fallback_count} fallbacks"
    )
    print("=" * 70)


def demo_tier1_rolling_summary():
    """Demo Tier-1 rolling summary with QA gate."""
    print("\n" + "=" * 70)
    print("TIER-1 DEMO: Rolling Summary with QA Gate")
    print("=" * 70 + "\n")

    backend = HuggingFaceBackend("gpt2", device="cpu")

    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="rolling_summary",
        max_tokens=512,
        window_size=128,
        summary_interval=200,
        max_policy_ms=3000,
    )

    print(f"QA gate active: {llm._qa_gate is not None}\n")

    conversation = [
        "John's salary is $85,000 per year.",
        "He started on January 15, 2023.",
        "His employee ID is EMP-12345.",
        "What is John's salary and start date?",
    ]

    for i, msg in enumerate(conversation, 1):
        print(f"[Turn {i}] User: {msg}")
        result = llm.chat(msg, max_new_tokens=30)
        print(f"[Turn {i}] Bot: {result['response']}")

        if result["stats"].summaries_created > 0:
            print(f"  ✓ Summary created (verified by QA gate)")

        print()


def demo_tier1_latency_budget():
    """Demo Tier-1 latency budgeting with fallback."""
    print("\n" + "=" * 70)
    print("TIER-1 DEMO: Latency Budget Enforcement")
    print("=" * 70 + "\n")

    backend = HuggingFaceBackend("gpt2", device="cpu")

    # Set a very tight budget to trigger fallbacks
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="semantic",
        max_tokens=1024,
        window_size=256,
        semantic_clusters=20,  # High cluster count = slow
        max_policy_ms=50,  # Very tight budget
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    )

    print("Testing with tight latency budget (50ms)...\n")

    # Generate long context to stress the policy
    for i in range(5):
        msg = f"This is message {i} with some content to fill the context."
        result = llm.chat(msg, max_new_tokens=20)

        stats = result["stats"]
        print(
            f"Turn {i+1}: Policy took {stats.policy_latency_ms:.1f}ms, "
            f"fallbacks={stats.fallback_count}"
        )

    print(f"\n✓ Total fallbacks: {llm.stats.fallback_count}")


if __name__ == "__main__":
    try:
        demo_tier1_semantic()
    except ImportError as e:
        print(f"⚠ Skipping semantic demo: {e}")

    try:
        demo_tier1_rolling_summary()
    except Exception as e:
        print(f"⚠ Skipping rolling summary demo: {e}")

    try:
        demo_tier1_latency_budget()
    except Exception as e:
        print(f"⚠ Skipping latency budget demo: {e}")
