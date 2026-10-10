from __future__ import annotations

import pytest

from learnloop.domain.depth import depth_description, start_depth
from learnloop.domain.errors import ValidationError


def test_start_depth_mappings():
    assert start_depth("school") == 1
    assert start_depth("beginner") == 1
    assert start_depth("junior") == 2
    assert start_depth("mid") == 3
    assert start_depth("senior") == 3


def test_start_depth_case_and_whitespace():
    assert start_depth("  Junior  ") == 2
    assert start_depth("SENIOR") == 3


def test_start_depth_invalid():
    with pytest.raises(ValidationError):
        start_depth("expert")


def test_depth_ladder_descriptions():
    assert depth_description(1) == "what"
    assert depth_description(2) == "how"
    assert depth_description(3) == "why"
    assert depth_description(4) == "trade-offs"
    assert depth_description(5) == "scale/failure"


def test_depth_description_out_of_bounds():
    with pytest.raises(ValidationError):
        depth_description(0)
    with pytest.raises(ValidationError):
        depth_description(6)
