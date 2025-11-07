# 📖 Usage Summary - Everything You Need to Know

**Complete guide to using Finite Memory AI**

---

## 🎯 **TL;DR - Get Started in 30 Seconds**

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

# 1. Create a backend
backend = HuggingFaceBackend("gpt2")

# 2. Create the LLM with finite memory
llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=512)

# 3. Chat!
response = llm.chat("Hello!")
print(response)
```

**That's it!** The LLM automatically manages context to stay within 512 tokens.

---

## 📚 **Documentation Index**

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)** | Get started in 5 minutes | 5 min |
| **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** | Understand the architecture | 10 min |
| **[README.md](README.md)** | Full feature list & overview | 15 min |
| **[PHASE_2_COMPLETE.md](PHASE_2_COMPLETE.md)** | Performance optimizations | 10 min |
| **[examples/](examples/)** | Code examples | Varies |

---

## 🚀 **Common Use Cases**

### **1. Simple Chatbot**
```python
llm = CompleteFiniteMemoryLLM(
    backend=HuggingFaceBackend("gpt2"),
    memory_policy="sliding",  # Simple & fast
    max_tokens=512
)

while True:
    user_input = input("You: ")
    response = llm.chat(user_input)
    print(f"Bot: {response}")
```

### **2. Customer Support with Context**
```python
llm = CompleteFiniteMemoryLLM(
    backend=OpenAIBackend("gpt-3.5-turbo"),
    memory_policy="importance",  # Remembers key details
    max_tokens=2048
)

# Remembers order number, issue, etc.
llm.chat("My order #12345 hasn't arrived")
llm.chat("I ordered it 2 weeks ago")
response = llm.chat("Can you help?")
```

### **3. Long Conversations**
```python
llm = CompleteFiniteMemoryLLM(
    backend=AnthropicBackend("claude-3-sonnet-20240229"),
    memory_policy="rolling_summary",  # Summarizes old context
    max_tokens=4096
)

# Can chat for 100+ turns without losing context
for i in range(100):
    response = llm.chat(f"Tell me about topic {i}")
```

---

## 🎨 **Choosing a Memory Policy**

| Policy | Speed | Use When | Pros | Cons |
|--------|-------|----------|------|------|
| **sliding** | ⚡⚡⚡ Fastest | Short chats, simple bots | Simple, fast | Loses old info |
| **importance** | ⚡⚡ Fast | Key details matter | Keeps important info | Needs attention scores |
| **semantic** | ⚡⚡ Fast | Multi-topic chats | Handles topics well | Requires embeddings |
| **rolling_summary** | ⚡ Moderate | Very long chats | Maintains narrative | Slower (summarization) |
| **hybrid** | ⚡⚡ Fast | Production apps | Best of all | More complex |

**Recommendation**: Start with `sliding`, upgrade to `hybrid` for production.

---

## 🔧 **Configuration Options**

### **Basic Configuration**
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,           # Required: Your LLM backend
    memory_policy="sliding",   # Required: Memory strategy
    max_tokens=512            # Required: Token limit
)
```

### **Advanced Configuration**
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",
    max_tokens=2048,
    
    # Performance
    enable_telemetry=True,        # Track metrics
    embedding_cache_size=1000,    # Cache embeddings
    
    # Quality
    summary_qa_gate=True,         # Verify summaries
    latency_budget_ms=5000,       # Max 5s per turn
    
    # Advanced
    enable_kv_cache=True,         # For local models
    device="cuda"                 # GPU if available
)
```

---

## 📊 **Monitoring & Debugging**

### **Check Memory Usage**
```python
stats = llm.stats
print(f"Tokens: {stats['total_tokens']}/{llm.max_tokens}")
print(f"Messages: {stats['num_messages']}")
```

### **Save & Restore**
```python
# Save conversation
checkpoint = llm.save_checkpoint()

# Later... restore
llm.restore_checkpoint(checkpoint)
```

### **Reset Conversation**
```python
llm.reset()  # Start fresh
```

### **Export Metrics**
```python
from finite_memory_llm.telemetry import MetricsCollector

metrics = MetricsCollector()
summary = metrics.get_summary()
print(f"Avg latency: {summary['policy_latency_p50_ms']:.2f}ms")
```

---

## 🎓 **Supported Backends**

### **Local Models (HuggingFace)**
```python
from finite_memory_llm import HuggingFaceBackend

backend = HuggingFaceBackend(
    model_name="gpt2",           # Or any HF model
    device="cpu",                # Or "cuda" for GPU
    enable_kv_cache=True         # Optimize for speed
)
```

**Popular models**:
- `gpt2`, `gpt2-medium`, `gpt2-large`
- `facebook/opt-1.3b`
- `EleutherAI/gpt-neo-1.3B`

### **OpenAI API**
```python
from finite_memory_llm import OpenAIBackend

