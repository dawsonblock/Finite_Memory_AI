# Contributing to Finite Memory LLM

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Installation

1. **Fork and clone the repository**

```bash
git clone https://github.com/yourusername/finite-memory-llm.git
cd finite-memory-llm
```

2. **Install in development mode**

```bash
pip install -e ".[dev]"
```

This installs the package with all development dependencies: pytest, ruff, black, mypy, etc.

3. **Verify installation**

```bash
make help
```

## Code Style

We use modern Python 3.10+ features and enforce consistent code style.

### Type Hints

**Required:** All functions must have type hints using modern syntax:

```python
# Good - Modern Python 3.10+
def process(data: list[int], config: dict[str, Any] | None = None) -> str:
    """Process data with optional config."""
    ...

# Bad - Old syntax
def process(data: List[int], config: Optional[Dict[str, Any]] = None) -> str:
    ...
```

### Formatting

We use **Black** for code formatting:

```bash
make format        # Format all code
make format-check  # Check without changes
```

Configuration in `pyproject.toml`:
- Line length: 100
- Target: Python 3.10+

### Linting

We use **Ruff** for fast linting:

```bash
make lint          # Check code
make lint-fix      # Auto-fix issues
```

Ruff checks for:
- Code style (E, W)
- Unused imports (F)
- Import sorting (I)
- Naming conventions (N)
- Python upgrade suggestions (UP)
- Bug-prone patterns (B)

### Type Checking

We use **MyPy** for static type checking:

```bash
make type-check
```

All code should pass strict type checking.

## Testing

### Running Tests

```bash
# Quick test run
make test

# With coverage report
make test-cov

# Specific test file
pytest tests/test_finite_memory.py -v

# Specific test function
pytest tests/test_finite_memory.py::TestMemoryStats::test_initialization -v
```

### Writing Tests

1. **Location**: Place tests in `tests/` directory
2. **Naming**: Test files should start with `test_`
3. **Structure**: Use pytest fixtures and classes

Example:

```python
import pytest
from finite_memory_llm import CompleteFiniteMemoryLLM

class TestMyFeature:
    """Test suite for my feature."""
    
    def test_basic_functionality(self):
        """Test basic use case."""
        # Arrange
        llm = CompleteFiniteMemoryLLM(...)
        
        # Act
        result = llm.chat("test")
        
        # Assert
        assert "response" in result
```

### Coverage

We aim for >80% test coverage. Check coverage with:

```bash
make test-cov
open htmlcov/index.html  # View detailed report
```

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-description
```

Branch naming:
- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation
- `refactor/` for code improvements

### 2. Make Changes

- Write clean, well-documented code
- Add/update tests
- Update documentation if needed

### 3. Run Quality Checks

Before committing, run all checks:

```bash
make all-checks
```

This runs:
- Code formatting check (black)
- Linting (ruff)
- Type checking (mypy)
- Tests with coverage (pytest)

### 4. Commit

Write clear commit messages:

```bash
git add .
git commit -m "feat: add semantic memory optimization

- Improved clustering algorithm
- Added caching for embeddings
- Updated tests and docs"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Test updates
- `refactor:` - Code refactoring
- `perf:` - Performance improvement

### 5. Push and Create PR

```bash
git push origin feature/my-feature
```

Then create a Pull Request on GitHub:

1. **Title**: Clear, descriptive summary
2. **Description**: 
   - What changes were made
   - Why they were needed
   - Any breaking changes
3. **Checklist**:
   - [ ] Tests added/updated
   - [ ] Documentation updated
   - [ ] All checks passing
   - [ ] Type hints added

### 6. Review Process

- Maintainers will review your PR
- Address any feedback
- Once approved, it will be merged

## Reporting Issues

### Bug Reports

Include:
1. **Python version**: `python --version`
2. **Package version**: Check `__version__`
3. **Minimal reproduction**: Code that demonstrates the bug
4. **Expected vs actual behavior**
5. **Error messages**: Full stack traces

### Feature Requests

Include:
1. **Use case**: Why is this feature needed?
2. **Proposed API**: How should it work?
3. **Alternatives**: What other solutions exist?

## Development Workflow

### Daily Development

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes and test frequently
make test

# 4. Run checks before committing
make all-checks

# 5. Commit and push
git add .
git commit -m "feat: description"
git push origin feature/my-feature
```

### Code Organization

```
finite-memory-llm/
├── finite_memory_llm/     # Main package
│   ├── __init__.py        # Public API
│   └── core.py            # Core implementation
├── examples/              # Usage examples
├── tests/                 # Test suite
├── benchmarks/            # Performance benchmarks
├── docs/                  # Documentation (if added)
└── pyproject.toml         # Package configuration
```

### Adding New Features

1. **Discuss first**: Open an issue to discuss the feature
2. **Design**: Plan the API and implementation
3. **Implement**: Write code with tests and docs
4. **Review**: Submit PR for review
5. **Merge**: After approval and passing checks

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Security**: Email maintainers directly

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

Thank you for contributing! 🎉

