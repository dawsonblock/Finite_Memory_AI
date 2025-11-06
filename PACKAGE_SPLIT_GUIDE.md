# 📦 Package Split Guide - Finite Memory AI v2.4.0

**Purpose**: Split monolithic package into lightweight components

---

## 🎯 Why Split?

### **Current Problem**:
- Everyone installs 1.2GB of dependencies
- API-only users pay 2.3s import cost for torch they don't need
- Package is bloated for simple use cases

### **Solution**:
Split into 4 packages with clear purposes

---

## 📦 Package Structure

### **1. finite-memory-llm-core** (LIGHTWEIGHT)
**Size**: ~5MB installed  
**Import time**: ~0.01s  
**Purpose**: Base interfaces, no heavy dependencies

**Dependencies**:
```
numpy>=1.24.0  # Only essential
```

**Use Case**: 
- Building custom backends
- API-only implementations
- Lightweight deployments

**Installation**:
```bash
pip install finite-memory-llm-core
```

**Example**:
```python
from finite_memory_llm.interfaces import LLMBackend, MemoryStats

class MyCustomBackend(LLMBackend):
    # Implement your backend
    pass
```

---

### **2. finite-memory-llm-local** (HEAVY)
**Size**: ~1.2GB installed  
**Import time**: ~2.3s (torch overhead)  
**Purpose**: Local model support with torch

**Dependencies**:
```
finite-memory-llm-core==2.4.0
torch>=2.0.0
transformers>=4.30.0
sentence-transformers>=2.2.0
scikit-learn>=1.3.0
```

**Use Case**:
- Running local HuggingFace models
- GPU acceleration
- Full feature set

**Installation**:
```bash
pip install finite-memory-llm-local
```

**Example**:
```python
from finite_memory_llm import CompleteFiniteMemoryLLM
from finite_memory_llm.backends_lazy import HuggingFaceBackendLazy

backend = HuggingFaceBackendLazy("gpt2")  # Torch loads here
llm = CompleteFiniteMemoryLLM(backend)
```

---

### **3. finite-memory-llm-api** (LIGHT)
**Size**: ~10MB installed  
**Import time**: ~0.05s  
**Purpose**: API backends only (OpenAI, Anthropic, etc.)

**Dependencies**:
```
finite-memory-llm-core==2.4.0
requests>=2.31.0
aiohttp>=3.8.0  # For async
```

**Optional**:
```
cohere>=4.0.0      # pip install finite-memory-llm-api[cohere]
anthropic>=0.3.0   # pip install finite-memory-llm-api[anthropic]
openai>=1.0.0      # pip install finite-memory-llm-api[openai]
```

**Use Case**:
- API-only deployments
- Serverless functions
- Lightweight containers

**Installation**:
```bash
# Base
pip install finite-memory-llm-api

# With specific backends
pip install finite-memory-llm-api[openai,anthropic]

# With all backends
pip install finite-memory-llm-api[all]
```

**Example**:
```python
from finite_memory_llm import CompleteFiniteMemoryLLM
from finite_memory_llm.backends import OpenAIBackend

backend = OpenAIBackend(api_key="...")
llm = CompleteFiniteMemoryLLM(backend)
```

---

### **4. finite-memory-llm** (META PACKAGE)
**Size**: Depends on choice  
**Purpose**: Convenience meta-package

**Default**: Installs `finite-memory-llm-local` (full features)

**Installation**:
```bash
# Default: full local support
pip install finite-memory-llm

# Core only
pip install finite-memory-llm[core-only]

# API only
pip install finite-memory-llm[api-only]

# Everything
pip install finite-memory-llm[all]
```

---

## 📊 Comparison Table

| Package | Size | Import Time | Use Case |
|---------|------|-------------|----------|
| **core** | 5MB | 0.01s | Custom backends, lightweight |
| **local** | 1.2GB | 2.3s | Local models, full features |
| **api** | 10MB | 0.05s | API backends only |
| **meta** | Varies | Varies | Convenience wrapper |

---

## 🚀 Migration Guide

### **Current Users (v2.3.0)**:
```bash
# Old way (installs everything)
pip install finite-memory-llm

# New way (same behavior)
pip install finite-memory-llm  # Still works, installs local
```

