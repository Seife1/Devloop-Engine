# LearnLoop MCP Architecture

## Package Structure

LearnLoop is organized as a Python package with clear separation of concerns:

```
src/learnloop/
├── __init__.py              # Package version
├── __main__.py              # CLI entry point
├── cli.py                   # Command-line interface
├── config.py                # Runtime settings (database path, etc.)
├── gui.py                   # Native Microsoft Edge WebView2 desktop window
├── logging.py               # Logging infrastructure
├── server.py                # MCP server builder and tool registration
│
├── domain/                  # Core domain models and business logic
│   ├── models.py            # Data models with validation (Task 2 ✓)
│   ├── project_context.py   # Project context management
│   ├── learning_event.py    # Learning event detection
│   ├── scheduling.py        # SM-2 spaced repetition
│   ├── staleness.py         # File staleness detection
│   ├── depth.py             # Explanation depth analysis
│   ├── mastery.py           # Mastery score calculation
│   ├── teaching.py          # Quiz generation
│   ├── clock.py             # Time utilities
│   ├── errors.py            # Domain-specific errors
│   └── ...
│
├── persistence/             # Data persistence layer
│   ├── db.py                # Synchronous SQLite interface (legacy)
│   ├── async_db.py          # Async SQLite interface (Task 4 ✓)
│   ├── db_resilience.py     # Error handling and fallback (Task 4 ✓)
│   └── migrations/          # Database schema migrations
│
├── mcp/                     # MCP protocol integration
│   ├── config.py            # MCP server configuration schema (Task 1 ✓)
│   ├── schemas.py           # Tool input/output schemas
│   ├── prompts.py           # MCP prompts registration
│   └── tools/               # MCP tool implementations
│       ├── capture.py       # Intent tracking and queue processing
│       ├── knowledge.py     # Knowledge item management
│       ├── review.py        # Spaced repetition reviews
│       ├── facts.py         # Fact management
│       ├── technologies.py  # Technology detection
│       ├── profile.py       # User profile management
│       └── ...
│
├── services/                # Application services
│   ├── auto_tracker.py      # Automatic learning event detection
│   ├── git_integration.py   # Git hook management
│   ├── reconciliation.py    # Intent-commit matching
│   └── ...
│
├── capture/                 # Legacy capture infrastructure
│   ├── queue.py             # Queue processing
│   ├── techscan.py          # Technology detection
│   ├── skill_mapper.py      # Skill identification
│   └── redaction.py         # Secret redaction
│
└── dashboard/               # Optional web dashboard
    └── ...
```

## Core Components (from Design)

### 1. MCP Server Core
- **Location**: `server.py`, `mcp/`
- **Purpose**: MCP protocol compliance, tool registration, context detection
- **Status**: Partial (existing structure, needs enhancement for Tasks 5+)

### 2. Data Models
- **Location**: `domain/models.py`
- **Purpose**: Core data structures with validation
- **Status**: ✓ Complete (Task 2)
- **Models**: ProjectContext, IntentRecord, ExposureRecord, KnowledgeItem, ReviewSchedule

### 3. Database Layer
- **Location**: `persistence/async_db.py`, `persistence/db_resilience.py`
- **Purpose**: Async SQLite operations with retry and fallback
- **Status**: ✓ Complete (Task 4)
- **Features**: Connection pooling, retry logic, in-memory fallback, corruption detection

### 4. MCP Configuration
- **Location**: `mcp/config.py`
- **Purpose**: Configuration schema for MCP server settings
- **Status**: ✓ Complete (Task 1)
- **Features**: Environment variable loading, validation, performance tuning

### 5. Auto-Tracker Service
- **Location**: `services/auto_tracker.py` (to be implemented)
- **Purpose**: Automatic learning event detection from conversations
- **Status**: Not started (Task 6)

### 6. Git Integration Service
- **Location**: `services/git_integration.py` (to be implemented)
- **Purpose**: Git hook management and commit reconciliation
- **Status**: Not started (Task 8)

### 7. Progressive Enhancement Manager
- **Location**: `services/progressive_enhancement.py` (to be implemented)
- **Purpose**: Feature gating based on readiness level
- **Status**: Not started (Task 15)

## Configuration

