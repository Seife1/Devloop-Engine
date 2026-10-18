# Implementation Plan: MCP-Native LearnLoop Plugin Redesign

## Overview

Transform LearnLoop from a CLI-based learning companion into an MCP-native plugin with zero-friction setup and progressive enhancement. Implementation uses Python with async/await patterns for MCP protocol integration, SQLite for data persistence, and property-based testing for algorithmic correctness.

**Key Deliverables:**
- MCP server with automatic project detection
- Auto-tracking service for learning event detection
- Progressive enhancement system with readiness levels
- Git integration with non-invasive hooks
- Spaced repetition review engine with staleness detection

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Create new Python package structure: `src/learnloop_mcp/`
  - Define core data models in `models.py` using dataclasses
  - Set up async SQLite database layer with aiosqlite
  - Configure dependency management in `pyproject.toml`
  - Create configuration schema for MCP server settings
  - _Requirements: 26.1, 26.2, 27.1_

- [x] 2. Implement core data models with validation
  - [x] 2.1 Implement ProjectContext model
    - Define ProjectContext dataclass with validation
    - Add validators for readiness_level (1-4), repo_path existence
    - Implement serialization/deserialization methods
    - _Requirements: 1.1, 1.6, 23.1, 23.2_
  
  - [x] 2.2 Implement LearningEvent model
    - Define LearningEvent with EventType and EventSource enums
    - Add confidence score validation (0.0-1.0)
    - Implement timestamp validation (not future dates)
    - _Requirements: 3.7, 23.3_
  
  - [x] 2.3 Implement IntentRecord model
    - Define IntentRecord with IntentStatus enum
    - Add validation: matched status requires commit_sha
    - Validate closed_at timestamp when status != OPEN
    - _Requirements: 4.1, 4.2, 4.3, 23.4, 23.5_
  
  - [x] 2.4 Implement ExposureRecord model
    - Define ExposureRecord with commit_sha validation (40 hex chars)
    - Add explanation_depth validation when explanation_recorded
    - Validate verified_at timestamp not in future
    - _Requirements: 7.6, 23.6, 23.7_
  
  - [x] 2.5 Implement KnowledgeItem and ReviewSchedule models
    - Define KnowledgeItem with DepthBand enum
    - Add self_rating validation (1.0-5.0)
    - Define ReviewSchedule with SM-2 parameter validation
    - Validate easiness (1.3-2.5), interval (>0), repetitions (>=0)
    - _Requirements: 9.1, 9.2, 9.3, 15.2, 15.3, 23.8, 23.9, 23.10, 23.11_

- [x] 3. Checkpoint - Ensure all tests pass
  - Run unit tests for data models
  - Verify validation rules enforce constraints
  - Ensure serialization round-trips correctly

- [x] 4. Implement database layer with async operations
  - [x] 4.1 Create database schema and migrations
    - Write SQL schema for all tables
    - Implement migration system with version tracking
    - Create indexes for common queries (project_id, due_at, etc.)
    - _Requirements: 23.1-23.11, 27.1_
  
  - [x] 4.2 Implement async database operations
    - Create AsyncDatabase class with connection pooling
    - Implement CRUD operations for all models
    - Add query methods with proper parameter binding
    - Implement transaction support with context managers
    - _Requirements: 1.6, 27.2_
  
  - [x] 4.3 Implement database error handling and resilience
    - Add retry logic with exponential backoff for locked database
    - Implement fallback to in-memory database on connection failure
    - Add corruption detection with PRAGMA integrity_check
    - Queue write operations when using temporary database
    - _Requirements: 24.1, 24.2, 24.3, 24.4_

- [ ]* 4.4 Write unit tests for database operations
  - Test CRUD operations for all models
  - Test transaction rollback on errors
  - Test connection retry logic
  - _Requirements: 24.1, 24.2, 24.3_

- [x] 5. Implement MCP Server core with context detection
  - [-] 5.1 Create MCP server initialization
    - Implement LearnLoopMCPServer class
    - Add MCP protocol initialization handler
    - Configure async transport layer
    - Register standard MCP capabilities
    - _Requirements: 1.1, 1.9, 25.1_
  
  - [-] 5.2 Implement context detection algorithm
    - Create detect_context() method
    - Scan workspace for .learn/ directory
    - Detect git repository presence
    - Scan for technology configuration files
    - Calculate initial readiness level
    - _Requirements: 1.1, 1.7, 1.8, 19.1-19.7_
  
  - [-] 5.3 Implement auto-bootstrap for new projects
    - Create project record in database
    - Initialize .learn/ directory structure
    - Create .learn/queue/ directory
    - Write .learn/.gitignore file
    - Initialize concepts.md with template
    - Install git hook if repository detected
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 5.2, 5.3_
  
  - [-] 5.4 Implement welcome message generation
    - Generate welcome message for new users (<100 words)
    - Create quick start action suggestions
    - Format message for AI assistant display
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 5.5 Write property test for context detection idempotency
  - **Property P10 (partial): Session Continuity**
  - **Validates: Requirements 1.1, 1.6, 1.9**
  - Generate random workspace paths and project states
  - Verify detect_context() is deterministic for same input
  - Verify bootstrap creates consistent directory structure

