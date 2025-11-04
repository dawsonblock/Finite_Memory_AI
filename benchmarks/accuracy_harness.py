#!/usr/bin/env python3
"""
Accuracy Evaluation Harness - v2.2+

Measures how well memory policies preserve information by testing
recall of facts planted at different positions in the conversation.

This evaluates the accuracy vs compression trade-off for each policy.

Run with:
    python benchmarks/accuracy_harness.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend


@dataclass
class PlantedFact:
    """A fact planted in the conversation for later recall."""

    position: str  # "early", "mid", "late"
    turn: int  # Which turn it was planted
    question: str  # Question to test recall
    answer: str  # Expected answer (keyword)
    context: str  # The statement containing the fact


# Synthetic QA dataset with facts
SYNTHETIC_FACTS = [
    # Early position facts
    PlantedFact(
        position="early",
        turn=1,
        question="What color was the sports car I mentioned?",
        answer="red",
        context="I saw a beautiful red sports car today at the dealership.",
    ),
    PlantedFact(
        position="early",
        turn=2,
        question="What city did I say I was born in?",
        answer="Seattle",
        context="I was born in Seattle, Washington in 1990.",
    ),
    PlantedFact(
        position="early",
        turn=3,
        question="What was my first pet's name?",
        answer="Max",
        context="My first pet was a golden retriever named Max.",
    ),
    # Mid position facts
    PlantedFact(
        position="mid",
        turn=7,
        question="What programming language did I say I learned first?",
        answer="Python",
        context="Python was the first programming language I learned in college.",
    ),
    PlantedFact(
        position="mid",
        turn=9,
        question="What instrument do I play?",
        answer="piano",
        context="I've been playing the piano since I was seven years old.",
    ),
    # Late position facts
    PlantedFact(
        position="late",
        turn=14,
        question="What's my favorite cuisine?",
        answer="Italian",
        context="Italian is definitely my favorite cuisine, especially pasta.",
    ),
    PlantedFact(
        position="late",
        turn=16,
        question="What book am I currently reading?",
        answer="Dune",
        context="I'm currently reading Dune by Frank Herbert.",
    ),
]


# Filler conversations (neutral context)
FILLER_MESSAGES = [
    "Tell me about machine learning.",
    "What's the weather like?",
    "How do neural networks work?",
    "Explain transformers.",
    "What is attention mechanism?",
    "How does backpropagation work?",
    "What is gradient descent?",
    "Tell me about deep learning.",
    "What is a recurrent neural network?",
    "How do you train a model?",
    "What is overfitting?",
    "Explain regularization.",
    "What is dropout?",
    "Tell me about CNNs.",
    "What is transfer learning?",
]


def plant_fact_conversation(
    llm: CompleteFiniteMemoryLLM, fact: PlantedFact, turn_number: int, verbose: bool = False
) -> None:
    """Plant a fact in the conversation."""
    if verbose:
        print(f'  Turn {turn_number}: Planting {fact.position} fact: "{fact.context[:50]}..."')
    llm.chat(fact.context, max_new_tokens=20)


def test_fact_recall(
    llm: CompleteFiniteMemoryLLM, fact: PlantedFact, turn_number: int, verbose: bool = False
) -> bool:
    """Test if the model can recall a planted fact."""
    if verbose:
        print(f"  Turn {turn_number}: Testing {fact.position} fact recall...")

    result = llm.chat(fact.question, max_new_tokens=30)
    response = result["response"].lower()

    # Check if the answer keyword appears in the response
    recalled = fact.answer.lower() in response

    if verbose:
        status = "✓ Recalled" if recalled else "✗ Forgot"
        print(f"    {status}: Looking for '{fact.answer}' in '{response[:60]}'")

    return recalled


def add_filler_turns(
    llm: CompleteFiniteMemoryLLM, n_turns: int, start_turn: int, verbose: bool = False
) -> None:
    """Add filler conversations between facts."""
    for i in range(n_turns):
        msg = random.choice(FILLER_MESSAGES)
        if verbose and i == 0:
            print(f"  ... {n_turns} filler turns ...")
        llm.chat(msg, max_new_tokens=20)


def evaluate_policy(
    policy: str, max_tokens: int = 512, window_size: int = 128, verbose: bool = True
) -> dict[str, Any]:
    """Evaluate a single policy's accuracy."""
    if verbose:
        print(f"\n{'='*70}")
        print(f"Evaluating Policy: {policy}")
        print(f"  max_tokens={max_tokens}, window_size={window_size}")
        print(f"{'='*70}")

    # Initialize LLM
    backend = HuggingFaceBackend("gpt2", device="cpu")
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy=policy,
        max_tokens=max_tokens,
        window_size=window_size,
    )

    # Track results
    results_by_position = {"early": [], "mid": [], "late": []}

    # Run conversation with planted facts
    turn = 1

    for fact in SYNTHETIC_FACTS:
        # Add filler until we reach this fact's turn
        filler_needed = fact.turn - turn
        if filler_needed > 0:
            add_filler_turns(llm, filler_needed, turn, verbose=verbose)
            turn += filler_needed

        # Plant the fact
        plant_fact_conversation(llm, fact, turn, verbose=verbose)
        turn += 1

    # Add more filler to increase memory pressure
    add_filler_turns(llm, 5, turn, verbose=verbose)
    turn += 5

    if verbose:
        print(f"\n  Testing recall after {turn} turns...")

    # Test recall for all facts
    for fact in SYNTHETIC_FACTS:
        recalled = test_fact_recall(llm, fact, turn, verbose=verbose)
        results_by_position[fact.position].append(recalled)
        turn += 1

    # Calculate statistics
    stats = llm.stats
    accuracy_by_position = {
        pos: sum(results) / len(results) if results else 0.0
        for pos, results in results_by_position.items()
    }

    overall_accuracy = sum(sum(results) for results in results_by_position.values()) / sum(
        len(results) for results in results_by_position.values()
    )

    result = {
        "policy": policy,
        "overall_accuracy": overall_accuracy,
        "accuracy_by_position": accuracy_by_position,
        "compression_ratio": stats.compression_ratio,
        "tokens_seen": stats.tokens_seen,
        "tokens_retained": stats.tokens_retained,
        "evictions": stats.evictions,
    }

    if verbose:
        print(f"\n  Results:")
        print(f"    Overall Accuracy: {overall_accuracy:.1%}")
        print(f"    Early Facts:  {accuracy_by_position['early']:.1%}")
        print(f"    Mid Facts:    {accuracy_by_position['mid']:.1%}")
        print(f"    Late Facts:   {accuracy_by_position['late']:.1%}")
        print(f"    Compression:  {stats.compression_ratio:.2f}x")
        print(f"    Evictions:    {stats.evictions}")

    return result


