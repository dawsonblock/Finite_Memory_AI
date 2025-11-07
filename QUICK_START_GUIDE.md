# 🚀 Quick Start Guide - Finite Memory AI

**Get started with Finite Memory AI in 5 minutes!**

---

## 📦 **Installation**

### **Step 1: Clone the Repository**
```bash
git clone https://github.com/dawsonblock/Finite_Memory_AI.git
cd Finite_Memory_AI
```

### **Step 2: Install Dependencies**
```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### **Step 3: Verify Installation**
```bash
python -c "import finite_memory_llm; print('✓ Installation successful!')"
```

---

## 🎯 **Basic Usage**

### **Example 1: Local Model (HuggingFace)**

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

# Create a backend with a local model
backend = HuggingFaceBackend("gpt2", device="cpu")

# Create the LLM with finite memory (512 tokens max)
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="sliding",  # Simple sliding window
    max_tokens=512
)

# Start chatting!
response = llm.chat("Hello! What can you help me with?")
print(response)

response = llm.chat("Tell me about Python programming.")
print(response)

# The LLM automatically manages context to stay within 512 tokens!
```

### **Example 2: OpenAI API**

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, OpenAIBackend

# Create OpenAI backend
backend = OpenAIBackend(
    model="gpt-3.5-turbo",
    api_key="your-api-key-here"  # Or set OPENAI_API_KEY env var
)

# Create LLM with semantic memory policy
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",  # Intelligent clustering
    max_tokens=2048
)

# Chat naturally - context is managed automatically
response = llm.chat("What's the weather like?")
print(response)

response = llm.chat("Should I bring an umbrella?")
print(response)
```

### **Example 3: Anthropic Claude**

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, AnthropicBackend

# Create Anthropic backend
backend = AnthropicBackend(
    model="claude-3-sonnet-20240229",
    api_key="your-api-key-here"  # Or set ANTHROPIC_API_KEY env var
)

# Create LLM with rolling summary
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="rolling_summary",  # Compresses old context
    max_tokens=4096
)

# Long conversations are automatically summarized
for i in range(20):
    response = llm.chat(f"Tell me fact #{i+1} about space.")
    print(f"Fact {i+1}: {response}")
```

---

## 🎨 **Memory Policies**

Choose the right policy for your use case:

### **1. Sliding Window** (Simple & Fast)
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="sliding",
    max_tokens=512
)
```
- **Best for**: Simple conversations, chat bots
- **How it works**: Keeps most recent messages, drops oldest
- **Speed**: ⚡ Fastest

### **2. Importance-Based** (Smart Retention)
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="importance",
    max_tokens=1024
)
```
- **Best for**: Conversations with key information
- **How it works**: Keeps high-attention tokens, drops low-value ones
- **Speed**: ⚡⚡ Fast

### **3. Semantic** (Intelligent Clustering)
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",
    max_tokens=2048
)
```
- **Best for**: Multi-topic conversations
- **How it works**: Clusters similar content, keeps representatives
- **Speed**: ⚡⚡ Fast (now 40-60% faster with optimizations!)

### **4. Rolling Summary** (Long Conversations)
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="rolling_summary",
    max_tokens=4096
)
```
- **Best for**: Very long conversations, narratives
- **How it works**: Summarizes old context automatically
- **Speed**: ⚡ Moderate (requires summarization)

### **5. Hybrid** (Best of All)
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="hybrid",
    max_tokens=2048
)
```
- **Best for**: Complex, varied conversations
- **How it works**: Combines multiple strategies
- **Speed**: ⚡⚡ Fast

---

## 🔧 **Advanced Features**

### **Save & Restore Conversations**

```python
# Save conversation state
checkpoint = llm.save_checkpoint()

# Later... restore it
llm.restore_checkpoint(checkpoint)

# Continue where you left off!
response = llm.chat("What were we talking about?")
```

### **Get Memory Statistics**

```python
# Check current memory usage
stats = llm.stats

print(f"Tokens used: {stats['total_tokens']}/{llm.max_tokens}")
print(f"Messages: {stats['num_messages']}")
print(f"Evictions: {stats.get('evictions', 0)}")
```

### **Reset Conversation**

```python
# Start fresh
llm.reset()

# New conversation with clean slate
response = llm.chat("Hello again!")
```

### **Custom Configuration**

```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",
    max_tokens=2048,
    
    # Advanced options
    enable_telemetry=True,      # Track metrics
    latency_budget_ms=5000,     # Max 5s per turn
    summary_qa_gate=True,       # Verify summaries
    embedding_cache_size=1000   # Cache embeddings
)
```

---

## 📊 **Monitoring & Debugging**

### **Enable Telemetry**

```python
from finite_memory_llm import CompleteFiniteMemoryLLM
from finite_memory_llm.telemetry import MetricsCollector

# Create metrics collector
metrics = MetricsCollector()