- [x] 6. Implement Auto-Tracker service
  - [x] 6.1 Create conversation analysis engine
    - Implement analyze_conversation() method
    - Extract code blocks from assistant messages
    - Detect programming language from code blocks
    - Extract decision points from conversation
    - Calculate confidence scores for detected events
    - _Requirements: 3.1, 3.2, 3.7, 3.9_
  
  - [x] 6.2 Implement complexity score calculation
    - Create calculate_complexity_score() function
    - Calculate cyclomatic complexity
    - Calculate maximum nesting depth
    - Count unique identifiers
    - Normalize metrics and compute weighted average
    - _Requirements: 3.3, 18.1-18.9_
  
  - [x] 6.3 Implement skill detection from code
    - Create detect_skills_in_code() function
    - Pattern matching for common frameworks and libraries
    - AST-based analysis for language constructs
    - Return list of skill tags with confidence
    - _Requirements: 3.4_
  
  - [x] 6.4 Implement learning event storage
    - Filter events by confidence threshold (>0.7)
    - Store significant learning events in database
    - Deduplicate events based on content similarity
    - _Requirements: 3.8_

- [x]* 6.5 Write property test for complexity score bounds
  - **Property P5 (from testing strategy): Complexity Score Bounded**
  - **Validates: Requirements 18.7, 18.8**
  - Generate random code strings
  - Verify complexity score always between 0.0 and 1.0
  - Verify trivial code (<5 lines) scores below 0.2

- [ ]* 6.6 Write unit tests for Auto-Tracker
  - Test conversation analysis with sample messages
  - Test complexity calculation with known code examples
  - Test skill detection accuracy
  - _Requirements: 3.1-3.9, 18.1-18.9_

- [x] 7. Implement Intent tracking and recording
  - [x] 7.1 Create start_skill_session MCP tool
    - Implement tool handler for intent creation
    - Validate input parameters (intent, files, skills)
    - Create IntentRecord with OPEN status
    - Store session_id and timestamp
    - Return success response in under 50ms
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [x] 7.2 Implement intent query methods
    - Create fetch_open_intents() database query
    - Add filtering by project_id
    - Return intents ordered by created_at
    - _Requirements: 7.2_

- [ ]* 7.3 Write unit tests for intent tracking
  - Test intent creation with valid data
  - Test concurrent intent creation
  - Test intent query filtering
  - _Requirements: 4.1-4.6_

- [x] 8. Implement Git integration service
  - [x] 8.1 Create git hook installation logic
    - Implement install_hook() method
    - Detect existing post-commit hooks
    - Preserve non-LearnLoop hooks when appending
    - Update existing LearnLoop hooks in-place
    - Set executable permissions (chmod +x)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [x] 8.2 Generate post-commit hook script
    - Create Python script template for hook
    - Extract commit metadata (SHA, message, timestamp, files)
    - Write JSON to .learn/queue/ directory
    - Use commit SHA as filename for idempotency
    - Add error handling with exit code 0 guarantee
    - Optimize for <50ms execution time
    - _Requirements: 5.7, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 8.3 Implement commit queue processing
    - Create ingest_queue MCP tool
    - Read JSON files from .learn/queue/
    - Parse commit metadata with error handling
    - Create Queue_Entry records in database
    - Mark entries as processed after reconciliation
    - _Requirements: 7.1, 24.7_
  
  - [x] 8.4 Implement intent-commit reconciliation algorithm
    - Create reconcile_intents() method
    - Load unprocessed queue entries and open intents
    - Calculate match scores (70% file overlap, 30% time proximity)
    - Apply match threshold of 0.6
    - Create Exposure_Records for matched pairs
    - Mark unmatched commits as unexplained
    - Abandon intents older than 14 days
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 36.1-36.6_
  
  - [x] 8.5 Implement file overlap calculation
    - Create calculate_file_overlap() helper function
    - Count files in both intent and commit
    - Normalize by intent file list size
    - _Requirements: 36.1, 36.2_
  
  - [x] 8.6 Implement time decay calculation
    - Create calculate_time_decay() helper function
    - Use exponential decay with 24-hour half-life
    - Return score between 0.0 and 1.0
    - _Requirements: 36.3_

