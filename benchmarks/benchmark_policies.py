#!/usr/bin/env python3
"""
Benchmark Memory Policies

Comprehensive performance and memory benchmarking for all memory policies.
Measures:
  - Token throughput (tokens/second)
  - Memory overhead
  - Context compression effectiveness
  - Response latency
"""

import time
import tracemalloc
import statistics
from typing import Dict, List, Any

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend


class PolicyBenchmark:
    """Benchmark runner for memory policies."""

    def __init__(self, model_name: str = "gpt2", device: str = "cpu"):
        """Initialize benchmark with model."""
        print(f"Loading model: {model_name}")
        self.backend = HuggingFaceBackend(model_name, device=device)
        self.device = device
        print("✓ Model loaded\n")

    def generate_test_messages(self, count: int = 20) -> List[str]:
        """Generate diverse test messages."""
        messages = [
            "Hello! Tell me about the solar system.",
            "What is the largest planet?",
            "How far is Earth from the Sun?",
            "Tell me about quantum physics.",
            "What is quantum entanglement?",
            "Explain the double-slit experiment.",
            "Now let's discuss history. Who was Napoleon?",
            "When was World War II?",
            "What caused the French Revolution?",
            "Switch to technology. What is machine learning?",
            "How do neural networks work?",
            "What is deep learning?",
            "Let's talk about literature. Who wrote Hamlet?",
            "What is the theme of Romeo and Juliet?",
            "Tell me about Shakespeare's life.",
            "Back to science - what is DNA?",
            "How does evolution work?",
            "What is natural selection?",
            "Return to our first topic - how many planets are there?",
            "What was the first thing we discussed?",
        ]
        return messages[:count]

    def benchmark_policy(
        self,
        policy_name: str,
        messages: List[str],
        max_tokens: int = 512,
        window_size: int = 128,
        max_new_tokens: int = 30,
    ) -> Dict[str, Any]:
        """Run benchmark for a single policy."""
        print(f"{'=' * 70}")
        print(f"Benchmarking: {policy_name.upper()}")
        print(f"{'=' * 70}\n")

        # Initialize LLM with policy
        llm = CompleteFiniteMemoryLLM(
            self.backend,
            max_tokens=max_tokens,
            memory_policy=policy_name,
            window_size=window_size,
            semantic_clusters=4,
            summary_interval=200,
            device=self.device,
        )

        # Track metrics
        latencies = []
        memory_samples = []
        tokens_per_turn = []

        # Start memory tracking
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0]

        # Benchmark start
        total_start = time.time()

        for i, msg in enumerate(messages, 1):
            turn_start = time.time()

            # Generate response
            result = llm.chat(msg, max_new_tokens=max_new_tokens)

            turn_end = time.time()
            turn_latency = turn_end - turn_start

            latencies.append(turn_latency)
            tokens_per_turn.append(result["tokens_used"])

            # Sample memory usage
            current_memory = tracemalloc.get_traced_memory()[0]
            memory_samples.append(current_memory - start_memory)

            # Progress indicator
            if i % 5 == 0:
                print(f"  Completed {i}/{len(messages)} turns...")

        total_end = time.time()
        total_time = total_end - total_start

        # Final memory snapshot
        peak_memory = tracemalloc.get_traced_memory()[1] - start_memory
        tracemalloc.stop()

        # Calculate metrics
        total_tokens_generated = sum(tokens_per_turn)
        throughput = total_tokens_generated / total_time if total_time > 0 else 0
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        std_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0
        avg_memory = statistics.mean(memory_samples)

        # Compression metrics
        compression_ratio = llm.stats.compression_ratio
        eviction_rate = llm.stats.evictions / max(llm.stats.tokens_seen, 1)

        results = {
            "policy": policy_name,
            "total_time": total_time,
            "total_turns": len(messages),
            "total_tokens_generated": total_tokens_generated,
            "throughput_tokens_per_sec": throughput,
            "avg_latency_sec": avg_latency,
            "median_latency_sec": median_latency,
            "std_latency_sec": std_latency,
            "min_latency_sec": min(latencies),
            "max_latency_sec": max(latencies),
            "avg_memory_bytes": avg_memory,
            "peak_memory_bytes": peak_memory,
            "avg_memory_mb": avg_memory / (1024 * 1024),
            "peak_memory_mb": peak_memory / (1024 * 1024),
            "tokens_seen": llm.stats.tokens_seen,
            "tokens_retained": llm.stats.tokens_retained,
            "evictions": llm.stats.evictions,
            "compression_ratio": compression_ratio,
            "eviction_rate": eviction_rate,
            "summaries_created": llm.stats.summaries_created,
            "clusters_merged": llm.stats.clusters_merged,
            "importance_evictions": llm.stats.importance_evictions,
        }

        # Print summary
        print(f"\n{'─' * 70}")
        print("Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} tokens/sec")
        print(f"  Avg latency: {avg_latency:.3f}s")
        print(f"  Peak memory: {peak_memory / (1024 * 1024):.2f} MB")
        print(f"  Compression ratio: {compression_ratio:.2f}x")
        print(f"  Evictions: {llm.stats.evictions}")
        print(f"{'─' * 70}\n")

        return results

    def run_all_benchmarks(
        self,
        policies: List[str] = None,
        num_messages: int = 20,
        max_tokens: int = 512,
    ) -> List[Dict[str, Any]]:
        """Run benchmarks for all policies."""
        if policies is None:
            policies = ["sliding", "importance", "rolling_summary"]
            # Note: semantic excluded by default due to longer runtime

        print("\n" + "=" * 70)
        print("COMPREHENSIVE POLICY BENCHMARK")
        print("=" * 70)
        print(f"\nConfiguration:")
        print(f"  Policies: {', '.join(policies)}")
        print(f"  Messages: {num_messages}")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Device: {self.device}")
        print()

        messages = self.generate_test_messages(num_messages)
        results = []

        for policy in policies:
            try:
                result = self.benchmark_policy(
                    policy,
                    messages,
                    max_tokens=max_tokens,
                )
                results.append(result)
                time.sleep(1)  # Brief pause between benchmarks
            except Exception as e:
                print(f"⚠ Benchmark failed for {policy}: {e}\n")

        return results

    def print_comparison_table(self, results: List[Dict[str, Any]]):
        """Print comparison table of all results."""
        if not results:
            print("No results to display.")
            return

        print("\n" + "=" * 70)
        print("BENCHMARK COMPARISON")
        print("=" * 70)

        # Performance metrics
        print("\n--- Performance ---")
        print(f"{'Policy':<20} {'Throughput':<15} {'Avg Latency':<15} {'Total Time':<15}")
        print("─" * 70)
        for r in results:
            print(
                f"{r['policy']:<20} "
                f"{r['throughput_tokens_per_sec']:<15.2f} "
                f"{r['avg_latency_sec']:<15.3f} "
                f"{r['total_time']:<15.2f}"
            )

        # Memory metrics
        print("\n--- Memory Usage ---")
        print(f"{'Policy':<20} {'Avg Memory (MB)':<20} {'Peak Memory (MB)':<20}")
        print("─" * 70)
        for r in results:
            print(
                f"{r['policy']:<20} "
                f"{r['avg_memory_mb']:<20.2f} "
                f"{r['peak_memory_mb']:<20.2f}"
            )

        # Compression metrics
        print("\n--- Compression ---")
        print(
            f"{'Policy':<20} {'Tokens Seen':<15} {'Retained':<15} {'Ratio':<15} {'Evictions':<15}"
        )
        print("─" * 70)
        for r in results:
            print(
                f"{r['policy']:<20} "
                f"{r['tokens_seen']:<15} "
                f"{r['tokens_retained']:<15} "
                f"{r['compression_ratio']:<15.2f} "
                f"{r['evictions']:<15}"
            )

        # Policy-specific metrics
        print("\n--- Policy-Specific ---")
        print(f"{'Policy':<20} {'Summaries':<15} {'Clusters Merged':<20} {'Importance Evict':<20}")
        print("─" * 70)
        for r in results:
            print(
                f"{r['policy']:<20} "
                f"{r['summaries_created']:<15} "
                f"{r['clusters_merged']:<20} "
                f"{r['importance_evictions']:<20}"
            )

        print("=" * 70)

        # Recommendations
        print("\n--- Recommendations ---\n")

        # Find best throughput
        best_throughput = max(results, key=lambda r: r["throughput_tokens_per_sec"])
        print(
            f"  Highest throughput: {best_throughput['policy']} "
            f"({best_throughput['throughput_tokens_per_sec']:.2f} tokens/sec)"
        )

        # Find lowest memory
        best_memory = min(results, key=lambda r: r["peak_memory_mb"])
        print(
            f"  Lowest memory usage: {best_memory['policy']} "
            f"({best_memory['peak_memory_mb']:.2f} MB)"
        )

        # Find best compression
        best_compression = max(results, key=lambda r: r["compression_ratio"])
        print(
            f"  Best compression: {best_compression['policy']} "
            f"({best_compression['compression_ratio']:.2f}x)"
        )

        print("\n" + "=" * 70)


def main():
    """Run comprehensive benchmark suite."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark finite memory policies")
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["sliding", "importance", "rolling_summary"],
        help="Policies to benchmark (default: sliding importance rolling_summary)",
    )
    parser.add_argument(
        "--messages", type=int, default=20, help="Number of test messages (default: 20)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=512, help="Max tokens for memory (default: 512)"
    )
    parser.add_argument("--model", default="gpt2", help="Model name (default: gpt2)")
    parser.add_argument("--device", default="cpu", help="Device (cpu or cuda) (default: cpu)")

    args = parser.parse_args()

    # Run benchmarks
    benchmark = PolicyBenchmark(model_name=args.model, device=args.device)
    results = benchmark.run_all_benchmarks(
        policies=args.policies,
        num_messages=args.messages,
        max_tokens=args.max_tokens,
    )

    # Print comparison
    benchmark.print_comparison_table(results)

    # Optionally save results
    try:
        import json
        from pathlib import Path

        output_dir = Path("benchmark_results")
        output_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"benchmark_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✓ Results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠ Could not save results: {e}")


if __name__ == "__main__":
    main()
