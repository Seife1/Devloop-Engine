"""Unit tests for reconciliation helper functions.

Tests for calculate_file_overlap() and calculate_time_decay() functions.
Requirements: 36.1, 36.2, 36.3
"""

from datetime import timedelta

import pytest

from learnloop.services.reconcile_service import calculate_file_overlap, calculate_time_decay


class TestFileOverlap:
    """Test file overlap calculation (Requirements 36.1, 36.2)."""
    
    def test_empty_intent_files_returns_zero(self):
        """Empty intent file list should return 0.0 overlap."""
        assert calculate_file_overlap([], ["file1.py", "file2.py"]) == 0.0
    
    def test_empty_commit_files_returns_zero(self):
        """No overlap when commit has no files."""
        assert calculate_file_overlap(["file1.py"], []) == 0.0
    
    def test_both_empty_returns_zero(self):
        """Both empty lists should return 0.0."""
        assert calculate_file_overlap([], []) == 0.0
    
    def test_perfect_overlap_returns_one(self):
        """All intent files in commit should return 1.0."""
        intent_files = ["src/a.py", "src/b.py"]
        commit_files = ["src/a.py", "src/b.py"]
        assert calculate_file_overlap(intent_files, commit_files) == 1.0
    
    def test_partial_overlap_normalized_by_intent_size(self):
        """Partial overlap should be normalized by intent file count."""
        intent_files = ["src/a.py", "src/b.py", "src/c.py"]
        commit_files = ["src/a.py", "src/b.py", "src/d.py"]
        # 2 files overlap out of 3 intent files = 2/3
        assert calculate_file_overlap(intent_files, commit_files) == pytest.approx(2/3)
    
    def test_single_file_match(self):
        """Single file overlap case."""
        intent_files = ["src/a.py"]
        commit_files = ["src/a.py", "src/b.py"]
        assert calculate_file_overlap(intent_files, commit_files) == 1.0
    
    def test_no_overlap_returns_zero(self):
        """No overlapping files should return 0.0."""
        intent_files = ["src/a.py", "src/b.py"]
        commit_files = ["tests/test_a.py", "docs/README.md"]
        assert calculate_file_overlap(intent_files, commit_files) == 0.0
    
    def test_commit_has_more_files_than_intent(self):
        """Commit with more files than intent, partial overlap."""
        intent_files = ["src/a.py"]
        commit_files = ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]
        assert calculate_file_overlap(intent_files, commit_files) == 1.0
    
    def test_intent_has_more_files_than_commit(self):
        """Intent with more files than commit."""
        intent_files = ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]
        commit_files = ["src/a.py", "src/b.py"]
        # 2 out of 4 intent files matched
        assert calculate_file_overlap(intent_files, commit_files) == 0.5
    
    def test_duplicate_files_in_lists(self):
        """Duplicate files in either list should be handled correctly."""
        intent_files = ["src/a.py", "src/a.py", "src/b.py"]
        commit_files = ["src/a.py", "src/b.py", "src/b.py"]
        # Sets remove duplicates: {a.py, b.py} & {a.py, b.py} = 2 items
        # Intent has 3 items in list = 2/3
        assert calculate_file_overlap(intent_files, commit_files) == pytest.approx(2/3)
    
    def test_case_sensitive_matching(self):
        """File paths should be case-sensitive."""
        intent_files = ["src/File.py"]
        commit_files = ["src/file.py"]
        assert calculate_file_overlap(intent_files, commit_files) == 0.0
    
    def test_symmetry_property(self):
        """File overlap should be symmetric for same-sized lists."""
        files_a = ["a.py", "b.py", "c.py"]
        files_b = ["a.py", "b.py", "c.py"]
        assert calculate_file_overlap(files_a, files_b) == calculate_file_overlap(files_b, files_a)