- [ ]* 8.7 Write property test for reconciliation idempotency
  - **Property P9: Queue Processing Idempotency**
  - **Validates: Requirements 7.10, 31.1, 31.2**
  - Generate random commit data
  - Process same commit multiple times
  - Verify identical results and no duplicate exposures

- [~]* 8.8 Write property test for file overlap symmetry
  - **Property P4 (from testing strategy): File Overlap Symmetry**
  - **Validates: Requirements 36.1, 36.2**
  - Generate random file lists
  - Verify calculate_file_overlap(A, B) == calculate_file_overlap(B, A)

- [ ]* 8.9 Write property test for exposure verification
  - **Property P1: Exposure Verification**
  - **Validates: Requirements 7.6, 7.7, 7.9, 23.4, 36.1, 36.4**
  - For all exposures with verified_at, verify matching intent and commit exist
  - Verify file overlap >= MATCH_THRESHOLD

- [ ]* 8.10 Write property test for intent-commit mutual exclusion
  - **Property P5: Intent-Commit Mutual Exclusion**
  - **Validates: Requirements 7.7, 23.4, 23.5, 31.2**
  - Verify each commit matches at most one intent
  - No duplicate matching across intents

- [x] 9. Checkpoint - Verify git integration works end-to-end
  - Test hook installation in sample repository
  - Make test commits and verify queue entries created
  - Run reconciliation and verify exposures created

- [x] 10. Implement explanation prompts and recording
  - [x] 10.1 Create explanation prompt generator
    - Implement generate_explanation_prompt() function
    - Extract code snippets from exposure files (max 50 lines)
    - Generate depth-appropriate questions (2-4 questions)
    - Tailor questions to skill complexity
    - Include self-rating encouragement (1-5 scale)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 10.2 Create record_explanation MCP tool
    - Implement tool handler for explanation recording
    - Validate self_rating between 1.0 and 5.0
    - Store explanation text with item reference
    - Calculate explanation depth score
    - Update Exposure_Record with depth and recorded flag
    - _Requirements: 10.1, 10.2, 10.4, 10.5, 10.6_
  
  - [x] 10.3 Implement explanation depth calculation
    - Analyze explanation text for technical terms
    - Count decision rationale statements
    - Detect alternative consideration
    - Calculate score between 0.0 and 1.0
    - _Requirements: 10.3, 10.4_
  
  - [x] 10.4 Implement explanation quality feedback
    - Detect low-quality explanations (<0.4 score)
    - Generate improvement suggestions
    - _Requirements: 10.7_

- [ ]* 10.5 Write property test for explanation depth bounds
  - **Property P6: Explanation Depth Bounds**
  - **Validates: Requirements 10.2, 10.4, 10.5, 23.6, 23.7**
  - For all exposures with explanation_recorded=true, verify depth in [0.0, 1.0]
  - Verify explanation text is non-empty

- [ ]* 10.6 Write unit tests for explanation system
  - Test prompt generation with various skill levels
  - Test depth calculation with sample explanations
  - Test quality feedback triggers
  - _Requirements: 8.1-8.8, 10.1-10.7_

- [x] 11. Implement knowledge item management
  - [x] 11.1 Create register_knowledge_item MCP tool
    - Implement tool handler for item registration
    - Validate unique key within project
    - Validate title (<100 chars) and summary (<500 chars)
    - Classify depth_band based on complexity
    - Store tracked files list
    - Schedule first review for 1 day later
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.8_
  
  - [x] 11.2 Implement concepts.md synchronization
    - Update concepts.md on item creation
    - Format entry with markdown headings
    - Include title, summary, tracked files, depth band
    - Create file if it doesn't exist
    - _Requirements: 9.6, 9.7, 22.1-22.7_
  
  - [x] 11.3 Implement depth band classification
    - Calculate complexity from tracked files
    - Classify as basic (<0.3), intermediate (0.3-0.6), advanced (>0.6)
    - Allow manual override
    - _Requirements: 9.5, 39.1-39.6_

- [ ]* 11.4 Write unit tests for knowledge item management
  - Test item creation with validation
  - Test concepts.md formatting
  - Test depth band classification
  - _Requirements: 9.1-9.8, 22.1-22.7, 39.1-39.6_

