#!/usr/bin/env python3
"""
Policy Comparison Example

Compares all four memory policies side-by-side:
- Sliding window
- Importance-based
- Semantic clustering
- Rolling summary
"""

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend
import time


def run_policy_test(policy_name: str, backend: HuggingFaceBackend, test_messages: list):
    """Run a test conversation with a specific policy."""
    print(f"\n{'=' * 70}")
    print(f"Testing Policy: {policy_name.upper()}")
    print(f"{'=' * 70}\n")
    
    # Initialize LLM with the specified policy
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy=policy_name,
        max_tokens=512,
        window_size=128,
        semantic_clusters=4,
        summary_interval=200,
    )
    
    start_time = time.time()
    
    for i, msg in enumerate(test_messages, 1):
        print(f"[Turn {i}] User: {msg}")
        result = llm.chat(msg, max_new_tokens=30)
        print(f"[Turn {i}] Assistant: {result['response'][:100]}...")
        print(f"  Stats: context={result['context_length']}, evictions={result['stats'].evictions}")
        print()
    
    elapsed = time.time() - start_time
    
    # Final statistics
    print(f"{'─' * 70}")
    print(f"Final Statistics for {policy_name}:")
    print(f"  Total tokens seen: {llm.stats.tokens_seen}")
    print(f"  Tokens retained: {llm.stats.tokens_retained}")
    print(f"  Total evictions: {llm.stats.evictions}")
    print(f"  Compression ratio: {llm.stats.compression_ratio:.2f}x")
    print(f"  Summaries created: {llm.stats.summaries_created}")
    print(f"  Clusters merged: {llm.stats.clusters_merged}")
    print(f"  Importance evictions: {llm.stats.importance_evictions}")
    print(f"  Time elapsed: {elapsed:.2f}s")
    print(f"{'─' * 70}")
    
    return {
        "policy": policy_name,
        "tokens_seen": llm.stats.tokens_seen,
        "tokens_retained": llm.stats.tokens_retained,
        "evictions": llm.stats.evictions,
        "compression_ratio": llm.stats.compression_ratio,
        "time": elapsed,
    }


def main():
    print("\n" + "=" * 70)
    print("MEMORY POLICY COMPARISON")
    print("=" * 70)
    
    # Load model once and reuse
    print("\nLoading model...")
    backend = HuggingFaceBackend("gpt2", device="cpu")
    
    # Test conversation with diverse topics
    test_messages = [
        "Hello! Tell me about the solar system.",
        "What is the largest planet?",
        "Now tell me about quantum physics.",
        "What is quantum entanglement?",
        "Let's switch topics. Who wrote Hamlet?",
        "What year was it written?",
        "Back to our first topic - how many planets are there?",
        "What was the first thing I asked you about?",
    ]
    
    # Test each policy
    policies = ["sliding", "importance", "semantic", "rolling_summary"]
    results = []
    
    for policy in policies:
        result = run_policy_test(policy, backend, test_messages)
        results.append(result)
        time.sleep(1)  # Brief pause between tests
    
    # Summary comparison table
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Policy':<20} {'Seen':<10} {'Kept':<10} {'Evicted':<10} {'Ratio':<10} {'Time (s)':<10}")
    print("─" * 70)
    
    for r in results:
        print(f"{r['policy']:<20} {r['tokens_seen']:<10} {r['tokens_retained']:<10} "
              f"{r['evictions']:<10} {r['compression_ratio']:<10.2f} {r['time']:<10.2f}")
    
    print("=" * 70)
    print("\nKey Observations:")
    print("  - Sliding: Simple FIFO eviction, predictable behavior")
    print("  - Importance: Keeps high-attention tokens (requires local model)")
    print("  - Semantic: Clusters similar content, good for topic diversity")
    print("  - Rolling Summary: Compresses old context into summaries")
    print("=" * 70)


if __name__ == "__main__":
    main()

