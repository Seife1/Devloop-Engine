# Requirements Document: MCP-Native LearnLoop Plugin Redesign

## Introduction

This document specifies the requirements for transforming LearnLoop from a CLI-based learning companion into an MCP-native plugin. The redesigned system eliminates adoption barriers through automatic context awareness, zero-friction setup, and progressive feature disclosure. The system maintains core learning principles (exposure vs mastery, git verification, spaced repetition) while integrating seamlessly into AI-assisted coding workflows.

The primary goal is to reduce time-to-first-value from 15+ minutes to under 2 minutes, while increasing sustained engagement through context-aware prompting and progressive enhancement.

## Glossary

- **MCP_Server**: The Model Context Protocol server that manages communication between AI assistants and LearnLoop services
- **Project_Context**: Metadata about a user's project including path, technologies, readiness level, and learning history
- **Learning_Event**: A detected opportunity for learning (implementation, decision, question, or explanation)
- **Intent_Record**: A user's stated learning goal before implementing a feature
- **Commit_Record**: Git commit metadata captured by post-commit hooks
- **Exposure_Record**: Verified pairing of an intent with a commit, proving code was written
- **Knowledge_Item**: A documented concept or skill with tracked files and review schedule
- **Readiness_Level**: User's competency level (1-4) determining feature visibility
- **Review_Schedule**: SM-2 spaced repetition schedule for a knowledge item
- **Queue_Entry**: Commit metadata waiting to be reconciled with intents
- **Staleness_Flag**: Indicator that tracked files changed since last explanation
- **Auto_Tracker**: Service that detects learning opportunities from AI conversations
- **Progressive_Enhancement_Manager**: Service controlling feature visibility based on user level
- **Git_Integration_Service**: Service managing git hooks and commit reconciliation
- **Reconciliation**: Process of matching open intents with commits based on file overlap and timing
- **Explanation_Prompt**: AI-generated question encouraging user to explain learned concepts
- **Session_Briefing**: Summary of project state and suggested actions at session start
- **Complexity_Score**: Calculated measure of code complexity (0.0-1.0)
- **Confidence_Score**: Measure of certainty in detected learning events (0.0-1.0)

## Requirements

### Requirement 1: Automatic Project Detection and Initialization

**User Story:** As a developer starting to use LearnLoop, I want the system to automatically set up without manual configuration, so that I can begin learning tracking immediately.

#### Acceptance Criteria

1. WHEN the MCP_Server initializes in a workspace, THE MCP_Server SHALL detect whether a LearnLoop project already exists for that workspace
2. WHEN no existing project is detected, THE MCP_Server SHALL create a new project record with auto-detected metadata
3. WHEN creating a new project, THE MCP_Server SHALL create the `.learn/` directory structure
4. WHEN creating a new project, THE MCP_Server SHALL initialize a `concepts.md` file in the `.learn/` directory
5. WHEN creating a new project with a git repository, THE MCP_Server SHALL install a post-commit hook
6. WHEN an existing project is detected, THE MCP_Server SHALL load the project context and update last accessed timestamp
7. THE MCP_Server SHALL detect project technologies by scanning configuration files
8. THE MCP_Server SHALL calculate initial readiness level based on existing project data
9. WHEN initialization completes in under 500 milliseconds, THE MCP_Server SHALL return project context to the AI assistant

### Requirement 2: Zero-Friction Welcome Experience

**User Story:** As a first-time LearnLoop user, I want clear guidance without overwhelming setup steps, so that I understand the value and can start immediately.

#### Acceptance Criteria

1. WHEN a new project is initialized, THE MCP_Server SHALL generate a welcome message explaining core concepts
2. THE welcome message SHALL be under 100 words
3. THE welcome message SHALL explain that no manual actions are required
4. WHEN displaying welcome messages, THE MCP_Server SHALL offer optional quick start actions
5. WHEN a user declines the quick start, THE MCP_Server SHALL proceed with passive tracking

### Requirement 3: Automatic Learning Event Detection

**User Story:** As a developer coding with AI assistance, I want the system to automatically detect learning opportunities, so that I don't need to manually mark what I'm learning.

#### Acceptance Criteria

