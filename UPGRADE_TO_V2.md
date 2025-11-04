# Upgrade Guide: v1.0 → v2.0

## Overview

Version 2.0 modernizes the package for Python 3.10+ with improved type hints, modern packaging, and better tooling.

## Breaking Changes

### 1. Python Version Requirement

**Old (v1.0):** Python 3.7+
**New (v2.0):** Python 3.10+

**Action Required:**
```bash
python --version  # Must show 3.10 or higher
```

### 2. Type Hints Syntax

Modern union syntax is now used throughout:

**Old:**
```python
from typing import Optional, Union, List, Dict

def method(arg: Optional[str]) -> Union[List[int], Dict[str, str]]:
    ...
```

**New:**
```python
def method(arg: str | None) -> list[int] | dict[str, str]:
    ...
```

**Impact:** If you're importing types from the package for type checking, update your code to use modern syntax.

### 3. Packaging

**Old:** Configured via `setup.py` only
**New:** Configured via `pyproject.toml` (PEP 518, PEP 621)

**Action Required:**
```bash
# Old install
pip install -e .

# New install (same command, but now reads pyproject.toml)
pip install -e .

# New: Install with dev dependencies
pip install -e ".[dev]"
```

### 4. Dependencies Updated

Minimum versions increased for better performance and security:

| Dependency           | v1.0         | v2.0         |
|---------------------|--------------|--------------|
| Python              | >=3.7        | >=3.10       |
| torch               | >=1.9.0      | >=2.0.0      |
| transformers        | >=4.20.0     | >=4.35.0     |
| sentence-transformers| >=2.0.0     | >=2.2.0      |
| scikit-learn        | >=0.24.0     | >=1.3.0      |
| numpy               | >=1.19.0     | >=1.24.0     |

**Action Required:**
```bash
# Update dependencies
pip install --upgrade -r requirements.txt
```

## New Features

### 1. Modern Dev Tools

V2.0 includes modern development tools configured out of the box:

- **Ruff**: Fast Python linter (replaces flake8)
- **Black**: Code formatter
- **MyPy**: Static type checker
- **Pytest**: Testing with coverage

**Usage:**
```bash
make format      # Format code
make lint        # Check code quality
make type-check  # Verify type hints
make test        # Run tests
make all-checks  # Run everything
```

### 2. Makefile Commands

New `Makefile` for common tasks:

```bash
make help        # Show all commands
make install     # Install package
make install-dev # Install with dev tools
make test-cov    # Run tests with coverage
make clean       # Remove build artifacts
```

### 3. Type Hints Marker

Package now includes `py.typed` marker for full type hint support:

```python
# Your IDE will now get type hints from finite_memory_llm
from finite_memory_llm import CompleteFiniteMemoryLLM
llm: CompleteFiniteMemoryLLM  # Type checking works!
```

### 4. Better Documentation

All docstrings updated with:
- Clear parameter descriptions
- Return type documentation
- Usage examples

## Migration Steps

### Step 1: Check Python Version

```bash
python --version
```

If < 3.10, upgrade Python first.

### Step 2: Backup Current Environment

```bash
pip freeze > old_requirements.txt
```

### Step 3: Upgrade Package

```bash
cd finite-memory-llm
git pull  # or download v2.0
pip install -e ".[dev]"
```

### Step 4: Update Your Code (if needed)

Most code will work without changes. If you were importing types:

**Before:**
```python
from typing import Optional
from finite_memory_llm import CompleteFiniteMemoryLLM

def my_function(llm: Optional[CompleteFiniteMemoryLLM]):
    ...
```

**After:**
```python
from finite_memory_llm import CompleteFiniteMemoryLLM

def my_function(llm: CompleteFiniteMemoryLLM | None):
    ...
```

### Step 5: Run Tests

```bash
make test
```

## Compatibility Notes

### Fully Backward Compatible

These features work exactly the same:

- ✅ All memory policies (sliding, importance, semantic, rolling_summary)
- ✅ HuggingFaceBackend and APIChatBackend
- ✅ Checkpointing (save/load format unchanged)
- ✅ Chat interface and API
- ✅ Configuration options

### Your Existing Code Should Work

If you're using the package like this:

```python
from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend

backend = HuggingFaceBackend("gpt2")
llm = CompleteFiniteMemoryLLM(backend, memory_policy="sliding", max_tokens=512)
result = llm.chat("Hello")
```

**It will continue to work without any changes!**

## Benefits of Upgrading

1. **Better Performance**: Modern Python 3.10+ optimizations
2. **Improved Type Safety**: Better IDE autocomplete and error detection
3. **Modern Tooling**: Ruff, Black, MyPy configured and ready
4. **Active Development**: v2.0 is the maintained version
5. **Better Dependencies**: Updated to latest stable versions
6. **Cleaner Code**: Modern Python idioms throughout

## Troubleshooting

### "SyntaxError: invalid syntax"

You're using Python < 3.10. Upgrade Python:
```bash
# macOS (homebrew)
brew install python@3.10

# Ubuntu/Debian
sudo apt install python3.10

# Or use pyenv
pyenv install 3.10.0
pyenv local 3.10.0
```

### Import errors after upgrade

Reinstall the package:
```bash
pip uninstall finite-memory-llm
pip install -e ".[dev]"
```

### Type checking errors

If using mypy, update your `mypy.ini` or `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.10"
```

## Questions?

Open an issue on GitHub with:
- Your Python version (`python --version`)
- Error message (if any)
- What you're trying to do

## Summary

**Most users can upgrade by simply:**

1. Ensuring Python 3.10+
2. Running `pip install -e ".[dev]"`
3. Continuing to use the package as before

The API is 100% backward compatible - only internal implementation uses modern features.

