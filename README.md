# 🧠 Finite Memory AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: ruff](https://img.shields.io/badge/linter-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

**Production-ready finite memory and context distillation for large language models.**

Finite Memory AI gives any LLM **long-term conversational memory** with controlled context growth through intelligent compression. Works seamlessly with both local models (HuggingFace) and hosted APIs (OpenAI, Anthropic, etc.).

## 🌟 Why Finite Memory AI?

LLMs typically re-process the entire prompt history on every turn, leading to:
- 💸 **Exponentially growing costs**
- 🐌 **Slower response times**
- 💥 **Context limit overflows**
- 🔄 **Redundant reprocessing**

**Finite Memory AI solves this** by acting as an intelligent memory manager that sits between you and the LLM, optimizing prompts before each generation.

### Key Features

| Feature | Description | Benefit |
|---------|-------------|---------|
| **🎯 Finite Memory** | Controlled context with automatic eviction policies | No more context overflow |
| **🧬 Context Distillation** | Builds information-dense, short prompts | Faster & cheaper responses |
| **🔥 Importance-Based Retention** | Keeps high-attention and valuable tokens | Preserves critical information |
| **🧠 Semantic Memory** | Clusters and compresses by meaning | Handles diverse topics gracefully |
| **📝 Rolling Summaries** | Auto-compresses old context | Maintains long-term coherence |
| **🔌 Universal Compatibility** | Works with any LLM (local or hosted) | No model modification needed |
| **⚡ Modern Python 3.10+** | Latest type hints, performance optimizations | Clean, maintainable code |

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/dawsonblock/Finite_Memory_AI.git
cd Finite_Memory_AI

# Install with development tools
pip install -e ".[dev]"
```

### Basic Usage

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

# Initialize with a local model
backend = HuggingFaceBackend("gpt2", device="cpu")
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="sliding",  # Choose: sliding, importance, semantic, rolling_summary
    max_tokens=512,
    window_size=128
)

# Chat with finite memory!
result = llm.chat("What is the capital of France?")
print(result["response"])

# Continue the conversation - old context automatically managed
result = llm.chat("What about Germany?")
print(result["response"])
```

### With Hosted APIs (OpenAI, Anthropic, etc.)

```python
from transformers import AutoTokenizer
from finite_memory_llm import CompleteFiniteMemoryLLM, APIChatBackend
import openai

# Initialize tokenizer for token counting
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Define your API call
def call_openai(prompt: str, max_new_tokens: int) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_new_tokens
    )
    return response.choices[0].message.content

# Wrap in our backend
backend = APIChatBackend(
    tokenizer=tokenizer,
    send_callable=call_openai,
    name="openai-gpt4"
)

# Use with finite memory
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="semantic",  # Great for diverse topics
    max_tokens=4096,
    window_size=1024
)

# Your API calls now use optimized, compressed prompts
result = llm.chat("Explain quantum computing")
```

## 📚 Memory Policies

Choose the right policy for your use case:

### 1. **Sliding Window** (`sliding`)
- **How it works**: Simple FIFO - oldest tokens evicted first
- **Best for**: Short conversations, speed-critical applications
- **Pros**: Fast, predictable, low overhead
- **Cons**: May lose important early context

```python
llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
```

### 2. **Importance-Based** (`importance`)
- **How it works**: Uses model attention scores to identify important tokens
- **Best for**: Technical discussions, reasoning tasks, coding sessions
- **Pros**: Preserves critical information, attention-aware
- **Cons**: Requires local model access for attention scores

```python
llm = CompleteFiniteMemoryLLM(backend, memory_policy="importance")
```

### 3. **Semantic Clustering** (`semantic`)
- **How it works**: Embeds text spans, clusters by meaning, keeps representatives
- **Best for**: Multi-topic conversations, knowledge-intensive chats
- **Pros**: Topic-aware, handles diverse subjects well
- **Cons**: Requires sentence-transformers, slightly slower

```python
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="semantic",
    semantic_clusters=4  # Number of semantic clusters
)
```

### 4. **Rolling Summary** (`rolling_summary`)
- **How it works**: Periodically summarizes old context into compact summaries
- **Best for**: Long conversations, storytelling, roleplay
- **Pros**: Maintains long-term coherence, good compression
- **Cons**: May lose fine details in summaries

```python
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="rolling_summary",
    summary_interval=256  # Summarize every N tokens
)
```

## 🎨 Advanced Features

### 🎯 API-Safe Importance Probes (v2.2+)

Use importance-based eviction even with hosted APIs (OpenAI, Anthropic) where attention scores aren't available:

```python
# Importance policy now works with API backends!
from transformers import AutoTokenizer
from finite_memory_llm import CompleteFiniteMemoryLLM, APIChatBackend

tokenizer = AutoTokenizer.from_pretrained("gpt2")

def call_api(prompt: str, max_tokens: int) -> str:
    # Your API call here
    return "response"

backend = APIChatBackend(tokenizer, call_api, name="openai-gpt4")

# Importance policy uses logit probes automatically
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="importance",  # Now works with APIs!
    max_tokens=4096
)
```