class TestTimeDecay:
    """Test time decay calculation (Requirement 36.3)."""
    
    def test_zero_time_delta_returns_one(self):
        """Immediate commit (0 time difference) should return 1.0."""
        assert calculate_time_decay(timedelta(seconds=0)) == 1.0
    
    def test_negative_time_delta_returns_zero(self):
        """Commit before intent (negative delta) should return 0.0."""
        assert calculate_time_decay(timedelta(hours=-1)) == 0.0
        assert calculate_time_decay(timedelta(days=-1)) == 0.0
    
    def test_24_hour_half_life(self):
        """After 24 hours, score should be 0.5 (half-life)."""
        assert calculate_time_decay(timedelta(hours=24)) == pytest.approx(0.5)
    
    def test_48_hour_quarter_life(self):
        """After 48 hours (2 half-lives), score should be 0.25."""
        assert calculate_time_decay(timedelta(hours=48)) == pytest.approx(0.25)
    
    def test_72_hour_eighth_life(self):
        """After 72 hours (3 half-lives), score should be 0.125."""
        assert calculate_time_decay(timedelta(hours=72)) == pytest.approx(0.125)
    
    def test_12_hour_decay(self):
        """After 12 hours (half of half-life), score should be ~0.707."""
        # 2^(-12/24) = 2^(-0.5) = 0.707...
        assert calculate_time_decay(timedelta(hours=12)) == pytest.approx(0.7071, rel=0.01)
    
    def test_1_hour_minimal_decay(self):
        """After 1 hour, decay should be minimal."""
        # 2^(-1/24) ≈ 0.9716
        score = calculate_time_decay(timedelta(hours=1))
        assert 0.97 < score < 0.98
    
    def test_1_week_significant_decay(self):
        """After 1 week (168 hours), score should be very low."""
        # 168/24 = 7 half-lives: 2^(-7) = 1/128 ≈ 0.0078
        score = calculate_time_decay(timedelta(days=7))
        assert score < 0.01
    
    def test_2_weeks_near_zero(self):
        """After 2 weeks (14 days), score should be near zero."""
        # 336/24 = 14 half-lives: 2^(-14) ≈ 0.000061
        score = calculate_time_decay(timedelta(days=14))
        assert score < 0.001
    
    def test_returns_value_between_zero_and_one(self):
        """All positive time deltas should return value between 0.0 and 1.0."""
        test_deltas = [
            timedelta(minutes=1),
            timedelta(minutes=30),
            timedelta(hours=2),
            timedelta(hours=6),
            timedelta(hours=18),
            timedelta(days=1),
            timedelta(days=3),
            timedelta(days=10),
        ]
        for delta in test_deltas:
            score = calculate_time_decay(delta)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for delta {delta}"
    
    def test_monotonic_decrease(self):
        """Score should decrease monotonically as time increases."""
        deltas = [
            timedelta(hours=0),
            timedelta(hours=1),
            timedelta(hours=6),
            timedelta(hours=12),
            timedelta(hours=24),
            timedelta(hours=48),
            timedelta(days=7),
        ]
        scores = [calculate_time_decay(d) for d in deltas]
        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], f"Score not decreasing: {scores[i]} -> {scores[i+1]}"
    
    def test_fractional_hours(self):
        """Should handle fractional hours correctly."""
        # 6.5 hours
        score = calculate_time_decay(timedelta(hours=6, minutes=30))
        assert 0.8 < score < 0.9


class TestIntegrationScenarios:
    """Integration tests showing how overlap and time decay work together."""
    
    def test_perfect_match_immediate_commit(self):
        """Perfect file overlap with immediate commit gives high score."""
        intent_files = ["src/a.py", "src/b.py"]
        commit_files = ["src/a.py", "src/b.py"]
        time_delta = timedelta(minutes=5)
        
        file_score = calculate_file_overlap(intent_files, commit_files)
        time_score = calculate_time_decay(time_delta)
        
        # Combined score: 70% file overlap + 30% time proximity
        combined = (file_score * 0.7) + (time_score * 0.3)
        
        assert file_score == 1.0
        assert time_score > 0.99
        assert combined > 0.99  # Should be very close to 1.0
    
    def test_partial_match_delayed_commit(self):
        """Partial file overlap with delayed commit."""
        intent_files = ["src/a.py", "src/b.py", "src/c.py"]
        commit_files = ["src/a.py", "src/d.py"]
        time_delta = timedelta(hours=12)
        
        file_score = calculate_file_overlap(intent_files, commit_files)
        time_score = calculate_time_decay(time_delta)
        
        # Combined score
        combined = (file_score * 0.7) + (time_score * 0.3)
        
        assert file_score == pytest.approx(1/3)  # 1 of 3 intent files
        assert time_score == pytest.approx(0.7071, rel=0.01)
        assert combined == pytest.approx((1/3 * 0.7) + (0.7071 * 0.3), rel=0.01)
    
    def test_match_threshold_boundary(self):
        """Test scenarios around the 0.6 match threshold."""
        # Scenario 1: Just above threshold
        # Need combined score > 0.6
        # With 100% file overlap and ~5 hour delay:
        intent_files = ["src/a.py"]
        commit_files = ["src/a.py"]
        time_delta = timedelta(hours=5)
        
        file_score = calculate_file_overlap(intent_files, commit_files)
        time_score = calculate_time_decay(time_delta)
        combined = (file_score * 0.7) + (time_score * 0.3)
        
        assert file_score == 1.0
        assert combined > 0.6  # Should pass threshold
        
        # Scenario 2: Below threshold
        # 50% file overlap, 24 hour delay
        intent_files = ["src/a.py", "src/b.py"]
        commit_files = ["src/a.py", "src/c.py"]
        time_delta = timedelta(hours=24)
        
        file_score = calculate_file_overlap(intent_files, commit_files)
        time_score = calculate_time_decay(time_delta)
        combined = (file_score * 0.7) + (time_score * 0.3)
        
        assert file_score == 0.5
        assert time_score == 0.5
        # (0.5 * 0.7) + (0.5 * 0.3) = 0.35 + 0.15 = 0.5
        assert combined == pytest.approx(0.5)
        assert combined < 0.6  # Should fail threshold