1. WHEN the AI assistant sends code blocks, THE Auto_Tracker SHALL extract code segments with language detection
2. WHEN analyzing code segments, THE Auto_Tracker SHALL calculate complexity scores
3. WHEN complexity score exceeds 0.3, THE Auto_Tracker SHALL identify this as a significant learning event
4. WHEN detecting learning events, THE Auto_Tracker SHALL identify associated skills from code patterns
5. WHEN the AI assistant presents decisions or alternatives, THE Auto_Tracker SHALL detect decision points
6. WHEN decision points have significant alternatives, THE Auto_Tracker SHALL create decision-type learning events
7. THE Auto_Tracker SHALL assign confidence scores between 0.0 and 1.0 to all detected events
8. WHEN confidence score exceeds 0.7, THE Auto_Tracker SHALL store the learning event
9. WHEN analyzing conversations with 100 messages, THE Auto_Tracker SHALL complete analysis in under 200 milliseconds

### Requirement 4: Intent Tracking and Recording

**User Story:** As a developer starting a coding task, I want to declare my learning intent, so that the system can verify I actually implemented what I planned to learn.

#### Acceptance Criteria

1. WHEN a user calls start_skill_session with intent and files, THE MCP_Server SHALL create an Intent_Record
2. THE Intent_Record SHALL capture intent description, file list, and skills
3. THE Intent_Record SHALL be marked with status "open" upon creation
4. WHEN creating Intent_Records, THE MCP_Server SHALL store the session ID and timestamp
5. THE MCP_Server SHALL allow multiple open intents per project simultaneously
6. WHEN Intent_Records are created, THE MCP_Server SHALL respond in under 50 milliseconds

### Requirement 5: Git Hook Installation and Management

**User Story:** As a developer with existing git workflows, I want LearnLoop to integrate with git without breaking my existing hooks, so that my development process remains uninterrupted.

#### Acceptance Criteria

1. WHEN a git repository is detected, THE Git_Integration_Service SHALL check for existing post-commit hooks
2. WHEN no post-commit hook exists, THE Git_Integration_Service SHALL create a new hook file
3. WHEN an existing post-commit hook exists without LearnLoop markers, THE Git_Integration_Service SHALL append LearnLoop hook code
4. WHEN an existing LearnLoop hook is detected, THE Git_Integration_Service SHALL update it to the latest version
5. THE Git_Integration_Service SHALL mark hook code with "# learnloop-hook" comments
6. WHEN creating or modifying hook files, THE Git_Integration_Service SHALL set executable permissions
7. THE post-commit hook SHALL record commit metadata to `.learn/queue/` directory
8. THE post-commit hook SHALL complete in under 50 milliseconds to avoid delaying commits
9. IF the post-commit hook encounters errors, THEN THE hook SHALL log errors but return exit code 0

### Requirement 6: Commit Queue Recording

**User Story:** As a developer making commits, I want commit metadata captured instantly without blocking my workflow, so that tracking doesn't slow me down.

#### Acceptance Criteria

1. WHEN a git commit completes, THE post-commit hook SHALL extract commit SHA, message, timestamp, and file list
2. THE post-commit hook SHALL write commit metadata as JSON to `.learn/queue/` directory
3. WHEN writing queue entries, THE post-commit hook SHALL use commit SHA as filename for idempotency
4. THE queue file SHALL include project path to support multi-project tracking
5. THE post-commit hook SHALL complete file write in under 30 milliseconds

### Requirement 7: Intent-Commit Reconciliation

**User Story:** As a developer who declared learning intent, I want the system to verify I completed the work, so that I get credit only for actual implementation.

#### Acceptance Criteria

1. WHEN queue entries exist, THE Git_Integration_Service SHALL load unprocessed Queue_Entries
2. WHEN reconciling, THE Git_Integration_Service SHALL load all open Intent_Records for the project
3. FOR each Queue_Entry, THE Git_Integration_Service SHALL calculate match scores with all open intents
4. THE match score SHALL weight file overlap at 70% and time proximity at 30%
5. WHEN match score exceeds 0.6, THE Git_Integration_Service SHALL pair the intent with the commit
6. WHEN an intent matches a commit, THE Git_Integration_Service SHALL create an Exposure_Record
7. WHEN creating Exposure_Records, THE Git_Integration_Service SHALL mark the Intent_Record as "matched"
8. WHEN a commit matches no intents, THE Git_Integration_Service SHALL create an unexplained commit record
9. WHEN an Intent_Record is older than 14 days without matching, THE Git_Integration_Service SHALL mark it as "abandoned"
10. WHEN processing 10 queue entries, THE reconciliation SHALL complete in under 100 milliseconds

