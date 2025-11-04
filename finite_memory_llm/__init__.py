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

# Optional imports with graceful degradation
try:
    from .async_core import (
        AsyncAPIChatBackend,
        AsyncCompleteFiniteMemoryLLM,
        AsyncHuggingFaceBackend,
        AsyncLLMBackend,
    )
    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    AsyncCompleteFiniteMemoryLLM = None
    AsyncHuggingFaceBackend = None
    AsyncAPIChatBackend = None
    AsyncLLMBackend = None

try:
    from .multilingual import (
        LanguageDetector,
        LanguageInfo,
        MultilingualMemoryPolicy,
        MultilingualTokenizer,
        TranslationBridge,
    )
    _MULTILINGUAL_AVAILABLE = True
except ImportError:
    _MULTILINGUAL_AVAILABLE = False
    LanguageDetector = None
    LanguageInfo = None
    MultilingualTokenizer = None
    MultilingualMemoryPolicy = None
    TranslationBridge = None

try:
    from .backends import (
        AI21Backend,
        AnthropicBackend,
        CohereBackend,
        GoogleBackend,
        HuggingFaceInferenceBackend,
        ReplicateBackend,
        TogetherBackend,
    )
    _BACKENDS_AVAILABLE = True
except ImportError:
    _BACKENDS_AVAILABLE = False
    CohereBackend = None
    AI21Backend = None
    AnthropicBackend = None
    GoogleBackend = None
    HuggingFaceInferenceBackend = None
    TogetherBackend = None
    ReplicateBackend = None

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

