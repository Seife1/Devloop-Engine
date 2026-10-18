"""Tests for MCP server configuration schema.

Verifies that:
- Configuration defaults are valid
- Environment variable loading works
- Validation catches invalid values
- All required settings are present
"""

import os

import pytest

from learnloop.mcp.config import MCPServerConfig


class TestMCPServerConfig:
    """Test MCP server configuration."""

    def test_default_config_is_valid(self):
        """Default configuration should be valid."""
        config = MCPServerConfig.default()
        config.validate()  # Should not raise

    def test_config_validation_rejects_invalid_thresholds(self):
        """Configuration should reject thresholds outside [0, 1] range."""
        with pytest.raises(ValueError, match="complexity_significance_threshold"):
            config = MCPServerConfig(complexity_significance_threshold=1.5)
            config.validate()

        with pytest.raises(ValueError, match="auto_track_confidence_threshold"):
            config = MCPServerConfig(auto_track_confidence_threshold=-0.1)
            config.validate()

        with pytest.raises(ValueError, match="match_threshold"):
            config = MCPServerConfig(match_threshold=2.0)
            config.validate()

    def test_config_validation_rejects_invalid_weights(self):
        """Configuration should reject weights that don't sum to 1.0."""
        with pytest.raises(ValueError, match="file_overlap_weight.*time_proximity_weight"):
            config = MCPServerConfig(file_overlap_weight=0.5, time_proximity_weight=0.3)
            config.validate()

    def test_config_validation_rejects_invalid_port(self):
        """Configuration should reject invalid port numbers."""
        with pytest.raises(ValueError, match="dashboard_port"):
            config = MCPServerConfig(dashboard_port=0)
            config.validate()

        with pytest.raises(ValueError, match="dashboard_port"):
            config = MCPServerConfig(dashboard_port=99999)
            config.validate()

    def test_config_validation_rejects_negative_days(self):
        """Configuration should reject negative day values."""
        with pytest.raises(ValueError, match="intent_abandon_days"):
            config = MCPServerConfig(intent_abandon_days=-1)
            config.validate()

    def test_config_validation_rejects_negative_retries(self):
        """Configuration should reject negative retry attempts."""
        with pytest.raises(ValueError, match="db_retry_attempts"):
            config = MCPServerConfig(db_retry_attempts=-1)
            config.validate()

    def test_config_validation_rejects_invalid_log_settings(self):
        """Configuration should reject invalid logging settings."""
        with pytest.raises(ValueError, match="log_max_size_mb"):
            config = MCPServerConfig(log_max_size_mb=0)
            config.validate()

        with pytest.raises(ValueError, match="log_rotation_keep"):
            config = MCPServerConfig(log_rotation_keep=0)
            config.validate()

    def test_config_from_env_loads_legacy_tools(self):
        """Configuration should load legacy tools flag from environment."""
        os.environ["LEARNLOOP_LEGACY_TOOLS"] = "1"
        try:
            config = MCPServerConfig.from_env()
            assert config.enable_legacy_quiz_tools is True
        finally:
            os.environ.pop("LEARNLOOP_LEGACY_TOOLS", None)

    def test_config_from_env_loads_dashboard_settings(self):
        """Configuration should load dashboard settings from environment."""
        os.environ["LEARNLOOP_DASHBOARD_ENABLED"] = "1"
        os.environ["LEARNLOOP_DASHBOARD_PORT"] = "9090"
        try:
            config = MCPServerConfig.from_env()
            assert config.dashboard_enabled is True
            assert config.dashboard_port == 9090
        finally:
            os.environ.pop("LEARNLOOP_DASHBOARD_ENABLED", None)
            os.environ.pop("LEARNLOOP_DASHBOARD_PORT", None)

    def test_config_from_env_loads_log_level(self):
        """Configuration should load log level from environment."""
        os.environ["LEARNLOOP_LOG_LEVEL"] = "DEBUG"
        try:
            config = MCPServerConfig.from_env()
            assert config.log_level == "DEBUG"
        finally:
            os.environ.pop("LEARNLOOP_LOG_LEVEL", None)

    def test_config_from_env_with_overrides(self):
        """Configuration should apply direct overrides over environment variables."""
        os.environ["LEARNLOOP_DASHBOARD_PORT"] = "9090"
        try:
            config = MCPServerConfig.from_env(dashboard_port=7070)
            assert config.dashboard_port == 7070  # Override takes precedence
        finally:
            os.environ.pop("LEARNLOOP_DASHBOARD_PORT", None)

    def test_config_has_performance_constraints(self):
        """Configuration should include all performance constraints from Requirement 25."""
        config = MCPServerConfig.default()
        
        # Requirement 25.1: Project initialization under 500ms
        assert config.max_init_time_ms == 500
        
        # Requirement 25.2: Per-commit reconciliation under 100ms
        assert config.max_reconcile_time_ms == 100
        
        # Requirement 25.3: Review fetch under 50ms
        assert config.max_review_fetch_ms == 50
        
        # Session briefing under 100ms (Requirement 25.6)
        assert config.max_briefing_time_ms == 100
        
        # Conversation analysis under 200ms for 100 messages (Requirement 3.9)
        assert config.max_conversation_analysis_ms == 200

    def test_config_has_reconciliation_parameters(self):
        """Configuration should include reconciliation parameters from Requirements 7, 36."""
        config = MCPServerConfig.default()
        
        # Requirement 36.4: Match threshold
        assert 0.0 <= config.match_threshold <= 1.0
        
        # Requirement 36.1-36.3: File overlap and time proximity weights
        assert config.file_overlap_weight == 0.7
        assert config.time_proximity_weight == 0.3
        assert config.file_overlap_weight + config.time_proximity_weight == 1.0
        
        # Requirement 7.8: Intent abandonment after 14 days
        assert config.intent_abandon_days == 14

    def test_config_has_security_settings(self):
        """Configuration should include security settings from Requirement 28."""
        config = MCPServerConfig.default()
        
        # Requirement 28.1-28.3: Secret redaction
        assert config.enable_secret_redaction is True
        assert config.respect_gitignore is True
        
        # Requirement 28.5: Dashboard bound to localhost only
        assert config.dashboard_bind_address == "127.0.0.1"
        
        # Requirement 28.6: Read-only dashboard access
        assert config.dashboard_read_only is True

    def test_config_has_resilience_settings(self):
        """Configuration should include resilience settings from Requirement 24."""
        config = MCPServerConfig.default()
        
        # Requirement 24.1: Retry with exponential backoff up to 3 attempts
        assert config.db_retry_attempts == 3
        assert config.db_retry_backoff_base_ms == 100
        
        # Requirement 24.2: In-memory fallback on connection failure
        assert config.enable_in_memory_fallback is True
        
        # Requirement 24.4: Corruption detection
        assert config.enable_corruption_detection is True

    def test_config_has_storage_settings(self):
        """Configuration should include storage settings from Requirement 27."""
        config = MCPServerConfig.default()
        
        # Requirement 27.2: Database under 50MB for projects with under 5000 commits
        assert config.max_db_size_mb == 50
        
        # Requirement 27.3: Archive queue entries after 30 days
        assert config.queue_entry_archive_days == 30
        
        # Requirement 27.4: Prune low-confidence events after 90 days
        assert config.low_confidence_event_prune_days == 90
        
        # Requirement 27.5: Compress exposure record context
        assert config.enable_exposure_compression is True

    def test_config_has_auto_tracking_thresholds(self):
        """Configuration should include auto-tracking thresholds from Requirements 3, 18."""
        config = MCPServerConfig.default()
        
        # Requirement 3.3, 18.7: Complexity significance threshold
        assert config.complexity_significance_threshold == 0.3
        
        # Requirement 3.8: Auto-track confidence threshold
        assert config.auto_track_confidence_threshold == 0.7
