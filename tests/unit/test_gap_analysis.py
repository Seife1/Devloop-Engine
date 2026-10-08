from learnloop.domain.gap_analysis import SkillStanding, rank_gaps


def S(id, exposure, mastery, attempts):
    return SkillStanding(id, id, exposure, mastery, attempts)


def test_demonstrated_weakness_outranks_untested_outranks_mastered():
    ranked = rank_gaps(
        [
            S("mastered", 10, 0.95, 8),
            S("untested", 6, None, 0),
            S("weak", 6, 0.2, 4),
        ]
    )
    assert [s.skill_id for s in ranked] == ["weak", "untested"]


def test_no_exposure_is_not_a_gap():
    assert rank_gaps([S("never_used", 0, 0.1, 5)]) == []