def compare_policies(
    policies: list[str] = ["sliding", "importance", "semantic", "rolling_summary"],
    max_tokens: int = 512,
    verbose: bool = True,
) -> list[dict[str, Any]]:
    """Compare multiple policies on accuracy."""
    print("\n" + "=" * 70)
    print("  ACCURACY EVALUATION HARNESS - Finite Memory AI v2.2+")
    print("=" * 70)
    print(f"\nEvaluating {len(policies)} policies with max_tokens={max_tokens}")
    print(f"Testing recall of {len(SYNTHETIC_FACTS)} planted facts")

    results = []

    for policy in policies:
        try:
            result = evaluate_policy(policy, max_tokens=max_tokens, verbose=verbose)
            results.append(result)
        except Exception as e:
            print(f"⚠ Error evaluating {policy}: {e}")
            import traceback

            traceback.print_exc()

    # Print comparison table
    print("\n" + "=" * 70)
    print("  COMPARISON: Accuracy vs Compression")
    print("=" * 70)
    print(
        f"{'Policy':<15} {'Accuracy':<12} {'Early':<10} {'Mid':<10} {'Late':<10} {'Compression':<12}"
    )
    print("-" * 70)

    for r in results:
        acc = r["overall_accuracy"]
        early = r["accuracy_by_position"]["early"]
        mid = r["accuracy_by_position"]["mid"]
        late = r["accuracy_by_position"]["late"]
        comp = r["compression_ratio"]

        print(
            f"{r['policy']:<15} {acc:>6.1%}        {early:>5.1%}      {mid:>5.1%}      {late:>5.1%}      {comp:>6.2f}x"
        )

    # Find best policy
    if results:
        best = max(results, key=lambda x: x["overall_accuracy"])
        print(f"\n🏆 Best Accuracy: {best['policy']} ({best['overall_accuracy']:.1%})")

        best_compression = max(results, key=lambda x: x["compression_ratio"])
        print(
            f"📊 Best Compression: {best_compression['policy']} ({best_compression['compression_ratio']:.2f}x)"
        )

    print("=" * 70)

    return results


def main() -> None:
    """Run the accuracy harness."""
    random.seed(42)  # For reproducibility

    # Test all policies
    results = compare_policies(
        policies=["sliding", "importance", "rolling_summary"], max_tokens=512, verbose=True
    )

    print("\n✅ Accuracy evaluation complete!")
    print("\n📈 Key Insights:")
    print("  • 'Late' facts should have highest recall (most recent)")
    print("  • 'Early' facts test long-term memory retention")
    print("  • Trade-off: Higher compression often means lower accuracy")
    print("  • Importance policy should preserve high-value facts better")


if __name__ == "__main__":
    main()
