"""MCP server configuration schema.

This module defines configuration settings specific to MCP server operations,
including transport settings, feature flags, and performance tuning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for LearnLoop MCP server.

    Requirements:
    - 26.1: Cross-platform compatibility
    - 26.2: Platform-appropriate path handling
    - 27.1: Database storage in user data directory
    """

    # Server Identity
    server_name: str = "learnloop"
    server_version: str = "0.5.3"

    # Transport Configuration
    transport_type: Literal["stdio", "sse"] = "stdio"
    
    # Feature Flags (Progressive Enhancement)
    enable_auto_tracking: bool = True
    enable_explanation_prompts: bool = True
    enable_spaced_repetition: bool = True
    enable_deep_practice: bool = True
    
    # Legacy Features (disabled by default per ADR-0002)
    enable_legacy_quiz_tools: bool = False
    
    # Performance Settings (Requirement 25.1-25.6)
    max_init_time_ms: int = 500  # Project initialization timeout
    max_reconcile_time_ms: int = 100  # Per-commit reconciliation timeout
    max_review_fetch_ms: int = 50  # Review query timeout
    max_briefing_time_ms: int = 100  # Session briefing generation timeout
    max_conversation_analysis_ms: int = 200  # For 100 messages
    
    # Queue Processing
    max_queue_files_per_ingest: int = 200
    max_queue_file_bytes: int = 200_000
    
    # Git Integration
    git_hook_timeout_ms: int = 50  # Post-commit hook execution timeout
    
    # Staleness Detection
    enable_semantic_diff: bool = True  # Use AST comparison for staleness
    staleness_confidence_threshold: float = 0.7
    
    # Auto-Tracking Thresholds (Requirement 3.3, 3.8, 18.7)
    complexity_significance_threshold: float = 0.3
    auto_track_confidence_threshold: float = 0.7
    
    # Intent Reconciliation (Requirement 7.3, 7.4, 36.4)
    match_threshold: float = 0.6
    file_overlap_weight: float = 0.7
    time_proximity_weight: float = 0.3
    intent_abandon_days: int = 14
    
    # Database Settings (Requirement 27.2-27.5)
    max_db_size_mb: int = 50
    queue_entry_archive_days: int = 30
    low_confidence_event_prune_days: int = 90
    enable_exposure_compression: bool = True
    
    # Retry and Resilience (Requirement 24.1-24.4)
    db_retry_attempts: int = 3
    db_retry_backoff_base_ms: int = 100  # Exponential backoff base
    enable_in_memory_fallback: bool = True
    enable_corruption_detection: bool = True
    
    # Security and Privacy (Requirement 28.1-28.3)
    enable_secret_redaction: bool = True
    respect_gitignore: bool = True
    custom_redaction_patterns: list[str] = field(default_factory=list)
    
    # Dashboard Settings (Requirement 37.1, 37.2, 28.5)
    dashboard_enabled: bool = False
    dashboard_port: int = 8080
    dashboard_bind_address: str = "127.0.0.1"  # Localhost only for security
    dashboard_read_only: bool = True
    
    # Logging (Requirement 32.1-32.6)
    enable_logging: bool = True
    log_file_name: str = "learnloop.log"
    log_max_size_mb: int = 10
    log_rotation_keep: int = 5
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    # Metrics Collection (Requirement 40.1-40.8)
    enable_metrics: bool = True
    metrics_anonymous: bool = True
    metrics_local_only: bool = True

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate thresholds are in valid ranges
        if not 0.0 <= self.complexity_significance_threshold <= 1.0:
            raise ValueError(
                f"complexity_significance_threshold must be 0.0-1.0, "
                f"got {self.complexity_significance_threshold}"
            )
        
        if not 0.0 <= self.auto_track_confidence_threshold <= 1.0:
            raise ValueError(
                f"auto_track_confidence_threshold must be 0.0-1.0, "
                f"got {self.auto_track_confidence_threshold}"
            )
        
        if not 0.0 <= self.match_threshold <= 1.0:
            raise ValueError(f"match_threshold must be 0.0-1.0, got {self.match_threshold}")
        
        if not 0.0 <= self.staleness_confidence_threshold <= 1.0:
            raise ValueError(
                f"staleness_confidence_threshold must be 0.0-1.0, "
                f"got {self.staleness_confidence_threshold}"
            )
        
        # Validate weights sum appropriately
        weight_sum = self.file_overlap_weight + self.time_proximity_weight
        if not 0.99 <= weight_sum <= 1.01:  # Allow small floating point error
            raise ValueError(
                f"file_overlap_weight + time_proximity_weight must sum to 1.0, "
                f"got {weight_sum}"
            )
        
        # Validate positive integers
        if self.intent_abandon_days <= 0:
            raise ValueError(f"intent_abandon_days must be positive, got {self.intent_abandon_days}")
        
        if self.db_retry_attempts < 0:
            raise ValueError(f"db_retry_attempts must be non-negative, got {self.db_retry_attempts}")
        
        # Validate dashboard settings
        if self.dashboard_port <= 0 or self.dashboard_port > 65535:
            raise ValueError(f"dashboard_port must be 1-65535, got {self.dashboard_port}")
        
        # Validate logging settings
        if self.log_max_size_mb <= 0:
            raise ValueError(f"log_max_size_mb must be positive, got {self.log_max_size_mb}")
        
        if self.log_rotation_keep <= 0:
            raise ValueError(f"log_rotation_keep must be positive, got {self.log_rotation_keep}")

    @classmethod
    def default(cls) -> MCPServerConfig:
        """Create configuration with default values.

        Returns:
            MCPServerConfig with all default settings
        """
        return cls()

    @classmethod
    def from_env(cls, **overrides) -> MCPServerConfig:
        """Create configuration from environment variables with optional overrides.

        Environment variables:
        - LEARNLOOP_LEGACY_TOOLS: Enable legacy quiz tools (0/1)
        - LEARNLOOP_DASHBOARD_ENABLED: Enable dashboard server (0/1)
        - LEARNLOOP_DASHBOARD_PORT: Dashboard port (default 8080)
        - LEARNLOOP_LOG_LEVEL: Logging level (DEBUG/INFO/WARNING/ERROR)
        - LEARNLOOP_METRICS_ENABLED: Enable metrics collection (0/1)

        Args:
            **overrides: Direct configuration overrides

        Returns:
            MCPServerConfig with environment variables applied
        """
        import os

        config_dict = {
            "enable_legacy_quiz_tools": os.environ.get("LEARNLOOP_LEGACY_TOOLS") == "1",
            "dashboard_enabled": os.environ.get("LEARNLOOP_DASHBOARD_ENABLED") == "1",
            "dashboard_port": int(os.environ.get("LEARNLOOP_DASHBOARD_PORT", "8080")),
            "log_level": os.environ.get("LEARNLOOP_LOG_LEVEL", "INFO"),
            "enable_metrics": os.environ.get("LEARNLOOP_METRICS_ENABLED", "1") == "1",
        }

        # Apply overrides
        config_dict.update(overrides)

        config = cls(**config_dict)
        config.validate()
        return config
