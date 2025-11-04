#!/usr/bin/env python3
"""
Hosted API Example

Demonstrates how to use finite memory with hosted APIs
like OpenAI, Anthropic, or other cloud providers.
"""

from transformers import AutoTokenizer
from finite_memory_llm import CompleteFiniteMemoryLLM, APIChatBackend


def openai_example():
    """
    Example using OpenAI API (requires openai package).
    Uncomment and configure to use.
    """
    # from openai import OpenAI
    # 
    # client = OpenAI(api_key="your-api-key-here")
    # 
    # def call_openai(prompt: str, max_new_tokens: int) -> str:
    #     response = client.chat.completions.create(
    #         model="gpt-4o-mini",
    #         messages=[{"role": "user", "content": prompt}],
    #         max_tokens=max_new_tokens,
    #         temperature=0.7,
    #     )
    #     return response.choices[0].message.content
    # 
    # # Use GPT-2 tokenizer for token counting (close approximation)
    # tokenizer = AutoTokenizer.from_pretrained("gpt2")
    # 
    # backend = APIChatBackend(
    #     tokenizer=tokenizer,
    #     send_callable=call_openai,
    #     name="openai-gpt4"
    # )
    # 
    # llm = CompleteFiniteMemoryLLM(
    #     backend,
    #     memory_policy="semantic",
    #     max_tokens=4096,
    #     window_size=1024
    # )
    # 
    # result = llm.chat("Explain quantum computing in simple terms.")
    # print(result["response"])
    
    pass


def anthropic_example():
    """
    Example using Anthropic API (requires anthropic package).
    Uncomment and configure to use.
    """
    # import anthropic
    # 
    # client = anthropic.Anthropic(api_key="your-api-key-here")
    # 
    # def call_anthropic(prompt: str, max_new_tokens: int) -> str:
    #     message = client.messages.create(
    #         model="claude-3-sonnet-20240229",
    #         max_tokens=max_new_tokens,
    #         messages=[{"role": "user", "content": prompt}]
    #     )
    #     return message.content[0].text
    # 
    # tokenizer = AutoTokenizer.from_pretrained("gpt2")
    # 
    # backend = APIChatBackend(
    #     tokenizer=tokenizer,
    #     send_callable=call_anthropic,
    #     name="anthropic-claude"
    # )
    # 
    # llm = CompleteFiniteMemoryLLM(
    #     backend,
    #     memory_policy="importance",
    #     max_tokens=8192,
    #     window_size=2048
    # )
    # 
    # result = llm.chat("Write a short poem about the ocean.")
    # print(result["response"])
    
    pass


def mock_api_example():
    """
    Mock example that demonstrates the structure without requiring API keys.
    """
    print("=" * 70)
    print("HOSTED API EXAMPLE - Mock Backend")
    print("=" * 70)
    
    # Load tokenizer for token counting
    print("\n[1/3] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    
    # Create a mock API callable (replace with real API call)
    def mock_api_call(prompt: str, max_new_tokens: int) -> str:
        """
        Mock API response. Replace this with your actual API call:
        
        For OpenAI:
            response = openai_client.chat.completions.create(...)
            return response.choices[0].message.content
        
        For Anthropic:
            message = anthropic_client.messages.create(...)
            return message.content[0].text
        """
        # This is just a placeholder response
        return f"[Mock API Response] I received your prompt with {len(prompt)} characters."
    
    # Wrap in APIChatBackend
    print("[2/3] Creating API backend...")
    backend = APIChatBackend(
        tokenizer=tokenizer,
        send_callable=mock_api_call,
        name="mock-api"
    )
    
    # Initialize LLM with semantic memory for long conversations
    print("[3/3] Initializing finite memory LLM with semantic policy...")
    llm = CompleteFiniteMemoryLLM(
        backend,
        memory_policy="semantic",
        max_tokens=2048,
        window_size=512,
        semantic_clusters=4
    )
    
    print("\n" + "─" * 70)
    print("Testing with mock API...\n")
    
    # Test conversation
    messages = [
        "Hello! Tell me about machine learning.",
        "What are neural networks?",
        "How does backpropagation work?",
    ]
    
    for i, msg in enumerate(messages, 1):
        print(f"[Turn {i}] User: {msg}")
        result = llm.chat(msg, max_new_tokens=100)
        print(f"[Turn {i}] Assistant: {result['response']}")
        print(f"  Context: {result['context_length']} tokens\n")
    
    print("─" * 70)
    print("\nTo use with real APIs:")
    print("  1. Install the appropriate SDK (openai, anthropic, etc.)")
    print("  2. Replace mock_api_call with your actual API function")
    print("  3. Set your API key as environment variable or in code")
    print("  4. Adjust max_tokens to match your API's context limits")
    print("=" * 70)


def main():
    # Run the mock example
    mock_api_example()
    
    # Uncomment to try real APIs (after adding credentials):
    # openai_example()
    # anthropic_example()


if __name__ == "__main__":
    main()

