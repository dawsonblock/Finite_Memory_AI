"""Finite Memory LLM - Production-ready memory management for language models.

Modern Python 3.10+ implementation with:
- Advanced type hints (PEP 604 union syntax)
- Finite memory with multiple eviction policies
- Context distillation for efficient prompting
- Support for both local and hosted language models
- Async/await support for non-blocking operations
- Multi-language support with adaptive policies
- 7+ additional API backends

Quick start:
    >>> from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend
    >>> backend = HuggingFaceBackend("gpt2")
    >>> llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
    >>> result = llm.chat("Hello!")
"""

# Core imports (always available)
from .core import (
    APIChatBackend,
    CompleteFiniteMemoryLLM,
    ContextBuilder,
    HuggingFaceBackend,
    LLMBackend,
    MemoryStats,
    PrometheusHook,
    TelemetryHook,
    run_comprehensive_tests,
)

# Lazy loading for optional modules to speed up import time
_ASYNC_AVAILABLE = False
_MULTILINGUAL_AVAILABLE = False
_BACKENDS_AVAILABLE = False

# Placeholders for lazy-loaded modules
AsyncCompleteFiniteMemoryLLM = None
AsyncHuggingFaceBackend = None
AsyncAPIChatBackend = None
AsyncLLMBackend = None
LanguageDetector = None
LanguageInfo = None
MultilingualTokenizer = None
MultilingualMemoryPolicy = None
TranslationBridge = None
CohereBackend = None
AI21Backend = None
AnthropicBackend = None
GoogleBackend = None
HuggingFaceInferenceBackend = None
TogetherBackend = None
ReplicateBackend = None


def __getattr__(name):
    """Lazy load optional modules on first access."""
    global _ASYNC_AVAILABLE, _MULTILINGUAL_AVAILABLE, _BACKENDS_AVAILABLE
    global AsyncCompleteFiniteMemoryLLM, AsyncHuggingFaceBackend
    global AsyncAPIChatBackend, AsyncLLMBackend
    global LanguageDetector, LanguageInfo, MultilingualTokenizer
    global MultilingualMemoryPolicy, TranslationBridge
    global CohereBackend, AI21Backend, AnthropicBackend, GoogleBackend
    global HuggingFaceInferenceBackend, TogetherBackend, ReplicateBackend

    # Async module
    if name in (
        "AsyncCompleteFiniteMemoryLLM",
        "AsyncHuggingFaceBackend",
        "AsyncAPIChatBackend",
        "AsyncLLMBackend",
    ):
        if not _ASYNC_AVAILABLE:
            try:
                from .async_core import (
                    AsyncCompleteFiniteMemoryLLM as _AsyncLLM,
                    AsyncHuggingFaceBackend as _AsyncHF,
                    AsyncAPIChatBackend as _AsyncAPI,
                    AsyncLLMBackend as _AsyncBackend,
                )

                AsyncCompleteFiniteMemoryLLM = _AsyncLLM
                AsyncHuggingFaceBackend = _AsyncHF
                AsyncAPIChatBackend = _AsyncAPI
                AsyncLLMBackend = _AsyncBackend
                _ASYNC_AVAILABLE = True
            except ImportError as e:
                raise ImportError(
                    f"Async support not available. Install required dependencies. {e}"
                ) from e

        return globals()[name]

    # Multilingual module
    if name in (
        "LanguageDetector",
        "LanguageInfo",
        "MultilingualTokenizer",
        "MultilingualMemoryPolicy",
        "TranslationBridge",
    ):
        if not _MULTILINGUAL_AVAILABLE:
            try:
                from .multilingual import (
                    LanguageDetector as _LD,
                    LanguageInfo as _LI,
                    MultilingualTokenizer as _MT,
                    MultilingualMemoryPolicy as _MMP,
                    TranslationBridge as _TB,
                )

                LanguageDetector = _LD
                LanguageInfo = _LI
                MultilingualTokenizer = _MT
                MultilingualMemoryPolicy = _MMP
                TranslationBridge = _TB
                _MULTILINGUAL_AVAILABLE = True
            except ImportError as e:
                raise ImportError(
                    f"Multilingual support not available. "
                    f"Install with: pip install langdetect. {e}"
                ) from e

        return globals()[name]

    # Backends module
    if name in (
        "CohereBackend",
        "AI21Backend",
        "AnthropicBackend",
        "GoogleBackend",
        "HuggingFaceInferenceBackend",
        "TogetherBackend",
        "ReplicateBackend",
    ):
        if not _BACKENDS_AVAILABLE:
            try:
                from .backends import (
                    CohereBackend as _CB,
                    AI21Backend as _A21,
                    AnthropicBackend as _AB,
                    GoogleBackend as _GB,
                    HuggingFaceInferenceBackend as _HFIB,
                    TogetherBackend as _TB,
                    ReplicateBackend as _RB,
                )

                CohereBackend = _CB
                AI21Backend = _A21
                AnthropicBackend = _AB
                GoogleBackend = _GB
                HuggingFaceInferenceBackend = _HFIB
                TogetherBackend = _TB
                ReplicateBackend = _RB
                _BACKENDS_AVAILABLE = True
            except ImportError as e:
                raise ImportError(
                    f"Backend '{name}' not available. "
                    f"Install with: pip install finite-memory-llm[backends]. {e}"
                ) from e

        return globals()[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__version__ = "2.4.0"
__all__ = [
    # Core
    "APIChatBackend",
    "CompleteFiniteMemoryLLM",
    "ContextBuilder",
    "HuggingFaceBackend",
    "LLMBackend",
    "MemoryStats",
    "PrometheusHook",
    "TelemetryHook",
    "run_comprehensive_tests",
    # Async (optional)
    "AsyncCompleteFiniteMemoryLLM",
    "AsyncHuggingFaceBackend",
    "AsyncAPIChatBackend",
    "AsyncLLMBackend",
    # Multilingual (optional)
    "LanguageDetector",
    "LanguageInfo",
    "MultilingualTokenizer",
    "MultilingualMemoryPolicy",
    "TranslationBridge",
    # Additional Backends (optional)
    "CohereBackend",
    "AI21Backend",
    "AnthropicBackend",
    "GoogleBackend",
    "HuggingFaceInferenceBackend",
    "TogetherBackend",
    "ReplicateBackend",
]

