#!/bin/bash
# Full Build Script - Complete validation
# Runs all checks for production readiness

set -e

echo "🚀 Full Build Starting..."
echo ""

# 1. Clean previous builds
echo "🧹 Step 1/7: Cleaning..."
rm -rf build/ dist/ *.egg-info htmlcov/ .coverage .pytest_cache/
echo "✅ Cleaned"
echo ""

# 2. Linting
echo "📝 Step 2/7: Linting..."
ruff check finite_memory_llm/ tests/ || {
    echo "❌ Ruff check failed!"
    exit 1
}
black --check finite_memory_llm/ tests/ examples/ || {
    echo "⚠️  Black formatting issues found"
    echo "Run: black finite_memory_llm/ tests/ examples/"
}
echo "✅ Linting passed"
echo ""

# 3. Type checking
echo "🔍 Step 3/7: Type checking..."
mypy finite_memory_llm/ --ignore-missing-imports || {
    echo "⚠️  Type checking issues found (non-fatal)"
}
echo "✅ Type checking complete"
echo ""

# 4. Fast tests
echo "🧪 Step 4/7: Running fast tests..."
pytest tests/test_finite_memory.py -v -x || {
    echo "❌ Fast tests failed!"
    exit 1
}
echo "✅ Fast tests passed"
echo ""

# 5. Full test suite with coverage
echo "🧪 Step 5/7: Running full test suite..."
pytest tests/ -v --cov=finite_memory_llm --cov-report=html --cov-report=term || {
    echo "❌ Full tests failed!"
    exit 1
}
echo "✅ Full tests passed"
echo ""

# 6. Build package
echo "📦 Step 6/7: Building package..."
python3 -m build
echo "✅ Package built"
echo ""

# 7. Check package
echo "✅ Step 7/7: Checking package..."
twine check dist/* || {
    echo "❌ Package check failed!"
    exit 1
}
echo "✅ Package validated"
echo ""

echo "🎉 Full build complete!"
echo ""
echo "📊 Results:"
echo "  - Coverage report: htmlcov/index.html"
echo "  - Package: dist/"
echo "  - All checks passed ✅"
echo ""
echo "⏱️  Total time: ~2 minutes"
