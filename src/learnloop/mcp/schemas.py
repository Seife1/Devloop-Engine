"""Bounded input types: every free-text field has a size limit."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(min_length=1, max_length=2000)]
SkillId = Annotated[str, Field(min_length=1, max_length=80)]
SkillProposalId = Annotated[
    str, Field(min_length=3, max_length=80, pattern=r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*){1,3}$")
]
FilePath = Annotated[str, Field(min_length=1, max_length=300)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]
Limit = Annotated[int, Field(ge=1, le=50)]

ItemKey = Annotated[str, Field(min_length=1, max_length=120)]
ItemTitle = Annotated[str, Field(min_length=1, max_length=200)]
ItemSummary = Annotated[str, Field(min_length=1, max_length=600)]
LearnerProfileLevel = Literal["school", "beginner", "junior", "mid", "senior"]
LearnerGoal = Literal["learn", "interview", "both"]
LearnerAudience = Literal["self", "classmate", "recruiter", "tech-lead"]
ItemKind = Literal["component", "decision", "concept", "bug-fix"]
ItemBand = Literal["basic", "intermediate", "advanced"]
ItemStatus = Literal["unexplained", "shaky", "explained"]


class QuizQuestion(BaseModel):
    kind: Literal["predict", "explain", "spot-the-bug", "write-code"] = "explain"
    prompt: Annotated[str, Field(min_length=1, max_length=1500)]
    reference_answer: Annotated[str, Field(min_length=1, max_length=2000)]
    rubric: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=200)]], Field(min_length=1, max_length=5)
    ]
    source_file: FilePath | None = None


class QuestionResult(BaseModel):
    ordinal: Annotated[int, Field(ge=1, le=6)]
    learner_answer: Annotated[str, Field(min_length=1, max_length=4000)]
    score: Score
    hints_used: Annotated[int, Field(ge=0, le=10)] = 0
    mistake_pattern: Annotated[str, Field(max_length=300)] | None = None
