"""Unit tests for ExposureRecord model validation.

Tests Requirements:
- 7.6: ExposureRecord creation for verified intent-commit pairs
- 23.6: explanation_depth required when explanation_recorded
- 23.7: explanation_depth bounds validation
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.domain.models import ExposureRecord


class TestExposureRecordValidation:
    """Test ExposureRecord validation rules."""
    
    def test_valid_exposure_without_explanation(self):
        """Valid exposure record without explanation should be created."""
        project_id = str(uuid4())
        intent_id = str(uuid4())
        commit_sha = "a" * 40  # Valid 40 hex chars
        
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=project_id,
            intent_id=intent_id,
            commit_sha=commit_sha,
            skills=["python.testing"],
            files=["test_file.py"],
            verified_at=datetime.utcnow(),
            explanation_recorded=False,
            explanation_depth=None,
        )
        
        assert exposure.project_id == project_id
        assert exposure.intent_id == intent_id
        assert exposure.commit_sha == commit_sha
        assert exposure.skills == ["python.testing"]
        assert exposure.files == ["test_file.py"]
        assert not exposure.explanation_recorded
        assert exposure.explanation_depth is None
    
    def test_valid_exposure_with_explanation(self):
        """Valid exposure record with explanation should be created."""
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="b" * 40,
            skills=["python.async"],
            files=["async_code.py"],
            verified_at=datetime.utcnow(),
            explanation_recorded=True,
            explanation_depth=0.75,
        )
        
        assert exposure.explanation_recorded
        assert exposure.explanation_depth == 0.75
    
    def test_commit_sha_too_short(self):
        """Commit SHA shorter than 40 chars should raise ValidationError."""
        with pytest.raises(ValidationError, match="commit_sha must be 40 hex characters"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="abc123",  # Only 6 chars
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
            )
    
    def test_commit_sha_too_long(self):
        """Commit SHA longer than 40 chars should raise ValidationError."""
        with pytest.raises(ValidationError, match="commit_sha must be 40 hex characters"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="a" * 41,  # 41 chars
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
            )
    
    def test_commit_sha_non_hex_characters(self):
        """Commit SHA with non-hex characters should raise ValidationError."""
        with pytest.raises(ValidationError, match="commit_sha must be 40 hex characters"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="g" * 40,  # 'g' is not hex
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
            )
    
    def test_commit_sha_uppercase_rejected(self):
        """Commit SHA with uppercase letters should be rejected."""
        with pytest.raises(ValidationError, match="commit_sha must be 40 hex characters"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="A" * 40,  # Uppercase not allowed
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
            )
    
    def test_verified_at_future_rejected(self):
        """verified_at timestamp in the future should raise ValidationError."""
        future_time = datetime.utcnow() + timedelta(days=1)
        
        with pytest.raises(ValidationError, match="verified_at cannot be in the future"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="c" * 40,
                skills=["skill1"],
                files=["file.py"],
                verified_at=future_time,
            )
    
    def test_explanation_recorded_without_depth(self):
        """explanation_recorded=True without depth should raise ValidationError."""
        with pytest.raises(ValidationError, match="explanation_depth must be set when explanation_recorded is True"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="d" * 40,
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
                explanation_recorded=True,
                explanation_depth=None,  # Missing required depth
            )
    
    def test_explanation_depth_below_zero(self):
        """explanation_depth below 0.0 should raise ValidationError."""
        with pytest.raises(ValidationError, match="explanation_depth must be between 0.0 and 1.0"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="e" * 40,
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
                explanation_recorded=True,
                explanation_depth=-0.1,
            )
    
    def test_explanation_depth_above_one(self):
        """explanation_depth above 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError, match="explanation_depth must be between 0.0 and 1.0"):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="f" * 40,
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
                explanation_recorded=True,
                explanation_depth=1.1,
            )
    
    def test_explanation_depth_exactly_zero(self):
        """explanation_depth of exactly 0.0 should be valid."""
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="1" * 40,
            skills=["skill1"],
            files=["file.py"],
            verified_at=datetime.utcnow(),
            explanation_recorded=True,
            explanation_depth=0.0,
        )
        
        assert exposure.explanation_depth == 0.0
    
    def test_explanation_depth_exactly_one(self):
        """explanation_depth of exactly 1.0 should be valid."""
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="2" * 40,
            skills=["skill1"],
            files=["file.py"],
            verified_at=datetime.utcnow(),
            explanation_recorded=True,
            explanation_depth=1.0,
        )
        
        assert exposure.explanation_depth == 1.0
    
    def test_explanation_depth_without_recorded_flag(self):
        """explanation_depth without explanation_recorded=True should be valid."""
        # This is allowed - depth can be present even if flag is False
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="3" * 40,
            skills=["skill1"],
            files=["file.py"],
            verified_at=datetime.utcnow(),
            explanation_recorded=False,
            explanation_depth=0.5,
        )
        
        assert not exposure.explanation_recorded
        assert exposure.explanation_depth == 0.5


class TestExposureRecordEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_skills_list(self):
        """Empty skills list should be valid."""
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="7" * 40,
            skills=[],  # Empty list
            files=["file.py"],
            verified_at=datetime.utcnow(),
        )
        
        assert exposure.skills == []
    
    def test_empty_files_list(self):
        """Empty files list should be valid."""
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="8" * 40,
            skills=["skill1"],
            files=[],  # Empty list
            verified_at=datetime.utcnow(),
        )
        
        assert exposure.files == []
    
    def test_many_skills_and_files(self):
        """Large skills and files lists should be valid."""
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(uuid4()),
            intent_id=str(uuid4()),
            commit_sha="9" * 40,
            skills=[f"skill{i}" for i in range(100)],
            files=[f"file{i}.py" for i in range(50)],
            verified_at=datetime.utcnow(),
        )
        
        assert len(exposure.skills) == 100
        assert len(exposure.files) == 50
    
    def test_mixed_case_hex_in_sha_rejected(self):
        """Mixed case hex characters should be rejected."""
        with pytest.raises(ValidationError):
            ExposureRecord(
                id=str(uuid4()),
                project_id=str(uuid4()),
                intent_id=str(uuid4()),
                commit_sha="aBcDeF" + "0" * 34,  # Mixed case
                skills=["skill1"],
                files=["file.py"],
                verified_at=datetime.utcnow(),
            )