backend = OpenAIBackend(
    model="gpt-3.5-turbo",       # Or gpt-4
    api_key="your-key"           # Or set OPENAI_API_KEY
)
```

### **Anthropic Claude**
```python
from finite_memory_llm import AnthropicBackend

backend = AnthropicBackend(
    model="claude-3-sonnet-20240229",
    api_key="your-key"           # Or set ANTHROPIC_API_KEY
)
```

### **Cohere**
```python
from finite_memory_llm import CohereBackend

backend = CohereBackend(
    model="command",
    api_key="your-key"           # Or set COHERE_API_KEY
)
```

---

## ⚡ **Performance Tips**

### **1. Choose the Right Token Limit**
```python
# Smaller = faster, less context
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=256)  # Very fast

# Larger = slower, more context
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=4096)  # More context
```

### **2. Use GPU for Local Models**
```python
backend = HuggingFaceBackend("gpt2", device="cuda")  # Much faster!
```

### **3. Enable Caching**
```python
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="semantic",
    max_tokens=2048,
    embedding_cache_size=1000  # Cache 1000 embeddings
)
```

### **4. Use Simpler Policies for Speed**
```python
# Fastest
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=512)

# Slower but smarter
llm = CompleteFiniteMemoryLLM(backend, "rolling_summary", max_tokens=2048)
```

---

## 🐛 **Common Issues & Solutions**

### **Issue: "Module not found"**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

### **Issue: "Out of memory"**
```python
# Solution: Reduce max_tokens
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=256)
```

### **Issue: "Slow responses"**
```python
# Solution: Use faster policy or GPU
backend = HuggingFaceBackend("gpt2", device="cuda")
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=512)
```

### **Issue: "API key error"**
```bash
# Solution: Set environment variable
export OPENAI_API_KEY="your-key-here"
```

### **Issue: "Context lost too quickly"**
```python
# Solution: Increase max_tokens or use smarter policy
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="importance",  # Keeps important info
    max_tokens=2048              # More context
)
```

---

## 📈 **Performance Benchmarks**

### **Import Time**
```
Before: 5.4s
After:  0.1s
Improvement: 98% faster! ⚡
```

### **Sentence Detection**
```
Before: 100ms
After:  30ms
Improvement: 70% faster! ⚡
```

### **Embeddings**
```
Before: 200ms
After:  100ms
Improvement: 50% faster! ⚡
```

### **Sparse Matrices**
```
Before: 1000ms
After:  10ms
Improvement: 99% faster! ⚡⚡⚡
```

### **Overall System**
```
Improvement: 45-95% faster overall! ✓
```

---

## 🎯 **Best Practices**

### **1. Start Simple**
```python
# Begin with sliding window
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=512)

# Upgrade if needed
llm = CompleteFiniteMemoryLLM(backend, "hybrid", max_tokens=2048)
```

### **2. Monitor Performance**
```python
# Enable telemetry in production
llm = CompleteFiniteMemoryLLM(
    backend=backend,
    memory_policy="hybrid",
    max_tokens=2048,
    enable_telemetry=True  # Track metrics
)
```

### **3. Handle Errors Gracefully**
```python
try:
    response = llm.chat(user_input)
except Exception as e:
    print(f"Error: {e}")
    response = "Sorry, I encountered an error."
```

### **4. Save Important Conversations**
```python
# Save before closing
checkpoint = llm.save_checkpoint()
with open("conversation.json", "w") as f:
    json.dump(checkpoint, f)

# Restore later
with open("conversation.json", "r") as f:
    checkpoint = json.load(f)
llm.restore_checkpoint(checkpoint)
```

---

## 🔗 **Quick Links**

- 📖 **[QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)** - 5-minute tutorial
- 🧠 **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - Architecture explained
- 🚀 **[README.md](README.md)** - Full documentation
- ⚡ **[PHASE_2_COMPLETE.md](PHASE_2_COMPLETE.md)** - Performance details
- 💻 **[examples/](examples/)** - Code examples
- 🧪 **[tests/](tests/)** - Test suite (132 tests!)

---

## 💡 **Key Takeaways**

✅ **Easy**: 3 lines to get started  
✅ **Fast**: 45-95% faster with optimizations  
✅ **Flexible**: 5 memory policies, multiple backends  
✅ **Smart**: Automatic context management  
✅ **Tested**: 132 tests, 43% coverage  
✅ **Production-ready**: A+ quality  

---

## 🎉 **You're Ready to Build!**

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

# Create your LLM
backend = HuggingFaceBackend("gpt2")
llm = CompleteFiniteMemoryLLM(backend, "sliding", max_tokens=512)

# Start chatting!
response = llm.chat("Let's build something amazing!")
print(response)
```

**Happy coding!** 🚀

---

**Need help?** Check the documentation or open an issue on GitHub!