# Create LLM with telemetry
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",
    max_tokens=2048,
    enable_telemetry=True
)

# After some conversations...
summary = metrics.get_summary()
print(f"Average latency: {summary['policy_latency_p50_ms']:.2f}ms")
print(f"Cache hit rate: {summary.get('cache_hit_rate', 0):.1%}")
```

### **Export Metrics (Prometheus)**

```python
# Get Prometheus-formatted metrics
prometheus_text = metrics.export_prometheus()
print(prometheus_text)

# Or save to file
with open("metrics.txt", "w") as f:
    f.write(prometheus_text)
```

### **Dump Conversation Turns**

```python
# Save conversation history for debugging
llm.dump_turn("conversation_log.json")
```

---

## 🎓 **Common Use Cases**

### **Use Case 1: Customer Support Bot**

```python
# Long conversations with context management
llm = CompleteFiniteMemoryLLM(
    backend=OpenAIBackend("gpt-3.5-turbo"),
    memory_policy="hybrid",
    max_tokens=2048
)

# Customer asks multiple questions
llm.chat("I need help with my order #12345")
llm.chat("It hasn't arrived yet")
llm.chat("I ordered it 2 weeks ago")
response = llm.chat("Can you check the status?")
# LLM remembers order number and timeline!
```

### **Use Case 2: Code Assistant**

```python
# Technical conversations with important details
llm = CompleteFiniteMemoryLLM(
    backend=AnthropicBackend("claude-3-sonnet-20240229"),
    memory_policy="importance",
    max_tokens=4096
)

llm.chat("I'm building a Python web app with Flask")
llm.chat("I need to add user authentication")
llm.chat("And connect to a PostgreSQL database")
response = llm.chat("Show me the code structure")
# Keeps important technical details!
```

### **Use Case 3: Story Generation**

```python
# Long narratives with summaries
llm = CompleteFiniteMemoryLLM(
    backend=HuggingFaceBackend("gpt2-large"),
    memory_policy="rolling_summary",
    max_tokens=1024
)

# Generate a long story
for chapter in range(10):
    response = llm.chat(f"Continue the story. Chapter {chapter+1}:")
    print(f"\n=== Chapter {chapter+1} ===\n{response}")
# Old chapters are summarized automatically!
```

---

## ⚡ **Performance Tips**

### **1. Choose the Right Policy**
- **Short chats**: Use `sliding` (fastest)
- **Important info**: Use `importance` or `semantic`
- **Long conversations**: Use `rolling_summary`

### **2. Optimize Token Limits**
```python
# Smaller = faster, but less context
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="sliding",
    max_tokens=512  # Start small, increase if needed
)
```

### **3. Enable Caching**
```python
# Cache embeddings for semantic policy
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",
    max_tokens=2048,
    embedding_cache_size=1000  # Cache 1000 embeddings
)
```

### **4. Use Local Models for Speed**
```python
# Local models = no API latency
backend = HuggingFaceBackend("gpt2", device="cuda")  # GPU if available
llm = CompleteFiniteMemoryLLM(backend=backend, max_tokens=512)
```

---

## 🐛 **Troubleshooting**

### **Problem: Import errors**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

### **Problem: Out of memory**
```python
# Solution: Reduce max_tokens or use simpler policy
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="sliding",  # Simpler = less memory
    max_tokens=256  # Smaller limit
)
```

### **Problem: Slow responses**
```python
# Solution: Use faster policy or enable caching
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="sliding",  # Fastest policy
    max_tokens=512,
    embedding_cache_size=1000  # Enable caching
)
```

### **Problem: API key errors**
```bash
# Solution: Set environment variables
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

---

## 📚 **Next Steps**

### **Learn More**:
- 📖 Read the [README.md](README.md) for full feature list
- 🔧 Check [examples/](examples/) for more code samples
- 📊 See [PHASE_2_COMPLETE.md](PHASE_2_COMPLETE.md) for performance details
- 🎯 Review [TIER1_UPGRADE_GUIDE.md](TIER1_UPGRADE_GUIDE.md) for advanced features

### **Try Examples**:
```bash
# Run example scripts
python examples/basic_usage.py
python examples/semantic_policy_demo.py
python examples/checkpoint_demo.py
```

### **Run Tests**:
```bash
# Verify everything works
pytest tests/ -v -k "not slow"
```

---

## 💡 **Key Takeaways**

✅ **Easy to use**: Just 3 lines to get started  
✅ **Flexible**: Multiple backends (local & API)  
✅ **Smart**: 5 memory policies for different use cases  
✅ **Fast**: 45-95% faster with optimizations  
✅ **Production-ready**: 132 tests, 43% coverage  

---

## 🎉 **You're Ready!**

Start building with Finite Memory AI:

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

backend = HuggingFaceBackend("gpt2")
llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=512)

response = llm.chat("Hello! Let's build something amazing!")
print(response)
```

**Happy coding!** 🚀