- [x] 12. Implement spaced repetition engine (SM-2)
  - [x] 12.1 Create SM-2 schedule update algorithm
    - Implement update_sm2_schedule_with_staleness() function
    - Apply staleness penalty (reduce quality by 1 if stale)
    - Calculate new interval based on quality (0-5)
    - Update easiness factor with SM-2 formula
    - Clamp easiness between 1.3 and 2.5
    - Reset on failure (quality < 3)
    - Calculate next due date
    - _Requirements: 15.1-15.12_
  
  - [x] 12.2 Create review_due MCP tool
    - Implement tool handler to fetch due reviews
    - Query items with due_at <= today
    - Exclude snoozed items
    - Order by due_at ascending
    - Accept limit parameter for batch size
    - Include item details, files, staleness info
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_
  
  - [x] 12.3 Create record_review MCP tool
    - Implement tool handler for review completion
    - Accept answer quality (0-5) and depth reached
    - Update ReviewSchedule with SM-2 algorithm
    - Update success_streak on success
    - Clear staleness flag after stale item review
    - Generate review summary with accuracy
    - _Requirements: 16.8, 16.9, 16.10_
  
  - [x] 12.4 Implement review snoozing
    - Add snooze_review MCP tool
    - Accept snooze duration in days
    - Set snoozed_until timestamp
    - Exclude from due queries until date passes
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

- [ ]* 12.5 Write property test for SM-2 parameter constraints
  - **Property P7: SM-2 Parameter Constraints**
  - **Validates: Requirements 15.2, 15.3, 15.4, 15.9, 15.10, 23.9, 23.10, 23.11**
  - Generate random initial schedules and quality scores
  - Verify easiness always in [1.3, 2.5]
  - Verify interval always >= 1
  - Verify repetitions always >= 0

- [ ]* 12.6 Write property test for review schedule validity
  - **Property P3: Review Schedule Validity**
  - **Validates: Requirements 15.2, 15.3, 15.4, 15.12, 23.10, 23.11**
  - For all schedules with repetitions > 0, verify last_reviewed_at exists
  - Verify due_at > last_reviewed_at
  - Verify interval >= 1

- [ ]* 12.7 Write unit tests for spaced repetition
  - Test SM-2 algorithm with known inputs
  - Test staleness penalty application
  - Test review fetching with various filters
  - Test snooze functionality
  - _Requirements: 15.1-15.12, 16.1-16.10, 17.1-17.4_

- [x] 13. Checkpoint - Verify spaced repetition works correctly
  - Create test knowledge items
  - Complete reviews with various quality scores
  - Verify intervals calculated correctly
  - Test staleness penalty application

- [x] 14. Implement staleness detection
  - [x] 14.1 Create staleness detection on commit
    - Hook into reconciliation process
    - Check if commit modifies tracked files
    - Query Knowledge_Items tracking those files
    - Set is_stale flag and stale_since timestamp
    - Record which commit caused staleness
    - _Requirements: 14.1, 14.2, 14.3, 14.5_
  
  - [x] 14.2 Implement semantic diff for staleness
    - Ignore whitespace-only changes
    - Ignore comment-only changes
    - Use AST comparison for code files
    - Calculate confidence score for staleness
    - _Requirements: 14.7_
  
  - [x] 14.3 Implement staleness clearing
    - Clear is_stale flag on review completion
    - Set stale_since to NULL
    - _Requirements: 14.6_

- [ ]* 14.4 Write property test for staleness consistency
  - **Property P4: Staleness Consistency**
  - **Validates: Requirements 14.1, 14.2, 14.3, 14.6, 23.8**
  - For all items with is_stale=true, verify commit exists
  - Verify commit timestamp > last_explained_at
  - Verify commit modifies tracked files

- [ ]* 14.5 Write unit tests for staleness detection
  - Test staleness on file modification
  - Test staleness ignores whitespace changes
  - Test staleness clearing on review
  - _Requirements: 14.1-14.7_

- [x] 15. Implement Progressive Enhancement Manager
  - [x] 15.1 Create readiness level calculation
    - Implement calculate_readiness_level() method
    - Count total and explained commits
    - Count knowledge items and completed reviews
    - Calculate average explanation quality
    - Calculate review accuracy percentage
    - Count active days
    - Apply level thresholds (1-4)
    - Cache calculated level in database
    - _Requirements: 11.1-11.11_
  
  - [x] 15.2 Implement feature gating system
    - Create get_available_tools() method
    - Map tools to required readiness levels
    - Level 1: auto-tracking, basic intent tools
    - Level 2: explanation prompts, self-rating
    - Level 3: spaced repetition reviews
    - Level 4: deep practice, advanced analytics
    - Return tools based on user level
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [x] 15.3 Implement level-up detection
    - Create check_level_up_eligibility() method
    - Compare current vs potential level
    - Return eligibility flag and new level
    - _Requirements: 12.6_
  
  - [x] 15.4 Create level-up celebration messages
    - Generate unlock prompts for each level
    - List newly unlocked features
    - Show progress toward next level
    - _Requirements: 12.6, 12.7, 12.8_

