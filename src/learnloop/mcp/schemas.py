"""Bounded input types: every free-text field has a size limit."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(min_length=1, max_length=2000)]
SkillId = Annotated[str, Field(min_length=1, max_length=80)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]
Limit = Annotated[int, Field(ge=1, le=50)]

from typing import Literal  # noqa: E402

from pydantic import BaseModel  # noqa: E402


class QuizQuestion(BaseModel):
    kind: Literal["predict", "explain", "spot-the-bug", "write-code"] = "explain"
    prompt: Annotated[str, Field(min_length=1, max_length=1500)]
    reference_answer: Annotated[str, Field(min_length=1, max_length=2000)]
    rubric: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=200)]], Field(min_length=1, max_length=5)
    ]


class QuestionResult(BaseModel):
    ordinal: Annotated[int, Field(ge=1, le=6)]
    learner_answer: Annotated[str, Field(min_length=1, max_length=4000)]
    score: Score
    hints_used: Annotated[int, Field(ge=0, le=10)] = 0
    mistake_pattern: Annotated[str, Field(max_length=300)] | None = None