### Requirement 8: Contextual Explanation Prompts

**User Story:** As a developer who just implemented a feature, I want targeted questions that help me reflect on what I learned, so that I cement my understanding.

#### Acceptance Criteria

1. WHEN an Exposure_Record is created without explanation, THE Auto_Tracker SHALL generate an Explanation_Prompt
2. THE Explanation_Prompt SHALL include code snippets from relevant files
3. THE Explanation_Prompt SHALL limit code context to 50 lines maximum
4. WHEN generating prompts, THE Auto_Tracker SHALL create questions tailored to skill complexity
5. THE Explanation_Prompt SHALL include 2-4 open-ended questions
6. THE Explanation_Prompt SHALL encourage self-rating on a 1-5 scale
7. WHEN generating prompts for intermediate skills, THE questions SHALL ask about tradeoffs and alternatives
8. WHEN generating prompts for advanced skills, THE questions SHALL ask about edge cases and failure modes

### Requirement 9: Knowledge Item Registration

**User Story:** As a developer documenting learned concepts, I want to register knowledge items with tracked files, so that the system can detect staleness when code changes.

#### Acceptance Criteria

1. WHEN a user registers a knowledge item, THE MCP_Server SHALL create a Knowledge_Item with unique key
2. THE Knowledge_Item SHALL require a title under 100 characters
3. THE Knowledge_Item SHALL require a summary under 500 characters
4. WHEN creating Knowledge_Items, THE MCP_Server SHALL store the list of tracked files
5. THE MCP_Server SHALL classify depth_band as basic, intermediate, or advanced based on complexity
6. WHEN a Knowledge_Item is created, THE MCP_Server SHALL update the `concepts.md` file
7. WHEN updating `concepts.md`, THE MCP_Server SHALL append the new item in markdown format
8. THE MCP_Server SHALL schedule the first review for 1 day after creation

### Requirement 10: Explanation Recording and Depth Calculation

**User Story:** As a developer explaining what I learned, I want my explanation quality measured, so that I can track my understanding depth.

#### Acceptance Criteria

1. WHEN a user records an explanation, THE MCP_Server SHALL store the explanation text with item reference
2. THE MCP_Server SHALL accept self-rating values between 1.0 and 5.0
3. WHEN calculating explanation depth, THE MCP_Server SHALL analyze explanation text for technical terms
4. THE MCP_Server SHALL calculate explanation depth score between 0.0 and 1.0
5. WHEN explanation depth is calculated, THE MCP_Server SHALL update the Exposure_Record
6. THE MCP_Server SHALL mark the Exposure_Record as explanation_recorded
7. WHEN explanation quality score is below 0.4, THE MCP_Server SHALL suggest improvement prompts

### Requirement 11: Readiness Level Calculation

**User Story:** As a developer progressing with LearnLoop, I want the system to recognize my competency growth, so that I unlock advanced features when ready.

#### Acceptance Criteria

1. WHEN calculating readiness, THE Progressive_Enhancement_Manager SHALL count total commits for the project
2. THE Progressive_Enhancement_Manager SHALL count commits with recorded explanations
3. THE Progressive_Enhancement_Manager SHALL count total Knowledge_Items
4. THE Progressive_Enhancement_Manager SHALL calculate average explanation quality score
5. THE Progressive_Enhancement_Manager SHALL count completed reviews
6. THE Progressive_Enhancement_Manager SHALL calculate review accuracy percentage
7. WHEN a project has under 3 explained commits, THE readiness level SHALL be 1
8. WHEN a project has at least 3 explained commits and 2 knowledge items, THE readiness level SHALL be at least 2
9. WHEN a project has at least 10 explained commits with 0.6 average quality and 5 reviews, THE readiness level SHALL be at least 3
10. WHEN a project has at least 25 explained commits with 0.8 quality and 20 reviews with 75% accuracy, THE readiness level SHALL be 4
11. THE Progressive_Enhancement_Manager SHALL cache calculated readiness levels to avoid recalculation

### Requirement 12: Progressive Feature Unlocking

**User Story:** As a new LearnLoop user, I want to start with simple features and unlock advanced ones gradually, so that I'm not overwhelmed with complexity.

#### Acceptance Criteria

