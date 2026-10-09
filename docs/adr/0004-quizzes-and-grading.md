# ADR 0004: Quizzes, grading and the honesty of mastery

**Status:** accepted

**Decision.**
- The server never calls an LLM. `get_teaching_context` returns a bounded evidence bundle (<= 5 commits,
  8 files each, clipped text) plus teaching instructions; the agent writes the lesson and grades.
- The agent must store the quiz (`create_quiz`) *before* asking, so rubric and reference answer are fixed in advance.
- `record_quiz_result` rejects scores without the learner's verbatim answer, requires exactly one result per
  question, and can run once per quiz. The write is one transaction.
- One quiz = one mastery attempt (mean score). Confidence therefore counts independent quizzes, not questions.
- Support fades via `level_for`: it takes >= 3 attempts to leave "guided", so one lucky quiz can't remove support.
- Wrong answers with a `mistake_pattern` feed `known_mistakes`, which the next lesson must target.

**Known limit.** The server cannot verify that `learner_answer` is really the learner's, or that grading was fair.
This is an honor-system boundary between the agent and the server; the audit trail (`quiz_answers`) makes it reviewable.
