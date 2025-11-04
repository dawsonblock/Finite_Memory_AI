# Quick Start Guide

Get started with Finite Memory LLM in 5 minutes.

**Requirements:** Python 3.10 or higher

## Installation

### Option 1: Standard Install

```bash
cd finite-memory-llm
pip install -e .
```

### Option 2: Development Install (recommended)

```bash
cd finite-memory-llm
pip install -e ".[dev]"
```

This installs the package plus development tools: pytest, ruff, black, mypy

### Option 3: Dependencies Only

```bash
cd finite-memory-llm
pip install -r requirements.txt
```

**Modern Python 3.10+:** This package uses latest Python features for better performance and type safety.

## Basic Usage

### 1. Local Model (HuggingFace)

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

# Load a local model
backend = HuggingFaceBackend("gpt2", device="cpu")

# Create LLM with sliding window policy
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="sliding",
    max_tokens=512,
    window_size=128
)

# Chat!
result = llm.chat("Hello, how are you?")
print(result["response"])
```

### 2. Hosted API (OpenAI/Anthropic)

```python
from transformers import AutoTokenizer
from finite_memory_llm import CompleteFiniteMemoryLLM, APIChatBackend

# Load tokenizer for token counting
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Define your API call
def call_my_api(prompt: str, max_new_tokens: int) -> str:
    # Replace with your API call
    # Example for OpenAI:
    # response = openai_client.chat.completions.create(...)
    # return response.choices[0].message.content
    return "Your API response here"

# Wrap in backend
backend = APIChatBackend(tokenizer=tokenizer, send_callable=call_my_api)

# Create LLM
llm = CompleteFiniteMemoryLLM(backend, memory_policy="semantic", max_tokens=4096)
result = llm.chat("Tell me about AI")
```

## Memory Policies

Choose the right policy for your use case:

```python
# Simple FIFO eviction (fastest)
llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")

# Keep high-attention tokens (best for reasoning)
llm = CompleteFiniteMemoryLLM(backend, memory_policy="importance")

# Cluster and compress semantically (best for diverse topics)
llm = CompleteFiniteMemoryLLM(backend, memory_policy="semantic")

# Auto-summarize old context (best for long conversations)
llm = CompleteFiniteMemoryLLM(backend, memory_policy="rolling_summary")
```

## Save & Load Conversations

```python
# Save
llm.save_checkpoint("my_conversation.json")

# Load later
llm.load_checkpoint("my_conversation.json")

# Continue where you left off
result = llm.chat("Remember what we discussed?")
```

## Running Examples

```bash
# Basic chat example
python examples/basic_chat.py

# Compare all policies
python examples/policy_comparison.py

# Checkpoint demo
python examples/checkpoint_demo.py

# Hosted API template
python examples/hosted_api_example.py
```

## Running Tests

```bash
# Using make (recommended)
make test

# Or directly with pytest
pytest tests/ -v

# With coverage
make test-cov
```

## Running Benchmarks

```bash
# Benchmark all policies
python benchmarks/benchmark_policies.py

# Benchmark specific policies
python benchmarks/benchmark_policies.py --policies sliding importance

# Custom configuration
python benchmarks/benchmark_policies.py --messages 50 --max-tokens 1024
```

## Development Tools

```bash
# Format code
make format

# Run linter
make lint

# Type checking
make type-check

# Run all checks
make all-checks
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore [examples/](examples/) for more use cases
3. Check [tests/](tests/) for API usage patterns
4. Run [benchmarks/](benchmarks/) to choose the right policy

## Troubleshooting

### Import Error

If you get import errors, make sure you installed the package:
```bash
pip install -e .
```

### Python Version Error

If you get "SyntaxError: invalid syntax" with type hints like `X | Y`, you need Python 3.10+:
```bash
python --version  # Should show 3.10 or higher
```

### Out of Memory

Reduce `max_tokens` and `window_size`:
```python
llm = CompleteFiniteMemoryLLM(backend, max_tokens=256, window_size=64)
```

### Slow Performance

1. Use "sliding" policy for fastest performance
2. Reduce `max_new_tokens` in chat calls
3. Use GPU if available: `device="cuda"`

### Semantic Policy Not Working

Install sentence-transformers:
```bash
pip install sentence-transformers
```

## Support

For issues, questions, or contributions, please visit the project repository.

