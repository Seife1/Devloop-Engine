# Contributing to LearnLoop

Thank you for your interest in contributing to LearnLoop! LearnLoop is an open-source, local-first Model Context Protocol (MCP) server engine designed to bridge the gap between what AI coding agents build and what developers can understand, defend, and retain.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free experience for everyone. Please be respectful and constructive in all issues, pull requests, and discussions.

---

## Getting Started

### Prerequisites
- **Python**: Version 3.11 or higher
- **Package Manager**: [`uv`](https://astral.sh/uv) (recommended) or `pip` / `venv`
- **Git**: Configured with your name and email

### Fork and Clone
```bash
git clone https://github.com/Seife1/Devloop-Engine.git
cd Devloop-Engine
```

### Development Environment Setup

#### Using `uv` (Recommended - 10x faster):
```bash
# Create and activate virtual environment
uv venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install package in editable mode with development dependencies
uv pip install -e ".[dev,http]"
```

#### Using standard `pip`:
```bash
python -m venv .venv
# On Linux/macOS: source .venv/bin/activate
# On Windows: .venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e ".[dev,http]"
```

---

## Project Architecture & Structure

```text
├── src/learnloop/           # Main package source
│   ├── capture/             # Git hook capture, techscan, complexity analysis
│   ├── dashboard/           # Local mission control server & Next.js static assets
│   ├── domain/              # Core domain logic (SM-2, staleness, models)
│   ├── mcp/                 # MCP server tool definitions & protocol adapters
│   ├── persistence/         # SQLite schema & forward migrations
│   ├── services/            # Business services (intent, review, knowledge, tour)
│   ├── taxonomy/            # Built-in seed taxonomy (skills.yaml)
│   ├── cli.py               # CLI entrypoint (learnloop init, doctor, dashboard, etc.)
│   ├── integrator.py        # Universal IDE detection & MCP configuration
│   └── server.py            # FastMCP server construction
├── tests/                   # Comprehensive test suite
│   ├── unit/                # Unit tests for domain, capture, and services
│   ├── integration/         # Multi-component integration tests
│   ├── properties/          # Hypothesis property-based tests
│   └── e2e/                 # Full protocol end-to-end tests
├── website/                 # Public Next.js documentation & marketing web portal
├── Dockerfile               # Production container image
├── pyproject.toml           # Hatchling build specification & dependencies
└── CHANGELOG.md             # Formal release history
```

---

## Development Workflow

### Running Tests
We maintain strict test discipline across unit, integration, and property-based test suites:

```bash
# Run all unit tests
pytest tests/unit -v

# Run the complete test suite
pytest -v

# Run property-based tests with Hypothesis
pytest tests/properties -v
```

### Code Style & Quality Checks
Before submitting code, ensure all formatters and linters pass:

```bash
# Lint code with Ruff
ruff check src tests

# Format code with Ruff
ruff format src tests

# Type check strictly with Mypy
mypy src/learnloop/domain src/learnloop/services
```

---

## Git Commit Guidelines

We enforce the [Conventional Commits](https://www.conventionalcommits.org/) specification for all git commits:

```text
<type>(<scope>): <short imperative description>

[optional body]

[optional footer(s)]
```

### Allowed Types
- `feat`: A new user-facing feature or capability
- `fix`: A bug fix
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `docs`: Documentation-only changes
- `perf`: A code change that improves performance
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Maintenance tasks (tooling, gitignore, release tags)

**Examples:**
- `feat(mcp): add support for streaming tools/call events`
- `fix(installer): handle Linux ARM64 fallback gracefully`
- `docs(readme): add troubleshooting section for Claude Desktop`

---

## Submitting Pull Requests

1. **Create a branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Make your changes**: Ensure documentation and tests are updated.
3. **Verify tests pass**: Run `pytest` and `ruff check`.
4. **Commit with Conventional Commits**.
5. **Push and open a Pull Request**:
   - Fill out the PR template completely.
   - Reference any relevant issues (e.g. `Fixes #123`).
   - Keep pull requests focused on a single logical change.

---

## Questions & Discussions
Have questions or ideas? Open an issue or join the discussion in the GitHub repository. We look forward to building with you!
