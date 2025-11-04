# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-11-04

### Added
- **KV-cache tracking**: Monitor cache hit/miss rates in HuggingFaceBackend
  - New `get_cache_stats()` method returns cache metrics
  - Tracks opportunities for KV-cache carryover optimization
  - Foundation for full KV-cache reuse in future versions
- **API-safe importance probes**: Logit attribution for hosted APIs (v2.2+)
  - `_importance_via_logit_probes()` method measures token importance via impact on next-token probability
  - Automatic fallback when attention scores unavailable (API backends)
  - Bounded probe count (default 8) for controlled latency
  - Enables importance policy for OpenAI/Anthropic/etc.
- **Accuracy evaluation harness**: Systematic testing of memory vs accuracy trade-offs
  - New `benchmarks/accuracy_harness.py` with synthetic QA dataset
  - Plant facts at different positions (early/mid/late)
  - Measure recall accuracy by position and compression ratio
  - Compare policies on accuracy vs compression curves
  - 7 planted facts + filler conversations for realistic testing
- Enhanced `HuggingFaceBackend`:
  - New `enable_kv_cache` parameter (default True)
  - Cache hit/miss tracking for monitoring
  - Foundation for future full KV-cache reuse

### Changed
- Importance policy now uses logit probes as fallback when attention unavailable
- Updated `_evict_importance()` to try attention first, then logit probes
- Enhanced error handling in importance scoring

### Improved
- 📊 **Better API support**: Importance policy now works with hosted APIs
- 🎯 **Accuracy visibility**: Systematic evaluation of policy trade-offs
- 📈 **Monitoring**: KV-cache tracking for optimization opportunities
- 🧪 **Test coverage**: 63% (up from 60%), 41 tests passing

### Test Suite
- New `TestKVCacheTracking` class (2 tests)
- New `TestLogitProbes` class (2 tests)
- New `TestAccuracyHarness` class (2 tests)
- All 41 tests passing

### Future (v2.3+)
- Full KV-cache carryover with actual reuse (requires model.forward() integration)
- Streaming support with parallel policy computation (async/threading)
- Expanded accuracy harness with more diverse QA patterns

## [2.1.0] - 2025-11-04

### Added
- **Latency budgeting**: New `max_policy_ms` parameter for controlling policy execution time
  - Automatic fallback to sliding window when budget exceeded
  - Essential for production deployments with strict latency requirements
- **Anchor caching**: Context builder now caches sentence boundary computations
  - Reduces redundant token decoding operations
  - Up to 10x faster for repeated contexts
- **Performance telemetry**: Enhanced `MemoryStats` with timing information:
  - `policy_latency_ms` - Track policy execution time
  - `total_policy_calls` - Count total policy invocations
  - `fallback_count` - Monitor fallback frequency
  - `anchor_cache_hits` - Measure caching effectiveness
- New example: `examples/latency_budgeting_demo.py` with 5 comprehensive demos
- Documentation updates with latency budgeting guide and production configs

### Changed
- `ContextBuilder.build()` now returns tuple `(tokens, cache_hits)` instead of just tokens
- Policy execution wrapped with timing and exception handling
- Added `time` and `functools` imports to core module

### Improved
- 🚀 **Up to 10x faster** context building with anchor caching
- 🎯 **Predictable latency** with configurable budgets
- 📊 **Better observability** with comprehensive telemetry
- ⚡ **Production-ready** with automatic degradation under load

### Fixed
- Context builder no longer re-decodes tokens on every call (anchor caching)
- Policy failures now gracefully fall back instead of crashing

## [2.0.0] - 2025-11-03

### Added
- Modern Python 3.10+ type hints using PEP 604 union syntax (`X | Y`)
- Built-in generic types (`list[int]`, `dict[str, Any]`)
- `pyproject.toml` for modern packaging (PEP 518, PEP 621)
- `py.typed` marker for full IDE type hint support
- Ruff linter configuration (10-100x faster than flake8)
- Black code formatter configuration
- MyPy static type checker configuration
- Makefile with common development tasks
- `requirements-dev.txt` for development dependencies
- `.editorconfig` for consistent editor settings
- `.python-version` file for Python version specification
- Comprehensive documentation:
  - `UPGRADE_TO_V2.md` - Migration guide from v1.0
  - `MODERNIZATION_REPORT.md` - Complete modernization details
  - `CHANGELOG.md` - Version history
- Improved docstrings throughout codebase with parameter descriptions
- Future annotations import for deferred type evaluation

### Changed
- **BREAKING**: Minimum Python version increased from 3.7 to 3.10
- Updated dependencies to latest stable versions:
  - torch: 1.9.0 → 2.0.0
  - transformers: 4.20.0 → 4.35.0
  - sentence-transformers: 2.0.0 → 2.2.0
  - scikit-learn: 0.24.0 → 1.3.0
  - numpy: 1.19.0 → 1.24.0
- Simplified `setup.py` - now uses `pyproject.toml` as source of truth
- Updated all documentation for Python 3.10+
- Improved README with modern Python features list
- Updated QUICKSTART with Makefile commands

### Improved
- Better type safety with modern type hints
- Faster linting with Ruff
- Cleaner code syntax using modern Python features
- More comprehensive documentation
- Better IDE support with `py.typed` marker
- Automated development workflows with Makefile

### Maintained
- ✅ 100% backward compatible API
- ✅ All memory policies work identically
- ✅ Checkpoint format unchanged
- ✅ Configuration options unchanged
- ✅ All examples continue to work

## [1.0.0] - 2024

### Added
- Initial release
- Four memory policies: sliding, importance, semantic, rolling_summary
- HuggingFaceBackend for local models
- APIChatBackend for hosted APIs
- ContextBuilder for deterministic context selection
- Checkpointing (save/load conversation state)
- Comprehensive test suite
- Example scripts
- Benchmark tools
- Full documentation

[2.0.0]: https://github.com/yourusername/finite-memory-llm/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/yourusername/finite-memory-llm/releases/tag/v1.0.0