- [ ]* 15.5 Write property test for readiness monotonicity
  - **Property P2: Readiness Level Monotonicity**
  - **Validates: Requirements 11.7, 11.8, 11.9, 11.10, 23.1**
  - Generate sequence of learning actions
  - Verify level never decreases without explicit reset
  - Verify level progression is cumulative

- [ ]* 15.6 Write property test for progressive feature visibility
  - **Property P8: Progressive Feature Visibility**
  - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**
  - For all users and tools, verify can_access requires sufficient level
  - Verify tools are properly gated by level

- [ ]* 15.7 Write unit tests for progressive enhancement
  - Test readiness calculation with various metrics
  - Test feature gating at each level
  - Test level-up detection
  - _Requirements: 11.1-11.11, 12.1-12.8_

- [ ] 16. Implement session briefing system
  - [x] 16.1 Create session briefing generator
    - Implement get_session_briefing() method
    - Calculate days since last session
    - Count new commits since last session
    - Count unexplained commits
    - List stale knowledge items
    - Show current readiness level and progress
    - List items due for review today
    - Suggest next action based on priorities
    - _Requirements: 13.1-13.8_
  
  - [x] 16.2 Optimize briefing performance
    - Use efficient database queries with indexes
    - Cache frequently accessed metrics
    - Complete briefing generation in <100ms
    - _Requirements: 13.9, 25.6_

- [ ]* 16.3 Write unit tests for session briefing
  - Test briefing generation with sample data
  - Test performance with large datasets
  - Test priority suggestions
  - _Requirements: 13.1-13.9_

- [ ] 17. Implement unexplained commit tracking
  - [x] 17.1 Create unexplained commit recording
    - Store commits without matching intents
    - Record SHA, message, files, timestamp
    - _Requirements: 21.1, 21.2_
  
  - [x] 17.2 Implement unexplained commit prompts
    - Include count in session briefing
    - Generate prompts encouraging explanation
    - _Requirements: 21.3, 21.4_
  
  - [x] 17.3 Create explain_commit MCP tool
    - Allow retroactive explanation of commits
    - Create Knowledge_Item from explanation
    - Mark commit as explained
    - _Requirements: 21.5_

- [ ]* 17.4 Write unit tests for unexplained commits
  - Test unexplained commit creation
  - Test prompt generation
  - Test retroactive explanation
  - _Requirements: 21.1-21.5_

- [x] 18. Implement historical backfill
  - [x] 18.1 Create backfill_history method
    - Accept repository path and limit parameter
    - Default to last 50 commits
    - Extract SHA, message, timestamp, files
    - Create Queue_Entries for historical commits
    - Mark as unexplained (no intent creation)
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6_
  
  - [x] 18.2 Optimize backfill performance
    - Use git log with efficient formatting
    - Process commits in batches
    - Complete 50 commits in <5 seconds
    - _Requirements: 20.7_

- [ ]* 18.3 Write unit tests for historical backfill
  - Test backfill with sample repository
  - Test performance with large histories
  - Verify no intent creation for historical commits
  - _Requirements: 20.1-20.7_

- [x] 19. Checkpoint - Test complete workflow end-to-end
  - Initialize new project
  - Start skill session with intent
  - Make commits with git hooks
  - Process queue and verify reconciliation
  - Record explanations
  - Complete reviews
  - Verify level-up triggers

- [x] 20. Implement security and privacy features
  - [x] 20.1 Create code redaction system
    - Implement regex patterns for common secrets
    - Redact API keys, tokens, passwords
    - Respect .gitignore patterns
    - Allow user-configurable redaction patterns
    - _Requirements: 28.1, 28.2, 28.3_
  
  - [x] 20.2 Implement database security
    - Set restrictive file permissions on database
    - Bind dashboard to 127.0.0.1 only
    - Provide read-only dashboard access
    - _Requirements: 28.4, 28.5, 28.6_

- [ ]* 20.3 Write unit tests for security features
  - Test secret redaction with known patterns
  - Test .gitignore respect
  - Test dashboard binding restrictions
  - _Requirements: 28.1-28.6_

