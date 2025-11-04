# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

