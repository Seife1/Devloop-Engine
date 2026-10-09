from learnloop.domain.evidence_ranking import rank_evidence_files


def test_ranking_tiers_order():
    skill_id = "python.testing"
    commit_files = [
        "README.md",
        "poetry.lock",
        "src/auth/service.py",
        "src/misc.py",
        "tests/test_service.py",
        "src/important.py",
    ]
    declared_touched = ["src/important.py"]
    intent_text = "Implement authentication service logic and tests"
    mapped_skills_by_file = {
        "tests/test_service.py": ["python", "python.testing"],
        "src/auth/service.py": ["python", "web.auth"],
        "src/misc.py": ["python"],
        "src/important.py": ["python"],
    }

    ranked = rank_evidence_files(
        skill_id=skill_id,
        commit_files=commit_files,
        declared_touched=declared_touched,
        intent_text=intent_text,
        mapped_skills_by_file=mapped_skills_by_file,
    )

    # 1. declared+touched: src/important.py
    # 2. maps to python.testing: tests/test_service.py (and src/misc.py maps to parent python)
    # Note: mapped skills include target skill OR parent/child, so:
    # tests/test_service.py (python.testing), src/misc.py (python), src/auth/service.py (python)
    # README.md and poetry.lock are noise without matching skill -> excluded
    assert "README.md" not in ranked
    assert "poetry.lock" not in ranked
    assert ranked[0] == "src/important.py"
    assert "tests/test_service.py" in ranked


def test_ranking_noise_included_when_maps_to_skill():
    skill_id = "devops.ci"
    commit_files = [".github/workflows/ci.yml", "README.md"]
    declared_touched = []
    intent_text = "Update continuous integration workflows"
    mapped_skills_by_file = {
        ".github/workflows/ci.yml": ["devops.ci"],
    }

    ranked = rank_evidence_files(
        skill_id=skill_id,
        commit_files=commit_files,
        declared_touched=declared_touched,
        intent_text=intent_text,
        mapped_skills_by_file=mapped_skills_by_file,
    )

    assert ".github/workflows/ci.yml" in ranked
    assert "README.md" not in ranked


def test_ranking_token_overlap_precedes_arbitrary_rest():
    skill_id = "rust"  # No file maps to rust
    commit_files = ["src/billing_calculator.py", "src/zebra.py", "src/account.py"]
    declared_touched = []
    intent_text = "Fix billing calculation rounding bug"
    mapped_skills_by_file = {}

    ranked = rank_evidence_files(
        skill_id=skill_id,
        commit_files=commit_files,
        declared_touched=declared_touched,
        intent_text=intent_text,
        mapped_skills_by_file=mapped_skills_by_file,
    )

    # billing_calculator overlaps "billing"
    assert ranked[0] == "src/billing_calculator.py"
    # The rest sorted by path: src/account.py, then src/zebra.py
    assert ranked[1:] == ["src/account.py", "src/zebra.py"]


def test_ranking_determinism_and_large_commit():
    skill_id = "python"
    commit_files = [f"src/module_{i:03d}.py" for i in range(500)]
    declared_touched = ["src/module_042.py", "src/module_100.py"]
    intent_text = "Refactor module_300 and module_301"
    mapped_skills_by_file = {f: ["python"] for f in commit_files}

    first_run = rank_evidence_files(
        skill_id=skill_id,
        commit_files=commit_files,
        declared_touched=declared_touched,
        intent_text=intent_text,
        mapped_skills_by_file=mapped_skills_by_file,
    )

    for _ in range(5):
        run = rank_evidence_files(
            skill_id=skill_id,
            commit_files=list(reversed(commit_files)),
            declared_touched=declared_touched,
            intent_text=intent_text,
            mapped_skills_by_file=mapped_skills_by_file,
        )
        assert run == first_run

    # Declared touched must be first
    assert first_run[0] == "src/module_042.py"
    assert first_run[1] == "src/module_100.py"
    assert len(first_run) == 500