- [x] 21. Implement error handling and resilience
  - [x] 21.1 Add comprehensive error handling
    - Implement graceful degradation patterns
    - Add fallbacks for failed operations
    - Log all errors with context
    - _Requirements: 24.5, 24.6, 24.7, 24.8_
  
  - [x] 21.2 Create logging infrastructure
    - Log all tool calls with timestamps
    - Log database operations with execution time
    - Log git operations with status
    - Write to .learn/learnloop.log
    - Implement log rotation at 10MB
    - Keep last 5 log files
    - _Requirements: 32.1-32.6_
  
  - [x] 21.3 Implement graceful degradation
    - Fallback to manual recording if hooks fail
    - Continue with generic settings if tech detection fails
    - Store in database only if concepts.md fails
    - _Requirements: 33.1, 33.2, 33.3, 33.4, 33.5_

- [ ]* 21.4 Write unit tests for error handling
  - Test retry logic with mock failures
  - Test graceful degradation paths
  - Test logging output
  - _Requirements: 24.1-24.8, 32.1-32.6, 33.1-33.5_

- [x] 22. Implement performance optimizations
  - [x] 22.1 Add database indexes
    - Create composite indexes for common queries
    - Index (project_id, due_at, snoozed_until)
    - Index (project_id, status) for intents
    - Index (project_id, is_stale) for items
    - _Requirements: 25.3_
  
  - [x] 22.2 Implement caching layer
    - Cache readiness level calculations
    - Cache technology detection results
    - Cache code complexity scores
    - _Requirements: 11.11, 25.4_
  
  - [x] 22.3 Optimize hot paths
    - Profile queue processing performance
    - Optimize reconciliation algorithm
    - Batch database operations
    - _Requirements: 25.1-25.6_

- [ ]* 22.4 Write performance tests
  - Test initialization under 500ms
  - Test queue processing under 100ms per commit
  - Test review fetching under 50ms
  - Test conversation analysis under 200ms for 100 messages
  - _Requirements: 25.1-25.6_

- [x] 23. Implement dashboard server
  - [x] 23.1 Create dashboard web interface
    - Set up Flask/FastAPI server on port 8080
    - Bind to localhost only
    - Create project overview page
    - Display learning activity chart
    - List knowledge items with review status
    - _Requirements: 37.1-37.6_
  
  - [x] 23.2 Implement concepts.md rendering
    - Parse and render markdown
    - Add syntax highlighting for code blocks
    - _Requirements: 37.7_
  
  - [x] 23.3 Add multi-project selector
    - Create project dropdown in dashboard
    - Load project-specific data on selection
    - _Requirements: 38.4_

- [ ]* 23.4 Write integration tests for dashboard
  - Test dashboard startup and binding
  - Test project overview rendering
  - Test read-only access enforcement
  - _Requirements: 37.1-37.7_

- [x] 24. Implement cross-platform compatibility
  - [x] 24.1 Add platform-specific path handling
    - Use platformdirs for user data directories
    - Use os.path.join for cross-platform paths
    - _Requirements: 26.1, 26.2_
  
  - [x] 24.2 Detect shell environment for hooks
    - Detect bash, zsh, powershell
    - Generate compatible hook scripts
    - Handle Git Bash on Windows
    - _Requirements: 26.3, 26.4_
  
  - [x] 24.3 Handle filesystem differences
    - Support case-sensitive and case-insensitive filesystems
    - Normalize paths appropriately per platform
    - _Requirements: 26.5_

- [ ]* 24.4 Write cross-platform tests
  - Test path resolution on different platforms
  - Test hook generation for different shells
  - Test filesystem handling
  - _Requirements: 26.1-26.5_

- [x] 25. Implement multi-project support
  - [x] 25.1 Add project detection by workspace
    - Detect project from workspace path
    - Load appropriate project context
    - _Requirements: 38.1, 38.2_
  
  - [x] 25.2 Isolate data per project
    - Ensure intents scoped to project_id
    - Ensure exposures scoped to project_id
    - Ensure reviews scoped to project_id
    - _Requirements: 38.3, 38.5_
  
  - [x] 25.3 Implement per-project readiness
    - Calculate readiness per project independently
    - Cache per project
    - _Requirements: 38.6_

- [ ]* 25.4 Write integration tests for multi-project
  - Test switching between projects
  - Test data isolation
  - Test independent readiness calculation
  - _Requirements: 38.1-38.6_