1. WHEN readiness level is 1, THE MCP_Server SHALL expose only auto-tracking and basic intent tools
2. WHEN readiness level is 2, THE MCP_Server SHALL expose explanation prompts and self-rating tools
3. WHEN readiness level is 3, THE MCP_Server SHALL expose spaced repetition review tools
4. WHEN readiness level is 4, THE MCP_Server SHALL expose deep practice and advanced analytics tools
5. WHEN a user attempts to call a tool above their level, THE MCP_Server SHALL return a friendly upgrade message
6. WHEN a user reaches a new readiness level, THE MCP_Server SHALL generate a celebration message
7. THE celebration message SHALL list newly unlocked features
8. THE celebration message SHALL show progress toward next level

### Requirement 13: Session Briefing

**User Story:** As a developer starting a new coding session, I want a quick summary of my learning state, so that I know what to focus on today.

#### Acceptance Criteria

1. WHEN an existing project is loaded, THE MCP_Server SHALL generate a Session_Briefing
2. THE Session_Briefing SHALL include days elapsed since last session
3. THE Session_Briefing SHALL count commits made since last session
4. THE Session_Briefing SHALL count unexplained commits awaiting review
5. THE Session_Briefing SHALL list Knowledge_Items with stale flags
6. THE Session_Briefing SHALL show current readiness level and next level requirements
7. THE Session_Briefing SHALL list items due for review today
8. THE Session_Briefing SHALL suggest next action based on priorities
9. WHEN generating Session_Briefing, THE MCP_Server SHALL complete in under 100 milliseconds

### Requirement 14: Staleness Detection

**User Story:** As a developer whose code evolved, I want the system to detect when my explanations are outdated, so that I can update my understanding.

#### Acceptance Criteria

1. WHEN a commit modifies tracked files, THE Git_Integration_Service SHALL check for Knowledge_Items tracking those files
2. WHEN a Knowledge_Item's tracked file is modified, THE Git_Integration_Service SHALL set the is_stale flag
3. WHEN setting staleness, THE Git_Integration_Service SHALL record the stale_since timestamp
4. WHEN a stale Knowledge_Item is reviewed, THE MCP_Server SHALL display the stale reason
5. WHEN displaying stale items, THE MCP_Server SHALL show which commit caused staleness
6. WHEN a user reviews a stale item, THE MCP_Server SHALL clear the staleness flag
7. THE Git_Integration_Service SHALL ignore whitespace-only and comment-only changes for staleness

### Requirement 15: Spaced Repetition Scheduling (SM-2 Algorithm)

**User Story:** As a developer learning concepts over time, I want reviews scheduled based on my performance, so that I review difficult concepts more frequently.

#### Acceptance Criteria

1. WHEN a Knowledge_Item is created, THE MCP_Server SHALL create a Review_Schedule with initial parameters
2. THE initial Review_Schedule SHALL set easiness to 2.5
3. THE initial Review_Schedule SHALL set interval to 1 day
4. THE initial Review_Schedule SHALL set repetitions to 0
5. WHEN a user completes a review, THE MCP_Server SHALL update the Review_Schedule based on answer quality
6. THE answer quality SHALL be an integer between 0 and 5
7. WHEN answer quality is 3 or higher, THE MCP_Server SHALL increase the interval
8. WHEN answer quality is below 3, THE MCP_Server SHALL reset interval to 1 day and repetitions to 0
9. THE MCP_Server SHALL update easiness factor using formula: `easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))`
10. THE MCP_Server SHALL clamp easiness factor between 1.3 and 2.5
11. WHEN a stale item is reviewed, THE MCP_Server SHALL reduce answer quality by 1 before applying SM-2
12. THE Review_Schedule SHALL calculate next due date as current date plus interval in days

### Requirement 16: Review Session Management

**User Story:** As a developer with due reviews, I want to complete them in batches, so that I can efficiently review multiple concepts in one session.

#### Acceptance Criteria

1. WHEN a user requests reviews, THE MCP_Server SHALL fetch items due on or before today
2. THE MCP_Server SHALL accept a limit parameter to cap the number of review items
3. WHEN fetching reviews, THE MCP_Server SHALL exclude snoozed items
4. THE MCP_Server SHALL order reviews by due date ascending
5. FOR each review item, THE MCP_Server SHALL include the Knowledge_Item summary
6. FOR each review item, THE MCP_Server SHALL include tracked file paths
7. FOR each review item, THE MCP_Server SHALL include staleness flag and reason
8. WHEN a user completes a review, THE MCP_Server SHALL record answer quality and depth reached
9. THE MCP_Server SHALL update the Review_Schedule based on recorded performance
10. WHEN reviews are complete, THE MCP_Server SHALL generate a summary with accuracy and next review dates

