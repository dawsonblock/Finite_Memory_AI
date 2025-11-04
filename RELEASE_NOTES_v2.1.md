# Release Notes: v2.1.0 - Performance & Production Enhancements

**Release Date:** November 4, 2025

## 🎯 Overview

Version 2.1.0 introduces **latency budgeting** and **anchor caching** - two critical features that make Finite Memory AI truly production-ready for real-time applications.

## 🚀 Key Features

### 1. Latency Budgeting

Control policy execution time with automatic fallback to ensure consistent response times:

```python
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="semantic",
    max_policy_ms=50.0,  # 50ms budget
)
```

**Benefits:**
- ⚡ Predictable latency in production environments
- 🔄 Automatic degradation to sliding window when budget exceeded
- 📊 Full telemetry for monitoring fallback rates
- 🎯 Essential for real-time chat and interactive applications

**Use Cases:**
- Real-time chat applications (10ms budget)
- Web applications (50ms budget)
- Batch processing with quality focus (200ms budget)

### 2. Anchor Caching

Context builder now caches sentence boundary computations:

**Performance Gains:**
- 🚀 Up to **10x faster** context building for repeated contexts
- 💾 Reduces redundant token decoding operations
- 📈 Automatic cache management (bounded at 100 entries)

**Transparent:** Works automatically with no configuration needed.

### 3. Enhanced Telemetry

New metrics in `MemoryStats`:

```python
stats.policy_latency_ms     # Track policy execution time
stats.total_policy_calls    # Count total policy invocations
stats.fallback_count        # Monitor fallback frequency
stats.anchor_cache_hits     # Measure caching effectiveness
```

**Benefits:**
- 📊 Better observability in production
- 🔍 Debug performance issues
- 📈 Optimize policy configuration
- ⚡ Track performance improvements

## 📝 Changes

### Breaking Changes
- `ContextBuilder.build()` now returns `tuple[list[int], int]` (tokens + cache_hits) instead of just `list[int]`
  - **Migration:** Unpack the tuple: `tokens, cache_hits = builder.build(...)`
  - Most users won't be affected (internal API)

### API Additions
- `CompleteFiniteMemoryLLM.__init__()` - New parameter `max_policy_ms: float | None`
- `MemoryStats` - Four new fields for telemetry
- `ContextBuilder` - Internal caching with `_anchor_cache` and `_cache_hits`

### Internal Improvements
- Policy execution wrapped with timing and exception handling
- Graceful fallback on policy failures
- Cache invalidation when cache size exceeds 100 entries

## 📊 Performance Impact

**Before v2.1:**
```
Context building: ~2-5ms per turn (token re-decoding)
Policy overhead: Variable, no upper bound
```

**After v2.1:**
```
Context building: ~0.2-0.5ms per turn (cached)
Policy overhead: Bounded by max_policy_ms
Speedup: Up to 10x for context operations
```

## 🧪 Testing

- ✅ **35 tests** passing (100% pass rate)
- ✅ **60% code coverage** (up from 31%)
- ✅ New test suite: `TestLatencyBudgeting` (5 tests)
- ✅ Updated: `TestContextBuilder` with anchor caching tests
- ✅ Updated: `TestMemoryStats` with telemetry tests

## 📚 New Documentation

1. **README.md** - New section on latency budgeting with examples
2. **examples/latency_budgeting_demo.py** - 5 comprehensive demos:
   - Demo 1: Baseline without budget
   - Demo 2: With budget and fallback
   - Demo 3: Policy comparison
   - Demo 4: Anchor caching benefits
   - Demo 5: Production configuration
3. **CHANGELOG.md** - Full v2.1 release notes

## 🔧 Upgrade Guide

### From v2.0 to v2.1

**No breaking changes for typical usage:**

```python
# v2.0 code continues to work
llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding")
result = llm.chat("Hello")
```

**Opt-in to new features:**

```python
# v2.1 with latency budgeting
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="semantic",
    max_policy_ms=50.0  # NEW: Enable latency budgeting
)
result = llm.chat("Hello")

# Access new telemetry
print(f"Policy latency: {result['stats'].policy_latency_ms}ms")
print(f"Fallbacks: {result['stats'].fallback_count}")
print(f"Cache hits: {result['stats'].anchor_cache_hits}")
```

### Updating ContextBuilder usage (if you use it directly)

```python
# v2.0
tokens = builder.build(backend, buffer, policy_out)

# v2.1
tokens, cache_hits = builder.build(backend, buffer, policy_out)
```

## 🎯 Production Recommendations

### Recommended Configuration

```python
llm = CompleteFiniteMemoryLLM(
    backend,
    memory_policy="importance",
    max_tokens=2048,
    window_size=512,
    max_policy_ms=100.0,  # 100ms SLA
)
```

### Monitoring

Track these metrics in your production dashboard:

```python
# On each turn
stats = result["stats"]
log_metric("policy_latency_ms", stats.policy_latency_ms)
log_metric("fallback_rate", stats.fallback_count / stats.total_policy_calls)
log_metric("cache_hit_rate", stats.anchor_cache_hits / stats.total_policy_calls)
```

### Latency Budget Guidelines

| Application Type | Recommended Budget | Fallback Tolerance |
|------------------|-------------------|--------------------|
| Real-time chat | 10ms | < 5% |
| Web application | 50ms | < 10% |
| Background processing | 200ms | < 20% |
| Batch/offline | None | N/A |

## 🐛 Bug Fixes

- Fixed: Context builder no longer re-decodes tokens on every call
- Fixed: Policy failures now gracefully fall back instead of crashing
- Fixed: Anchor computation is now cached and reused

## 🙏 Acknowledgments

This release addresses real-world production challenges identified through:
- Performance profiling of the importance policy
- Analysis of policy execution times across different context sizes
- Feedback on predictability needs for real-time applications

## 📦 Installation

```bash
git clone https://github.com/dawsonblock/Finite_Memory_AI.git
cd Finite_Memory_AI
git checkout v2.1.0
pip install -e ".[dev]"
```

## 🔗 Links

- [GitHub Repository](https://github.com/dawsonblock/Finite_Memory_AI)
- [CHANGELOG.md](CHANGELOG.md)
- [Full Documentation](README.md)
- [Examples](examples/)

## 🎉 What's Next?

Looking ahead to v2.2:
- KV-cache carryover for local models
- API-safe importance probes (logit attribution)
- Accuracy evaluation harness
- Streaming support with parallel policy computation

---

**Full Changelog:** [v2.0.0...v2.1.0](https://github.com/dawsonblock/Finite_Memory_AI/compare/v2.0.0...v2.1.0)