- [x] 26. Implement migration from legacy LearnLoop
  - [x] 26.1 Create database migration system
    - Detect old schema version
    - Add project_level column
    - Create learning_events table
    - Backfill readiness levels
    - _Requirements: 29.1, 29.2, 29.3, 29.4_
  
  - [x] 26.2 Implement hook migration
    - Detect old hook format
    - Offer to update hooks
    - Preserve existing functionality
    - _Requirements: 29.5_
  
  - [x] 26.3 Preserve existing data
    - Migrate exposure records
    - Migrate knowledge items
    - Migrate review schedules
    - _Requirements: 29.6, 29.7_
  
  - [x] 26.4 Display migration message
    - Show one-time migration success message
    - Highlight new features
    - _Requirements: 29.8_

- [ ]* 26.5 Write migration tests
  - Test schema upgrade from old version
  - Test data preservation
  - Test hook migration
  - _Requirements: 29.1-29.8_

- [x] 27. Implement metrics collection
  - [x] 27.1 Create metrics tracking system
    - Track time to first session
    - Track daily active projects
    - Track feature discovery rate
    - Track average session length
    - Track explanation completion rate
    - Track review completion rate
    - _Requirements: 40.1-40.6_
  
  - [x] 27.2 Implement privacy controls
    - Store metrics locally only
    - Anonymize all data
    - Provide opt-out mechanism
    - _Requirements: 40.7, 40.8_

- [ ]* 27.3 Write unit tests for metrics
  - Test metric collection accuracy
  - Test anonymization
  - Test opt-out functionality
  - _Requirements: 40.1-40.8_

- [x] 28. Implement MCP tool response formatting
  - [x] 28.1 Standardize response format
    - Include "success" boolean in all responses
    - Include "error" field on failure with message
    - Include "data" field on success with results
    - Include "message" field for user display
    - Use ISO 8601 for timestamps
    - Use absolute paths for files
    - _Requirements: 30.1-30.6_

- [ ]* 28.2 Write property test for response format
  - **Property: Response format consistency**
  - **Validates: Requirements 30.1-30.6**
  - For all tool calls, verify response has "success" field
  - Verify failures have "error", successes have "data" or "message"

- [x] 29. Implement idempotency guarantees
  - [x] 29.1 Ensure commit processing idempotency
    - Use commit SHA as unique identifier
    - Skip already processed commits
    - _Requirements: 31.1_
  
  - [x] 29.2 Ensure intent matching idempotency
    - Prevent duplicate exposure creation
    - Use database constraints
    - _Requirements: 31.2_
  
  - [x] 29.3 Ensure knowledge item idempotency
    - Update existing items on duplicate key
    - Don't create duplicates
    - _Requirements: 31.3_
  
  - [x] 29.4 Ensure git hook idempotency
    - Produce identical hook file on reinstall
    - _Requirements: 31.4_

- [x] 30. Write comprehensive integration tests
  - [x] 30.1 Test zero-friction onboarding flow
    - New user initialization
    - Welcome message display
    - First intent tracking
    - First commit and reconciliation
  
  - [x] 30.2 Test complete learning cycle
    - Intent → Commit → Exposure → Explanation → Review
    - Verify data consistency throughout
  
  - [x] 30.3 Test progressive enhancement flow
    - Start at level 1
    - Progress through learning actions
    - Verify level-ups trigger correctly
    - Verify feature unlocking
  
  - [x] 30.4 Test staleness workflow
    - Create knowledge item
    - Modify tracked file
    - Verify staleness detection
    - Complete review and verify clearing
  
  - [x] 30.5 Test error recovery scenarios
    - Database lock simulation
    - Filesystem permission errors
    - Malformed queue entries
    - Verify graceful degradation

- [x] 31. Checkpoint - Complete system integration testing
  - Run all integration tests
  - Verify end-to-end workflows
  - Test error scenarios
  - Validate performance benchmarks

- [x] 32. Create comprehensive documentation
  - [x] 32.1 Write API documentation
    - Document all MCP tools with examples
    - Document data models with validation rules
    - Document algorithm specifications
  
  - [x] 32.2 Write user guide
    - Getting started tutorial
    - Progressive feature explanations
    - Best practices guide
  
  - [x] 32.3 Write migration guide
    - Legacy LearnLoop upgrade steps
    - Breaking changes documentation
    - Backward compatibility notes
  
  - [x] 32.4 Write development guide
    - Architecture overview
    - Contributing guidelines
    - Testing strategy

- [x] 33. Prepare for release
  - [x] 33.1 Update project metadata
    - Update version to 2.0.0
    - Update dependencies in pyproject.toml
    - Update README with new features
  
  - [x] 33.2 Run final test suite
    - All unit tests pass
    - All integration tests pass
    - All property tests pass
    - Performance benchmarks met
  
  - [x] 33.3 Create release artifacts
    - Build Python package
    - Generate changelog
    - Prepare release notes
  
  - [x] 33.4 Perform security review
    - Audit code redaction patterns
    - Review database permissions
    - Verify dashboard security
    - Check for dependency vulnerabilities

