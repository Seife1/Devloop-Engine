class LearnLoopError(Exception):
    """Base error. Messages are shown to the agent, so make them actionable."""


class NotFoundError(LearnLoopError):
    pass


class ValidationError(LearnLoopError):
    pass