### Runtime Settings (`config.py`)
- Database path (user data directory per Requirement 27.1)
- Intent abandonment threshold (14 days)
- Queue processing limits

### MCP Server Settings (`mcp/config.py`)
- Transport configuration (stdio by default)
- Feature flags for progressive enhancement
- Performance constraints (Requirement 25)
- Reconciliation parameters (Requirements 7, 36)
- Security settings (Requirement 28)
- Resilience settings (Requirement 24)
- Storage settings (Requirement 27)

## Dependencies

Core dependencies (from `pyproject.toml`):
- `mcp>=1.2,<2`: MCP protocol server (v1.x pinned per ADR-0002)
- `platformdirs>=4`: Cross-platform data directories (Requirement 26.1)
- `pyyaml>=6`: YAML configuration parsing
- `aiosqlite>=0.20`: Async SQLite interface (Requirement 27.1)

Development dependencies:
- `pytest>=8`: Testing framework
- `pytest-asyncio>=0.23`: Async test support
- `ruff>=0.5`: Linting and formatting
- `mypy>=1.10`: Static type checking
- `types-PyYAML`: Type stubs for PyYAML

## Cross-Platform Support (Requirement 26)

LearnLoop is designed to work consistently across Windows, macOS, and Linux:

1. **Data Directories**: Uses `platformdirs` to resolve OS-appropriate user data locations
2. **Path Handling**: Uses `Path` objects throughout for platform-agnostic path operations
3. **Git Hooks**: Detects shell environment (bash, zsh, PowerShell) and generates compatible scripts
4. **Filesystem Differences**: Handles both case-sensitive and case-insensitive filesystems

## Task Completion Status

### ✓ Completed Tasks

**Task 1: Project Structure and Core Infrastructure**
- ✓ Package structure: `src/learnloop/` (already existed)
- ✓ Data models: `domain/models.py` (Task 2 - completed)
- ✓ Database layer: `persistence/async_db.py`, `persistence/db_resilience.py` (Task 4 - completed)
- ✓ Dependencies: `pyproject.toml` verified and up-to-date
- ✓ MCP configuration: `mcp/config.py` created with full schema

**Task 2: Core Data Models** (completed in prior work)
- ✓ ProjectContext with validation
- ✓ LearningEvent with EventType and EventSource
- ✓ IntentRecord with IntentStatus
- ✓ ExposureRecord with commit SHA validation
- ✓ KnowledgeItem with DepthBand
- ✓ ReviewSchedule with SM-2 constraints

**Task 4: Database Layer** (completed in prior work)
- ✓ Database schema and migrations
- ✓ AsyncDatabase class with connection pooling
- ✓ CRUD operations for all models
- ✓ Error handling with retry logic
- ✓ Resilience features (in-memory fallback, corruption detection)

### Next Tasks

**Task 5: MCP Server Core** (Requirements 1.1, 1.9, 2.1-2.5, 25.1)
- Implement context detection algorithm
- Auto-bootstrap for new projects
- Welcome message generation

**Task 6: Auto-Tracker Service** (Requirements 3.1-3.9, 18.1-18.9)
- Conversation analysis engine
- Complexity score calculation
- Skill detection from code

**Task 8: Git Integration** (Requirements 5.1-5.9, 6.1-6.5, 7.1-7.10)
- Git hook installation
- Commit queue processing
- Intent-commit reconciliation

## Requirements Coverage

This architecture addresses requirements across multiple categories:

- **Req 1**: Auto project detection ✓ (structure ready, implementation pending)
- **Req 23**: Data validation ✓ (models complete)
- **Req 24**: Error recovery ✓ (resilience layer complete)
- **Req 25**: Performance constraints ✓ (configuration defined)
- **Req 26**: Cross-platform ✓ (platformdirs, Path usage)
- **Req 27**: Database storage ✓ (async layer complete, user data directory)

## Testing Strategy

Unit tests verify:
- Data model validation rules
- Configuration schema validation
- Database operations (CRUD, transactions)
- Error handling and retry logic

Property-based tests (planned):
- SM-2 parameter constraints (P7)
- Complexity score bounds (P5)
- Exposure verification (P1)
- Review schedule validity (P3)