- [x] 34. Final checkpoint - Release readiness
  - All tests passing
  - Documentation complete
  - Performance targets met
  - Security review passed
  - Release artifacts prepared

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property-based tests validate correctness properties from design document
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis library
- Unit tests validate specific examples and edge cases using pytest
- Integration tests validate complete workflows end-to-end
- Implementation uses Python with async/await for MCP protocol
- Database uses aiosqlite for async SQLite operations
- Testing uses pytest, pytest-asyncio, and hypothesis

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1"]
    },
    {
      "id": 1,
      "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5"]
    },
    {
      "id": 2,
      "tasks": ["4.1"]
    },
    {
      "id": 3,
      "tasks": ["4.2", "4.3", "4.4"]
    },
    {
      "id": 4,
      "tasks": ["5.1", "5.2"]
    },
    {
      "id": 5,
      "tasks": ["5.3", "5.4", "5.5"]
    },
    {
      "id": 6,
      "tasks": ["6.1", "6.2", "6.3"]
    },
    {
      "id": 7,
      "tasks": ["6.4", "6.5", "6.6", "7.1"]
    },
    {
      "id": 8,
      "tasks": ["7.2", "7.3", "8.1", "8.2"]
    },
    {
      "id": 9,
      "tasks": ["8.3", "8.5", "8.6"]
    },
    {
      "id": 10,
      "tasks": ["8.4"]
    },
    {
      "id": 11,
      "tasks": ["8.7", "8.8", "8.9", "8.10"]
    },
    {
      "id": 12,
      "tasks": ["10.1", "10.3"]
    },
    {
      "id": 13,
      "tasks": ["10.2", "10.4"]
    },
    {
      "id": 14,
      "tasks": ["10.5", "10.6", "11.1", "11.3"]
    },
    {
      "id": 15,
      "tasks": ["11.2", "11.4"]
    },
    {
      "id": 16,
      "tasks": ["12.1"]
    },
    {
      "id": 17,
      "tasks": ["12.2", "12.3", "12.4"]
    },
    {
      "id": 18,
      "tasks": ["12.5", "12.6", "12.7"]
    },
    {
      "id": 19,
      "tasks": ["14.1", "14.2"]
    },
    {
      "id": 20,
      "tasks": ["14.3", "14.4", "14.5"]
    },
    {
      "id": 21,
      "tasks": ["15.1", "15.2", "15.3"]
    },
    {
      "id": 22,
      "tasks": ["15.4", "15.5", "15.6", "15.7"]
    },
    {
      "id": 23,
      "tasks": ["16.1", "16.2", "16.3", "17.1"]
    },
    {
      "id": 24,
      "tasks": ["17.2", "17.3", "17.4", "18.1"]
    },
    {
      "id": 25,
      "tasks": ["18.2", "18.3"]
    },
    {
      "id": 26,
      "tasks": ["20.1", "20.2", "20.3"]
    },
    {
      "id": 27,
      "tasks": ["21.1", "21.2", "21.3", "21.4"]
    },
    {
      "id": 28,
      "tasks": ["22.1", "22.2", "22.3", "22.4"]
    },
    {
      "id": 29,
      "tasks": ["23.1", "23.2"]
    },
    {
      "id": 30,
      "tasks": ["23.3", "23.4"]
    },
    {
      "id": 31,
      "tasks": ["24.1", "24.2", "24.3", "24.4"]
    },
    {
      "id": 32,
      "tasks": ["25.1", "25.2", "25.3", "25.4"]
    },
    {
      "id": 33,
      "tasks": ["26.1", "26.2", "26.3", "26.4", "26.5"]
    },
    {
      "id": 34,
      "tasks": ["27.1", "27.2", "27.3"]
    },
    {
      "id": 35,
      "tasks": ["28.1", "28.2"]
    },
    {
      "id": 36,
      "tasks": ["29.1", "29.2", "29.3", "29.4"]
    },
    {
      "id": 37,
      "tasks": ["30.1", "30.2", "30.3", "30.4", "30.5"]
    },
    {
      "id": 38,
      "tasks": ["32.1", "32.2", "32.3", "32.4"]
    },
    {
      "id": 39,
      "tasks": ["33.1"]
    },
    {
      "id": 40,
      "tasks": ["33.2"]
    },
    {
      "id": 41,
      "tasks": ["33.3", "33.4"]
    }
  ]
}
```