### Requirement 17: Review Snoozing

**User Story:** As a developer not ready to review a concept, I want to defer it temporarily, so that it doesn't clutter my review queue today.

#### Acceptance Criteria

1. WHEN a user snoozes a review, THE MCP_Server SHALL set the snoozed_until field
2. THE MCP_Server SHALL accept snooze duration in days
3. WHEN fetching due reviews, THE MCP_Server SHALL exclude items with snoozed_until after today
4. WHEN snoozed_until date passes, THE review item SHALL reappear in the due queue

### Requirement 18: Complexity Score Calculation

**User Story:** As a system tracking learning significance, I want to measure code complexity, so that I can prioritize complex learning over trivial changes.

#### Acceptance Criteria

1. WHEN calculating complexity, THE Auto_Tracker SHALL normalize code by removing comments and whitespace
2. THE Auto_Tracker SHALL calculate cyclomatic complexity
3. THE Auto_Tracker SHALL calculate maximum nesting depth
4. THE Auto_Tracker SHALL count unique identifiers
5. THE Auto_Tracker SHALL count non-empty lines
6. THE Auto_Tracker SHALL normalize each metric to a 0-1 scale
7. THE final complexity score SHALL be a weighted average: 40% cyclomatic, 30% nesting, 20% identifiers, 10% length
8. THE complexity score SHALL be between 0.0 and 1.0
9. WHEN code is trivial (under 5 lines), THE complexity score SHALL be below 0.2

### Requirement 19: Technology Detection

**User Story:** As a new LearnLoop user, I want the system to understand my project's technology stack, so that it can provide relevant learning guidance.

#### Acceptance Criteria

1. WHEN detecting technologies, THE MCP_Server SHALL scan for package.json and extract JavaScript dependencies
2. WHEN detecting technologies, THE MCP_Server SHALL scan for requirements.txt or pyproject.toml and extract Python dependencies
3. WHEN detecting technologies, THE MCP_Server SHALL scan for pom.xml or build.gradle and extract Java dependencies
4. WHEN detecting technologies, THE MCP_Server SHALL scan for Cargo.toml and extract Rust dependencies
5. WHEN detecting technologies, THE MCP_Server SHALL scan for go.mod and extract Go dependencies
6. THE MCP_Server SHALL store detected technologies with version information when available
7. WHEN technology detection completes, THE MCP_Server SHALL store results in the project record

### Requirement 20: Historical Commit Backfill

**User Story:** As a developer adopting LearnLoop in an existing project, I want the system to import my recent commit history, so that I'm not starting from zero.

#### Acceptance Criteria

1. WHEN backfilling history, THE Git_Integration_Service SHALL default to importing the last 50 commits
2. THE Git_Integration_Service SHALL accept a limit parameter to control backfill size
3. FOR each historical commit, THE Git_Integration_Service SHALL extract SHA, message, timestamp, and file list
4. THE Git_Integration_Service SHALL create Queue_Entries for historical commits
5. THE Git_Integration_Service SHALL not create Intent_Records for historical commits
6. THE Git_Integration_Service SHALL mark historical commits as unexplained
7. WHEN backfilling 50 commits, THE operation SHALL complete in under 5 seconds

### Requirement 21: Unexplained Commit Tracking

**User Story:** As a developer with commits lacking intents, I want the system to prompt me to explain them retroactively, so that I don't lose learning opportunities.

#### Acceptance Criteria

1. WHEN reconciliation finds commits without matching intents, THE Git_Integration_Service SHALL create unexplained commit records
2. THE unexplained commit record SHALL store commit SHA, message, files, and timestamp
3. WHEN unexplained commits exist, THE MCP_Server SHALL include count in Session_Briefing
4. THE MCP_Server SHALL generate prompts encouraging users to explain unexplained commits
5. WHEN a user explains an unexplained commit, THE MCP_Server SHALL create a Knowledge_Item and mark the commit as explained

### Requirement 22: Concepts File Synchronization

**User Story:** As a developer reviewing my learning, I want a human-readable markdown file listing all my knowledge items, so that I can browse them outside the tool.

#### Acceptance Criteria

