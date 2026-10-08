from unittest.mock import patch
import pytest

from learnloop.taxonomy.loader import load_skills


def test_load_skills_returns_valid_entries():
    skills = load_skills()
    assert len(skills) > 0

    skills_by_id = {s["id"]: s for s in skills}
    assert "python" in skills_by_id
    assert skills_by_id["python"]["parent_id"] is None

    assert "python.testing" in skills_by_id
    assert skills_by_id["python.testing"]["parent_id"] == "python"

    assert "python.testing.fixtures" in skills_by_id
    assert skills_by_id["python.testing.fixtures"]["parent_id"] == "python.testing"


def test_load_skills_rejects_missing_parent():
    mock_data = {
        "skills": [
            {"id": "nonexistent.child", "name": "Child Skill"},
        ]
    }
    with patch("learnloop.taxonomy.loader.yaml.safe_load", return_value=mock_data):
        with pytest.raises(ValueError, match="parent 'nonexistent' of 'nonexistent.child' is missing"):
            load_skills()


def test_load_skills_handles_multi_level_hierarchy():
    mock_data = {
        "skills": [
            {"id": "lang", "name": "Language"},
            {"id": "lang.tool", "name": "Tool"},
            {"id": "lang.tool.sub", "name": "Subtool"},
        ]
    }
    with patch("learnloop.taxonomy.loader.yaml.safe_load", return_value=mock_data):
        skills = load_skills()
        assert len(skills) == 3
        assert skills[0] == {"id": "lang", "name": "Language", "parent_id": None}
        assert skills[1] == {"id": "lang.tool", "name": "Tool", "parent_id": "lang"}
        assert skills[2] == {"id": "lang.tool.sub", "name": "Subtool", "parent_id": "lang.tool"}
