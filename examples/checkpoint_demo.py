#!/usr/bin/env python3
"""
Checkpoint Demo

Demonstrates saving and loading conversation state,
allowing you to pause and resume conversations.
"""

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend
from pathlib import Path


def save_conversation_demo():
    """Create a conversation and save it."""
    print("=" * 70)
    print("CHECKPOINT DEMO - Saving Conversation")
    print("=" * 70)

    # Initialize
    print("\n[1/5] Loading model...")
    backend = HuggingFaceBackend("gpt2", device="cpu")

    print("[2/5] Creating LLM with importance policy...")
    llm = CompleteFiniteMemoryLLM(
        backend, memory_policy="importance", max_tokens=512, window_size=128
    )

    # Have a conversation
    print("[3/5] Starting conversation...\n")

    messages = [
        "My favorite color is blue.",
        "I enjoy reading science fiction books.",
        "What's my favorite color?",
    ]

    for i, msg in enumerate(messages, 1):
        print(f"[Turn {i}] User: {msg}")
        result = llm.chat(msg, max_new_tokens=40)
        print(f"[Turn {i}] Assistant: {result['response']}")
        print()

    # Save checkpoint
    print("[4/5] Saving checkpoint...")
    checkpoint_path = Path("checkpoints")
    checkpoint_path.mkdir(exist_ok=True)

    saved_path = llm.save_checkpoint("checkpoints/demo_conversation.json")
    print(f"✓ Saved to: {saved_path}")

    # Show statistics
    print(f"\n[5/5] Conversation statistics:")
    print(f"  Tokens seen: {llm.stats.tokens_seen}")
    print(f"  Tokens retained: {llm.stats.tokens_retained}")
    print(f"  Evictions: {llm.stats.evictions}")
    print(f"  Turns: {len(llm.conversation_history) // 2}")

    print("\n" + "=" * 70)
    print("Conversation saved successfully!")
    print("=" * 70)

    return saved_path


def load_conversation_demo(checkpoint_path):
    """Load a saved conversation and continue it."""
    print("\n\n" + "=" * 70)
    print("CHECKPOINT DEMO - Loading Conversation")
    print("=" * 70)

    # Initialize new LLM instance
    print("\n[1/4] Loading model...")
    backend = HuggingFaceBackend("gpt2", device="cpu")

    print("[2/4] Creating new LLM instance...")
    llm = CompleteFiniteMemoryLLM(
        backend, memory_policy="importance", max_tokens=512, window_size=128
    )

    # Load checkpoint
    print(f"[3/4] Loading checkpoint from {checkpoint_path}...")
    config = llm.load_checkpoint(checkpoint_path)

    print(f"\nRestored configuration:")
    print(f"  Policy: {config['memory_policy']}")
    print(f"  Max tokens: {config['max_tokens']}")
    print(f"  Window size: {config['window_size']}")
    print(f"  Turns restored: {len(llm.conversation_history) // 2}")

    # Show conversation history
    print(f"\n[4/4] Previous conversation:")
    print("─" * 70)
    for entry in llm.conversation_history:
        role = entry["role"].capitalize()
        content = entry["content"][:100]
        print(f"{role}: {content}")
    print("─" * 70)

    # Continue the conversation
    print("\nContinuing conversation...\n")

    new_messages = [
        "Do you remember what I said about books?",
        "Great! Now tell me about machine learning.",
    ]

    for i, msg in enumerate(new_messages, 1):
        turn_num = len(llm.conversation_history) // 2 + i
        print(f"[Turn {turn_num}] User: {msg}")
        result = llm.chat(msg, max_new_tokens=40)
        print(f"[Turn {turn_num}] Assistant: {result['response']}")
        print()

    print("=" * 70)
    print("Conversation continued successfully!")
    print(f"Total turns now: {len(llm.conversation_history) // 2}")
    print("=" * 70)


def demonstrate_multiple_checkpoints():
    """Show how to manage multiple conversation checkpoints."""
    print("\n\n" + "=" * 70)
    print("MULTIPLE CHECKPOINTS DEMO")
    print("=" * 70)

    backend = HuggingFaceBackend("gpt2", device="cpu")

    # Create different conversation types
    scenarios = [
        ("tech_talk", "importance", ["Tell me about Python.", "What's a decorator?"]),
        ("casual_chat", "sliding", ["Hello!", "How are you?"]),
        ("story_mode", "rolling_summary", ["Once upon a time...", "What happened next?"]),
    ]

    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)

    saved_checkpoints = []

    for name, policy, messages in scenarios:
        print(f"\n{name.replace('_', ' ').title()} ({policy} policy):")
        print("─" * 70)

        llm = CompleteFiniteMemoryLLM(backend, memory_policy=policy, max_tokens=256)

        for msg in messages:
            result = llm.chat(msg, max_new_tokens=30)
            print(f"User: {msg}")
            print(f"Assistant: {result['response'][:80]}...")

        checkpoint_path = checkpoint_dir / f"{name}.json"
        llm.save_checkpoint(checkpoint_path)
        saved_checkpoints.append((name, checkpoint_path))
        print(f"✓ Saved: {checkpoint_path}")

    print("\n" + "=" * 70)
    print("Saved Checkpoints:")
    print("─" * 70)
    for name, path in saved_checkpoints:
        print(f"  {name}: {path}")
    print("=" * 70)
    print("\nYou can now load any of these conversations later!")


def main():
    # Demo 1: Save a conversation
    checkpoint_path = save_conversation_demo()

    # Demo 2: Load and continue
    load_conversation_demo(checkpoint_path)

    # Demo 3: Multiple checkpoints
    demonstrate_multiple_checkpoints()

    print("\n" + "=" * 70)
    print("All checkpoint demos complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
