"""Finite Memory LLM - Production-ready memory management for language models.

Modern Python 3.10+ implementation with:
- Advanced type hints (PEP 604 union syntax)
- Finite memory with multiple eviction policies
- Context distillation for efficient prompting
- Support for both local and hosted language models

Quick start:
    >>> from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend
    >>> backend = HuggingFaceBackend("gpt2")
    >>> llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
    >>> result = llm.chat("Hello!")
"""

from __future__ import annotations

from .core import (
    APIChatBackend,
    CompleteFiniteMemoryLLM,
    ContextBuilder,
    HuggingFaceBackend,
    LLMBackend,
    MemoryStats,
    run_comprehensive_tests,
)

__version__ = "2.2.0"
__all__ = [
    "APIChatBackend",
    "CompleteFiniteMemoryLLM",
    "ContextBuilder",
    "HuggingFaceBackend",
    "LLMBackend",
    "MemoryStats",
    "run_comprehensive_tests",
]