1. WHEN a Knowledge_Item is created, THE MCP_Server SHALL append it to the `concepts.md` file
2. THE concepts.md entry SHALL include the item key as a heading
3. THE concepts.md entry SHALL include the title and summary
4. THE concepts.md entry SHALL include the tracked file list
5. THE concepts.md entry SHALL include the depth band
6. THE concepts.md file SHALL use markdown formatting for readability
7. WHEN updating concepts.md, THE MCP_Server SHALL create the file if it doesn't exist

### Requirement 23: Database Schema and Validation

**User Story:** As a system storing learning data, I want strong data validation, so that corrupted data doesn't break the learning loop.

#### Acceptance Criteria

1. THE Project_Context SHALL enforce readiness_level between 1 and 4
2. THE Project_Context SHALL enforce explained_commits less than or equal to total_commits
3. THE Learning_Event SHALL enforce confidence between 0.0 and 1.0
4. THE Intent_Record SHALL require matched_commit_sha when status is "matched"
5. THE Intent_Record SHALL require closed_at timestamp when status is not "open"
6. THE Exposure_Record SHALL require explanation_depth when explanation_recorded is true
7. THE Exposure_Record SHALL enforce explanation_depth between 0.0 and 1.0
8. THE Knowledge_Item SHALL enforce self_rating between 1.0 and 5.0 when not null
9. THE Review_Schedule SHALL enforce easiness between 1.3 and 2.5
10. THE Review_Schedule SHALL enforce interval as positive integer
11. THE Review_Schedule SHALL enforce repetitions as non-negative integer

### Requirement 24: Error Recovery and Resilience

**User Story:** As a developer relying on LearnLoop, I want the system to handle errors gracefully, so that failures don't disrupt my coding workflow.

#### Acceptance Criteria

1. WHEN the database is locked, THE MCP_Server SHALL retry connection with exponential backoff up to 3 attempts
2. IF database connection fails after retries, THEN THE MCP_Server SHALL create an in-memory temporary database
3. WHEN using temporary database, THE MCP_Server SHALL queue write operations for later persistence
4. WHEN the database is corrupted, THE MCP_Server SHALL detect corruption and offer to restore from backup
5. IF git hook installation fails due to permissions, THEN THE MCP_Server SHALL provide manual installation instructions
6. IF filesystem writes fail, THEN THE MCP_Server SHALL log errors and continue in read-only mode
7. IF queue processing encounters malformed JSON, THEN THE MCP_Server SHALL skip the entry and log the error
8. THE MCP_Server SHALL log all errors with timestamps and context to `.learn/errors.log`

### Requirement 25: Performance Constraints

**User Story:** As a developer expecting instant feedback, I want all operations to complete quickly, so that tracking doesn't slow me down.

#### Acceptance Criteria

1. WHEN initializing a project, THE MCP_Server SHALL complete in under 500 milliseconds
2. WHEN processing a single commit, THE reconciliation SHALL complete in under 100 milliseconds
3. WHEN fetching due reviews, THE query SHALL complete in under 50 milliseconds
4. WHEN analyzing 100 conversation messages, THE Auto_Tracker SHALL complete in under 200 milliseconds
5. WHEN the post-commit hook runs, THE hook SHALL complete in under 50 milliseconds
6. WHEN generating a Session_Briefing, THE MCP_Server SHALL complete in under 100 milliseconds

### Requirement 26: Cross-Platform Compatibility

**User Story:** As a developer on Windows, macOS, or Linux, I want LearnLoop to work consistently, so that I can use it regardless of my operating system.

#### Acceptance Criteria

1. THE MCP_Server SHALL use platformdirs to resolve user data directories on all platforms
2. THE MCP_Server SHALL use path separators appropriate for the operating system
3. THE Git_Integration_Service SHALL detect shell environment (bash, zsh, powershell) for hook installation
4. WHEN on Windows, THE Git_Integration_Service SHALL generate hooks compatible with Git Bash
5. THE MCP_Server SHALL handle case-sensitive and case-insensitive filesystems correctly

### Requirement 27: Database Storage and Growth Management

**User Story:** As a long-term LearnLoop user, I want the database to remain small and fast, so that performance doesn't degrade over time.

#### Acceptance Criteria