**How it works:**
- Samples spans from context
- Masks each span and measures impact on next-token probability
- Higher impact = more important = kept longer
- Bounded probes (default 8) for controlled latency

### 📊 Accuracy Evaluation (v2.2+)

Measure how well your policy preserves information:

```bash
# Run the accuracy harness
python benchmarks/accuracy_harness.py
```

**Output:**
```
Policy          Accuracy    Early    Mid      Late     Compression
-----------------------------------------------------------------
sliding         45.0%       20.0%    40.0%    75.0%    2.15x
importance      65.0%       50.0%    60.0%    85.0%    1.95x
rolling_summary 55.0%       30.0%    55.0%    80.0%    3.20x
```

**Benefits:**
- Systematic evaluation of policy trade-offs
- Measure recall by position (early/mid/late facts)
- Optimize for your accuracy requirements
- Compare compression vs information retention

### ⏱️ Latency Budgeting (v2.1+)

Control policy execution time with automatic fallback to ensure consistent response times:

```python
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="semantic",  # Can be slow for large contexts
    max_policy_ms=50.0,        # Maximum 50ms for policy execution
    max_tokens=2048
)

# If semantic policy exceeds 50ms, automatically falls back to sliding
result = llm.chat("Long message...")

# Check if fallback occurred
print(f"Policy latency: {result['stats'].policy_latency_ms:.1f}ms")
print(f"Fallback count: {result['stats'].fallback_count}")
print(f"Total policy calls: {result['stats'].total_policy_calls}")
```

**Benefits:**
- 🎯 **Predictable latency**: Never let policy overhead ruin user experience
- 🔄 **Automatic fallback**: Gracefully degrades to sliding window when budget exceeded
- 📊 **Telemetry**: Track policy performance and fallback frequency
- ⚡ **Production-ready**: Essential for real-time applications

**Recommended budgets:**
- `10ms` - Ultra-low latency (real-time chat)
- `50ms` - Standard web applications
- `200ms` - Batch processing with quality focus
- `None` - No limit (benchmark/development)

### Checkpointing - Save & Resume Conversations

```python
# Save conversation state
llm.save_checkpoint("conversation_2024.json")

# Later... load and continue
llm.load_checkpoint("conversation_2024.json")
result = llm.chat("What were we discussing?")
```

### View Current Context

```python
# See what's in memory
context = llm.get_context_window()
print(f"Current context: {len(context)} characters")
```

### Access Statistics

```python
result = llm.chat("Hello")
stats = result["stats"]

print(f"Tokens seen: {stats.tokens_seen}")
print(f"Tokens retained: {stats.tokens_retained}")
print(f"Compression ratio: {stats.compression_ratio:.2f}x")
print(f"Evictions: {stats.evictions}")
print(f"Policy latency: {stats.policy_latency_ms:.1f}ms")
print(f"Anchor cache hits: {stats.anchor_cache_hits}")
```

## 🏗️ Architecture

```
┌─────────────┐
│ User Input  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Tokenize                │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Memory Policy           │
│ ┌─────────────────────┐ │
│ │ • Sliding           │ │
│ │ • Importance        │ │
│ │ • Semantic          │ │
│ │ • Rolling Summary   │ │
│ └─────────────────────┘ │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Context Builder         │
│ • Keep recent window    │
│ • Preserve anchors      │
│ • Trim to max_tokens    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ LLM Generation          │
│ (Local or API)          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Response + Stats        │
└─────────────────────────┘
```

## 📊 Performance Comparison

| Policy | Throughput | Memory Usage | Compression | Best Use Case |
|--------|------------|--------------|-------------|---------------|
| Sliding | ⚡⚡⚡ High | 💾 Low | 🔄 Medium | Quick chats |
| Importance | ⚡⚡ Medium | 💾💾 Medium | 🔄🔄 High | Technical work |
| Semantic | ⚡ Lower | 💾💾💾 Higher | 🔄🔄🔄 Very High | Multi-topic |
| Rolling Summary | ⚡⚡ Medium | 💾💾 Medium | 🔄🔄🔄 Very High | Long stories |

## 🛠️ Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# This includes: pytest, ruff, black, mypy
```

### Common Commands

```bash
make help          # Show all commands
make test          # Run tests
make test-cov      # Run tests with coverage
make lint          # Check code quality
make format        # Auto-format code
make type-check    # Verify type hints
make all-checks    # Run everything
```

### Running Examples

```bash
python examples/basic_chat.py              # Simple demo
python examples/policy_comparison.py       # Compare policies
python examples/checkpoint_demo.py         # Save/load demo
python examples/hosted_api_example.py      # API wrapper example
```

### Running Benchmarks

```bash
python benchmarks/benchmark_policies.py --policies sliding importance
```

## 🧪 Testing

```bash
# Run all tests
make test

# With coverage report
make test-cov

# Specific test file
pytest tests/test_finite_memory.py -v

