---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

A clear and concise description of what the bug is.

## To Reproduce

Steps to reproduce the behavior:

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

# Your code that reproduces the bug
backend = HuggingFaceBackend("gpt2")
llm = CompleteFiniteMemoryLLM(backend, ...)
# ...
```

## Expected Behavior

A clear description of what you expected to happen.

## Actual Behavior

What actually happened. Include error messages:

```
Traceback (most recent call last):
  ...
```

## Environment

- **OS**: [e.g., Ubuntu 22.04, macOS 13, Windows 11]
- **Python version**: [e.g., 3.10.5, 3.11.2, 3.12.0]
- **Package version**: [e.g., 2.0.0]
- **PyTorch version**: [e.g., 2.0.0]
- **Transformers version**: [e.g., 4.35.0]

```bash
python --version
pip show finite-memory-llm
pip show torch transformers
```

## Additional Context

Add any other context about the problem here, such as:
- Does it happen with specific models?
- Does it happen with specific memory policies?
- Any relevant logs or screenshots?

## Possible Solution

If you have ideas on how to fix this, please share them here.