1. THE MCP_Server SHALL store the database in the user data directory (not `.learn/`)
2. THE database file SHALL remain under 50MB for projects with under 5000 commits
3. WHEN Queue_Entries are processed, THE MCP_Server SHALL archive them after 30 days
4. WHEN Learning_Events are older than 90 days with low confidence, THE MCP_Server SHALL prune them
5. THE MCP_Server SHALL compress code context strings in Exposure_Records

### Requirement 28: Security and Privacy

**User Story:** As a developer with proprietary code, I want sensitive data protected, so that secrets don't leak into learning records.

#### Acceptance Criteria

1. WHEN recording code contexts, THE MCP_Server SHALL apply regex-based redaction for common secret patterns
2. THE MCP_Server SHALL redact strings matching patterns like API keys, tokens, and passwords
3. THE MCP_Server SHALL respect `.gitignore` when scanning files for context
4. WHEN binding the dashboard, THE MCP_Server SHALL listen on 127.0.0.1 only
5. THE dashboard SHALL provide read-only access to learning data
6. THE database file SHALL have OS-level permissions restricting access to the owner

### Requirement 29: Migration from Legacy LearnLoop

**User Story:** As an existing LearnLoop user, I want to upgrade seamlessly, so that my learning history is preserved.

#### Acceptance Criteria

1. WHEN the MCP_Server detects an old schema version, THE MCP_Server SHALL apply database migrations
2. THE migration SHALL add the project_level column to projects table
3. THE migration SHALL create the learning_events table
4. THE migration SHALL backfill readiness levels from existing exposure and review data
5. WHEN old git hooks are detected, THE MCP_Server SHALL offer to update them
6. THE migration SHALL preserve all existing Exposure_Records
7. THE migration SHALL preserve all Knowledge_Items with review schedules
8. THE MCP_Server SHALL show a one-time migration success message

### Requirement 30: Tool Response Formatting

**User Story:** As an AI assistant integrating with LearnLoop, I want consistent response formats, so that I can present results clearly to users.

#### Acceptance Criteria

1. ALL tool responses SHALL include a "success" boolean field
2. WHEN operations fail, THE response SHALL include an "error" field with a descriptive message
3. WHEN operations succeed with data, THE response SHALL include a "data" field with the result
4. WHEN operations succeed with side effects, THE response SHALL include a "message" field for user display
5. ALL timestamps in responses SHALL use ISO 8601 format
6. ALL file paths in responses SHALL use absolute paths

### Requirement 31: Idempotency Guarantees

**User Story:** As a system handling concurrent operations, I want duplicate requests to be safe, so that race conditions don't corrupt data.

#### Acceptance Criteria

1. WHEN the same commit is processed multiple times, THE reconciliation SHALL produce identical results
2. WHEN the same intent is matched multiple times, THE system SHALL create only one Exposure_Record
3. WHEN the same Knowledge_Item key is registered twice, THE MCP_Server SHALL update the existing item
4. WHEN the same git hook is installed multiple times, THE system SHALL produce identical hook files

### Requirement 32: Logging and Observability

**User Story:** As a developer troubleshooting issues, I want detailed logs, so that I can diagnose problems independently.

#### Acceptance Criteria

1. THE MCP_Server SHALL log all tool calls with timestamps and parameters
2. THE MCP_Server SHALL log all database operations with execution time
3. THE MCP_Server SHALL log all git operations with success/failure status
4. THE MCP_Server SHALL write logs to `.learn/learnloop.log`
5. THE log file SHALL rotate when it exceeds 10MB
6. THE MCP_Server SHALL keep the last 5 log files

### Requirement 33: Graceful Degradation

**User Story:** As a developer experiencing partial system failures, I want core functionality to continue, so that minor issues don't completely block learning tracking.

#### Acceptance Criteria

1. IF git hooks fail to install, THEN THE MCP_Server SHALL offer manual recording as fallback
2. IF technology detection fails, THEN THE MCP_Server SHALL proceed with generic project settings
3. IF concepts.md cannot be written, THEN THE MCP_Server SHALL store data in database only
4. IF staleness detection fails, THEN THE MCP_Server SHALL log warning and skip staleness updates
5. IF explanation prompts cannot be generated, THEN THE MCP_Server SHALL allow manual explanation entry

### Requirement 34: Parser and Serializer Requirements

