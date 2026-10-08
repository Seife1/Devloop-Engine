"""Bounded input types: every free-text field has a size limit."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(min_length=1, max_length=2000)]
SkillId = Annotated[str, Field(min_length=1, max_length=80)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]
Limit = Annotated[int, Field(ge=1, le=50)]
