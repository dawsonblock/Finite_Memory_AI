#!/usr/bin/env python3
"""
Basic Chat Example

Demonstrates simple conversation using local HuggingFace model
with sliding window memory policy.
"""

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend


def main():
    print("=" * 70)
    print("BASIC CHAT EXAMPLE - Local HuggingFace Model")
    print("=" * 70)

    # Initialize backend with a small local model
    print("\n[1/3] Loading model...")
    backend = HuggingFaceBackend("gpt2", device="cpu")

    # Create LLM with sliding memory policy
    print("[2/3] Initializing finite memory LLM...")
    llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=512, window_size=128)

    # Simple conversation
    print("[3/3] Starting conversation...\n")

    conversation = [
        "Hello! My name is Alice.",
        "What's my name?",
        "Tell me about artificial intelligence.",
        "Can you remember what we discussed earlier?",
    ]

    for i, user_msg in enumerate(conversation, 1):
        print(f"\n{'─' * 70}")
        print(f"[Turn {i}] User: {user_msg}")

        result = llm.chat(user_msg, max_new_tokens=50)

        print(f"[Turn {i}] Assistant: {result['response']}")
        print(f"\nStats:")
        print(f"  - Tokens used: {result['tokens_used']}")
        print(f"  - Context length: {result['context_length']}")
        print(f"  - Total tokens seen: {result['stats'].tokens_seen}")
        print(f"  - Tokens retained: {result['stats'].tokens_retained}")
        print(f"  - Evictions: {result['stats'].evictions}")

    print(f"\n{'=' * 70}")
    print("Conversation complete!")
    print(f"{'=' * 70}")

    # Show final context window
    print("\nFinal context window:")
    print("─" * 70)
    print(llm.get_context_window()[:500] + "...")


if __name__ == "__main__":
    main()