**User Story:** As a system exchanging data with AI assistants, I want robust parsing and serialization, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN parsing MCP tool call parameters, THE MCP_Server SHALL validate against JSON schema
2. WHEN serializing responses, THE MCP_Server SHALL produce valid JSON
3. THE MCP_Server SHALL include a pretty printer for debugging tool responses
4. FOR ALL valid response objects, serializing then deserializing SHALL produce equivalent objects (round-trip property)
5. WHEN parsing fails, THE MCP_Server SHALL return structured error messages with field details
6. WHEN serializing timestamps, THE MCP_Server SHALL use ISO 8601 format consistently

### Requirement 35: Queue File Format

**User Story:** As a git hook recording commits, I want a simple file format, so that queue recording is fast and reliable.

#### Acceptance Criteria

1. WHEN recording commits, THE git hook SHALL serialize commit metadata as JSON
2. THE JSON structure SHALL include fields: sha, message, timestamp, files, project_path
3. THE git hook SHALL write one file per commit using SHA as filename
4. THE queue file SHALL have a `.json` extension
5. WHEN parsing queue files, THE MCP_Server SHALL handle malformed JSON gracefully
6. THE git hook SHALL use atomic file writes to prevent partial writes

### Requirement 36: Intent Matching Algorithm Specification

**User Story:** As a system verifying learning, I want precise intent matching, so that credit is given accurately.

#### Acceptance Criteria

1. WHEN calculating file overlap, THE algorithm SHALL count files present in both intent and commit
2. THE file overlap score SHALL be normalized by the size of the intent file list
3. WHEN calculating time decay, THE algorithm SHALL use exponential decay with 24-hour half-life
4. THE match threshold SHALL be 0.6 for intent-commit pairing
5. WHEN multiple intents match a commit equally, THE algorithm SHALL select the most recent intent
6. THE algorithm SHALL not match intents created after the commit timestamp

### Requirement 37: Dashboard Availability

**User Story:** As a developer wanting to visualize my learning, I want an optional web dashboard, so that I can see charts and analytics.

#### Acceptance Criteria

1. THE MCP_Server SHALL provide a dashboard tool to start the web interface
2. WHEN the dashboard starts, THE MCP_Server SHALL bind to port 8080 on localhost
3. THE dashboard SHALL display a project overview with total commits and knowledge items
4. THE dashboard SHALL display a chart of learning activity over time
5. THE dashboard SHALL list all Knowledge_Items with review status
6. THE dashboard SHALL provide read-only access to all learning data
7. THE dashboard SHALL render markdown from concepts.md with syntax highlighting

### Requirement 38: Multi-Project Support

**User Story:** As a developer working on multiple projects, I want LearnLoop to track each project independently, so that learning contexts don't mix.

#### Acceptance Criteria

1. THE MCP_Server SHALL detect project by workspace path
2. WHEN switching workspaces, THE MCP_Server SHALL load the appropriate project context
3. THE database SHALL store multiple projects with unique identifiers
4. THE dashboard SHALL provide a project selector dropdown
5. THE MCP_Server SHALL isolate intents, exposures, and reviews per project
6. WHEN calculating readiness, THE algorithm SHALL consider only data from the current project

### Requirement 39: Depth Band Classification

**User Story:** As a system organizing knowledge, I want to classify concepts by difficulty, so that reviews are appropriately challenging.

#### Acceptance Criteria

1. WHEN registering a Knowledge_Item, THE MCP_Server SHALL classify it as basic, intermediate, or advanced
2. THE classification SHALL be based on complexity_score of associated code
3. WHEN complexity_score is below 0.3, THE depth_band SHALL be "basic"
4. WHEN complexity_score is between 0.3 and 0.6, THE depth_band SHALL be "intermediate"
5. WHEN complexity_score is above 0.6, THE depth_band SHALL be "advanced"
6. THE MCP_Server SHALL allow manual override of depth_band classification

### Requirement 40: Success Metrics Tracking

**User Story:** As a LearnLoop product team, I want to measure adoption and engagement, so that we can improve the product.

#### Acceptance Criteria

1. THE MCP_Server SHALL track time from installation to first tracked session
2. THE MCP_Server SHALL track daily active projects
3. THE MCP_Server SHALL track feature discovery rate per readiness level
4. THE MCP_Server SHALL track average session length
5. THE MCP_Server SHALL track explanation completion rate
6. THE MCP_Server SHALL track review completion rate
7. ALL metrics SHALL be stored locally and anonymized
8. THE MCP_Server SHALL provide an opt-out mechanism for metrics collection
