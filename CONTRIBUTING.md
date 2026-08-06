# Contributing to KifPilot AI Support Agent

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Ollama (for local LLM/embedding models)
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/ai-support-agent.git
   cd ai-support-agent
   ```

2. **Set up backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Set up frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Start development servers**
   ```bash
   # Terminal 1: Backend
   cd backend
   python -m app.main

   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

5. **Run tests**
   ```bash
   # Backend
   cd backend
   pytest tests/ -v

   # Frontend
   cd frontend
   npm test
   ```

## Development Workflow

### Branch Naming

- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `docs/<description>` - Documentation updates
- `refactor/<description>` - Code refactoring
- `test/<description>` - Test additions/improvements

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

Examples:
```
feat(auth): add OAuth2 support
fix(documents): resolve upload timeout for large files
docs(api): update authentication endpoints
test(retrieval): add hybrid search integration tests
```

### Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes with tests
3. Ensure all tests pass
4. Update documentation if needed
5. Submit PR to `develop` branch
6. Address review feedback
7. Squash and merge after approval

## Coding Standards

### Python (Backend)

- **Formatter**: Ruff (configured in `pyproject.toml`)
- **Type Checking**: MyPy (strict mode)
- **Linting**: Ruff with strict rules
- **Testing**: pytest with asyncio support

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy app/
```

### TypeScript (Frontend)

- **Formatter**: Prettier
- **Linting**: ESLint with TypeScript support
- **Type Checking**: tsc --noEmit

```bash
# Format
npm run format

# Lint
npm run lint

# Type check
npm run typecheck
```

### General Guidelines

1. **Write tests first** (TDD preferred)
2. **Keep functions small** and focused
3. **Use type hints** everywhere
4. **Document public APIs** with docstrings
5. **Handle errors explicitly** - no bare except
6. **Log structured data** for observability
7. **Never commit secrets** or credentials

## Testing Requirements

### Backend

- Unit tests for all new functions
- Integration tests for API endpoints
- Load tests for performance-critical paths
- Regression tests for bug fixes

```bash
# Run specific test categories
pytest tests/ -m "unit"           # Unit tests
pytest tests/ -m "integration"    # Integration tests
pytest tests/ -m "load"           # Load tests
pytest tests/ -m "regression"     # Regression tests
```

### Frontend

- Unit tests for components/hooks
- Integration tests for API calls
- E2E tests for critical user flows

```bash
# Run tests
npm test              # Unit tests
npm run test:e2e      # Playwright E2E tests
```

## Documentation

- Update relevant docs for any API changes
- Add docstrings for new public functions/classes
- Keep README.md current
- Document breaking changes in CHANGELOG.md

## Security

- Run security checks before committing
- Never log sensitive data
- Validate all inputs
- Use parameterized queries
- Report vulnerabilities via [SECURITY.md](SECURITY.md)

```bash
# Security scan
pip install bandit
bandit -r app/
```

## Performance

- Profile before optimizing
- Add benchmarks for critical paths
- Monitor memory usage
- Use connection pooling
- Cache appropriately

## Release Process

1. Version bump in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create release PR to `main`
4. Tag release after merge
5. CI/CD builds and publishes artifacts

## Getting Help

- Check existing [issues](https://github.com/kifpilot/ai-support-agent/issues)
- Read the [documentation](docs/)
- Ask in [discussions](https://github.com/kifpilot/ai-support-agent/discussions)
- Contact maintainers for urgent issues

## Recognition

Contributors will be recognized in:
- Release notes
- Contributors list
- Annual contributor highlights

Thank you for contributing! 🚀