### **API-Only Users**:
```bash
# Old way (wasted 1.2GB)
pip install finite-memory-llm

# New way (saves 1.2GB!)
pip install finite-memory-llm-api[openai]
```

### **Custom Backend Developers**:
```bash
# Old way (needed full package)
pip install finite-memory-llm

# New way (lightweight)
pip install finite-memory-llm-core
```

---

## 💡 Benefits

### **For API-Only Users**:
- ✅ 95% smaller install (10MB vs 1.2GB)
- ✅ 99% faster imports (0.05s vs 2.3s)
- ✅ Lower memory usage (no torch)
- ✅ Faster container builds

### **For Local Model Users**:
- ✅ No change (same experience)
- ✅ Clear dependency management
- ✅ Optional features still available

### **For Developers**:
- ✅ Lightweight core for custom backends
- ✅ Clear separation of concerns
- ✅ Easier testing
- ✅ Better modularity

---

## 🔧 Implementation Status

### **Phase 1: Preparation** ✅
- [x] Create interfaces module
- [x] Create lazy-loading backends
- [x] Document split strategy

### **Phase 2: Package Creation** ⏳
- [ ] Create separate package directories
- [ ] Configure pyproject.toml for each
- [ ] Set up build scripts
- [ ] Test installations

### **Phase 3: Publishing** ⏳
- [ ] Publish core package
- [ ] Publish local package
- [ ] Publish api package
- [ ] Publish meta package

### **Phase 4: Migration** ⏳
- [ ] Update documentation
- [ ] Provide migration guide
- [ ] Deprecation warnings
- [ ] Support both versions

---

## 📝 Example Use Cases

### **Use Case 1: Serverless API Function**
```python
# Dockerfile
FROM python:3.10-slim
RUN pip install finite-memory-llm-api[openai]  # Only 10MB!

# main.py
from finite_memory_llm import CompleteFiniteMemoryLLM
from finite_memory_llm.backends import OpenAIBackend

backend = OpenAIBackend(api_key=os.environ["OPENAI_KEY"])
llm = CompleteFiniteMemoryLLM(backend)

def handler(event):
    return llm.chat(event["message"])
```

**Result**: 
- Container: 200MB (was 2GB)
- Cold start: 1s (was 5s)
- Memory: 100MB (was 600MB)

### **Use Case 2: Local GPU Inference**
```python
# Still works exactly the same
pip install finite-memory-llm-local

from finite_memory_llm import CompleteFiniteMemoryLLM
from finite_memory_llm.backends_lazy import HuggingFaceBackendLazy

backend = HuggingFaceBackendLazy("gpt2", device="cuda")
llm = CompleteFiniteMemoryLLM(backend)
```

### **Use Case 3: Custom Backend**
```python
pip install finite-memory-llm-core

from finite_memory_llm.interfaces import LLMBackend

class MyBackend(LLMBackend):
    def generate(self, input_ids, max_new_tokens, **kwargs):
        # Your implementation
        pass
```

---

## 🎯 Honest Impact

### **What This Fixes**:
✅ API-only users: 95% smaller, 99% faster imports  
✅ Clear dependency management  
✅ Better modularity  
✅ Faster container builds  

### **What This Doesn't Fix**:
⚠️ Local model users still have 2.3s import (torch overhead)  
⚠️ Requires package restructuring  
⚠️ Migration effort for existing users  

---

## 📈 Expected Results

| Metric | Before | After (API) | After (Local) |
|--------|--------|-------------|---------------|
| **Install Size** | 1.2GB | 10MB | 1.2GB |
| **Import Time** | 2.3s | 0.05s | 2.3s |
| **Memory Usage** | 600MB | 50MB | 600MB |
| **Container Size** | 2GB | 200MB | 2GB |

---

**Status**: 🟡 **DESIGNED, NOT YET IMPLEMENTED**  
**Effort**: Medium (requires package restructuring)  
**Impact**: High (95% smaller for API users)  
**Priority**: 2 (important but not critical)

🎯 **This is the RIGHT way to structure the package.**
