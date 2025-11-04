#!/bin/bash
# Quick Build Script - Fast development cycle
# Optimized for speed, runs only essential checks

set -e

echo "🚀 Quick Build Starting..."
echo ""

# 1. Lint (fast fail)
echo "📝 Step 1/3: Linting (fast fail)..."
ruff check finite_memory_llm/ --select F,E || {
    echo "❌ Linting failed!"
    exit 1
}
echo "✅ Linting passed"
echo ""

# 2. Fast tests (core only)
echo "🧪 Step 2/3: Running fast tests (core only)..."
pytest tests/test_finite_memory.py -v -x -q --tb=line || {
    echo "❌ Tests failed!"
    exit 1
}
echo "✅ Tests passed"
echo ""

# 3. Build package
echo "📦 Step 3/3: Building package..."
python3 -m build --wheel -q
echo "✅ Package built"
echo ""

echo "🎉 Quick build complete!"
echo "📦 Package: dist/*.whl"
echo "⏱️  Total time: ~30 seconds"