# Specific test
pytest tests/test_finite_memory.py::TestMemoryPolicies::test_sliding_policy -v
```

## 📖 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get up and running in 5 minutes
- **[Upgrade to v2.0](UPGRADE_TO_V2.md)** - Migration guide from v1.0
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Changelog](CHANGELOG.md)** - Version history
- **[Modernization Report](MODERNIZATION_REPORT.md)** - Technical details

## 🔬 How It Works

### Context Distillation

Instead of sending the full conversation history on every turn:

```
❌ Without Finite Memory:
Turn 1: "Hello"                    → 1 token
Turn 2: "Hello" + "How are you?"   → 5 tokens  
Turn 3: Previous + "Tell me..."    → 20 tokens
Turn 4: Previous + ...             → 100 tokens
...exponential growth...

✅ With Finite Memory:
Turn 1: "Hello"                    → 1 token
Turn 2: [compressed] + new         → 5 tokens
Turn 3: [compressed] + new         → 8 tokens  
Turn 4: [compressed] + new         → 10 tokens
...stays bounded...
```

### Intelligent Eviction

The system uses sophisticated algorithms to decide what to keep:

1. **Recency**: Recent context always preserved
2. **Importance**: High-attention tokens retained (local models)
3. **Semantic**: Meaning-based clustering and compression
4. **Summarization**: Old context compressed into summaries

### Deterministic Context Builder

All policies feed into a deterministic context builder that:
- Preserves the most recent window
- Keeps sentence boundary "anchors" for coherence
- Ensures the final context fits within `max_tokens`

## 🎯 Use Cases

### 1. **Customer Support Chatbots**
```python
llm = CompleteFiniteMemoryLLM(backend, memory_policy="importance", max_tokens=2048)
# Keeps important customer details while discarding pleasantries
```

### 2. **Code Review Assistant**
```python
llm = CompleteFiniteMemoryLLM(backend, memory_policy="semantic", max_tokens=4096)
# Clusters code by functionality, maintains technical context
```

### 3. **Long-form Content Creation**
```python
llm = CompleteFiniteMemoryLLM(backend, memory_policy="rolling_summary", max_tokens=2048)
# Summarizes previous chapters while writing new content
```

### 4. **Multi-topic Research**
```python
llm = CompleteFiniteMemoryLLM(backend, memory_policy="semantic", semantic_clusters=8)
# Handles switching between different research topics
```

## 🔧 Configuration

### Full Configuration Options

```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,                    # Required: HuggingFaceBackend or APIChatBackend
    max_tokens=512,                     # Maximum tokens to keep in memory
    memory_policy="sliding",            # Policy: sliding, importance, semantic, rolling_summary
    window_size=128,                    # Recent window to always preserve
    semantic_clusters=4,                # (semantic only) Number of clusters
    summary_interval=256,               # (rolling_summary only) Tokens before summarizing
    embedding_model=None,               # (semantic only) Custom embedding model
    device="cpu"                        # Device for computation
)
```

## 📈 Metrics & Monitoring

Every chat response includes comprehensive statistics:

```python
result = llm.chat("message")

# Access metrics
print(f"Response: {result['response']}")
print(f"Tokens used in generation: {result['tokens_used']}")
print(f"Current context length: {result['context_length']}")
print(f"Memory policy: {result['memory_policy']}")

# Detailed stats
stats = result['stats']
print(f"Total tokens seen: {stats.tokens_seen}")
print(f"Tokens retained in memory: {stats.tokens_retained}")
print(f"Compression ratio: {stats.compression_ratio:.2f}x")
print(f"Total evictions: {stats.evictions}")
print(f"Summaries created: {stats.summaries_created}")
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run quality checks: `make all-checks`
5. Commit: `git commit -m 'feat: add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📝 Citation

If you use Finite Memory AI in your research or project, please cite:

```bibtex
@software{finite_memory_ai_2025,
  author = {Block, Dawson},
  title = {Finite Memory AI: Context Distillation for Large Language Models},
  year = {2025},
  url = {https://github.com/dawsonblock/Finite_Memory_AI}
}
```

## 🛡️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [PyTorch](https://pytorch.org/) - Deep learning framework
- [Transformers](https://huggingface.co/transformers/) - HuggingFace transformers
- [Sentence Transformers](https://www.sbert.net/) - Semantic embeddings
- [scikit-learn](https://scikit-learn.org/) - Machine learning utilities

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/dawsonblock/Finite_Memory_AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dawsonblock/Finite_Memory_AI/discussions)
- **Email**: Contact via GitHub profile

## 🗺️ Roadmap

- [x] Core finite memory implementation
- [x] Multiple eviction policies
- [x] Checkpoint/restore functionality
- [x] Hosted API support
- [x] Comprehensive testing
- [x] Modern Python 3.10+ with type hints
- [ ] KV-cache optimization for local models
- [ ] Hybrid memory policies
- [ ] Vector database integration
- [ ] Multi-session memory persistence
- [ ] Web UI for interactive demos
- [ ] Performance profiling tools

## ⭐ Star History

If you find this project useful, please consider giving it a star!

---

**Made with ❤️ by Dawson Block**

*Finite Memory AI - Making LLMs remember smartly, not infinitely.*
