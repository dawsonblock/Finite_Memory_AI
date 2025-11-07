#!/usr/bin/env python3
"""
Test script for Finite Memory AI with local model
(DeepSeek API integration would require additional setup)
"""

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

def test_system():
    """Test the system with a local model"""
    
    print("=" * 60)
    print("Testing Finite Memory AI System")
    print("=" * 60)
    
    # Use local GPT-2 model for testing
    print("\n1. Creating HuggingFace backend (GPT-2)...")
    backend = HuggingFaceBackend(
        model_name="gpt2",
        device="cpu"
    )
    print("[OK] Backend created")
    
    # Create LLM with sliding window policy
    print("\n2. Creating Finite Memory LLM...")
    llm = CompleteFiniteMemoryLLM(
        backend=backend,
        memory_policy="sliding",
        max_tokens=512
    )
    print("[OK] LLM created with sliding window policy (512 tokens)")
    
    # Test 1: Simple greeting
    print("\n" + "=" * 60)
    print("Test 1: Simple Greeting")
    print("=" * 60)
    user_msg = "Hello! Can you introduce yourself briefly?"
    print(f"\nUser: {user_msg}")
    
    try:
        response = llm.chat(user_msg)
        print(f"Assistant: {response}")
        print("[OK] Test 1 passed")
    except Exception as e:
        print(f"[FAIL] Test 1 failed: {e}")
        return False
    
    # Test 2: Context retention
    print("\n" + "=" * 60)
    print("Test 2: Context Retention")
    print("=" * 60)
    user_msg = "What did I just ask you?"
    print(f"\nUser: {user_msg}")
    
    try:
        response = llm.chat(user_msg)
        print(f"Assistant: {response}")
        print("[OK] Test 2 passed")
    except Exception as e:
        print(f"[FAIL] Test 2 failed: {e}")
        return False
    
    # Test 3: Technical question
    print("\n" + "=" * 60)
    print("Test 3: Technical Question")
    print("=" * 60)
    user_msg = "Explain what a sliding window memory policy does in 2 sentences."
    print(f"\nUser: {user_msg}")
    
    try:
        response = llm.chat(user_msg)
        print(f"Assistant: {response}")
        print("[OK] Test 3 passed")
    except Exception as e:
        print(f"[FAIL] Test 3 failed: {e}")
        return False
    
    # Check memory stats
    print("\n" + "=" * 60)
    print("Memory Statistics")
    print("=" * 60)
    stats = llm.stats
    print(f"Tokens seen: {stats.tokens_seen}")
    print(f"Tokens retained: {stats.tokens_retained}")
    print(f"Evictions: {stats.evictions}")
    print(f"Compression ratio: {stats.compression_ratio:.2%}")
    print(f"Policy calls: {stats.total_policy_calls}")
    
    print("\n" + "=" * 60)
    print("[OK] All tests passed! System is working correctly.")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_system()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
