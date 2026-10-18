"""Unit tests for Auto-Tracker service.

Tests conversation analysis, code extraction, decision detection,
and confidence scoring.

Requirements: 3.1-3.9
"""

from datetime import datetime, timezone

import pytest

from learnloop.domain.learning_event import EventSource, EventType
from learnloop.services.auto_tracker_service import AutoTrackerService, Message


@pytest.fixture
def auto_tracker() -> AutoTrackerService:
    """Create an auto-tracker service instance."""
    return AutoTrackerService()


@pytest.fixture
def sample_project_id() -> str:
    """Sample project ID for tests."""
    return "test-project-123"


def test_analyze_empty_conversation(auto_tracker: AutoTrackerService, sample_project_id: str):
    """Test analyzing an empty conversation returns no events."""
    messages: list[Message] = []
    events = auto_tracker.analyze_conversation(messages, sample_project_id)
    assert events == []


def test_extract_code_blocks_fenced(auto_tracker: AutoTrackerService):
    """Test extracting fenced code blocks from markdown.
    
    Requirement 3.1: Extract code blocks from assistant messages.
    """
    content = """
    Here's a Python example:
    ```python
    def hello():
        print("Hello, world!")
    ```
    That's the code.
    """

    blocks = auto_tracker._extract_code_blocks(content)
    assert len(blocks) == 1
    assert "def hello" in blocks[0]["code"]
    assert blocks[0]["language"] == "python"


def test_extract_code_blocks_multiple(auto_tracker: AutoTrackerService):
    """Test extracting multiple code blocks."""
    content = """
    Python version:
    ```python
    def foo():
        pass
    ```
    
    JavaScript version:
    ```javascript
    function foo() {}
    ```
    """

    blocks = auto_tracker._extract_code_blocks(content)
    assert len(blocks) == 2
    assert blocks[0]["language"] == "python"
    assert blocks[1]["language"] == "javascript"


def test_detect_language_python(auto_tracker: AutoTrackerService):
    """Test language detection for Python code."""
    code = """
    def calculate(x, y):
        return x + y
    """
    language = auto_tracker._detect_language(code, "")
    assert language == "python"


def test_detect_language_javascript(auto_tracker: AutoTrackerService):
    """Test language detection for JavaScript code."""
    code = """
    const add = (x, y) => x + y;
    """
    language = auto_tracker._detect_language(code, "")
    assert language == "javascript"


def test_detect_language_from_context(auto_tracker: AutoTrackerService):
    """Test language detection from surrounding context."""
    code = "x = 42"
    context = "Here's a Python snippet: ```python"
    language = auto_tracker._detect_language(code, context)
    assert language == "python"


def test_is_significant_code_true(auto_tracker: AutoTrackerService):
    """Test significant code detection."""
    code = """
    def process_data(items):
        result = []
        for item in items:
            if item.valid:
                result.append(item)
        return result
    """
    assert auto_tracker._is_significant_code(code) is True


def test_is_significant_code_false_too_short(auto_tracker: AutoTrackerService):
    """Test that very short code is not significant."""
    code = "x = 42"
    assert auto_tracker._is_significant_code(code) is False


def test_is_significant_code_false_no_logic(auto_tracker: AutoTrackerService):
    """Test that code without logic is not significant."""
    code = """
    name = "Alice"
    age = 30
    """
    assert auto_tracker._is_significant_code(code) is False


def test_extract_context(auto_tracker: AutoTrackerService):
    """Test extracting context around code blocks."""
    content = """
    Here is how to implement authentication.
    ```python
    def authenticate(user):
        return verify_password(user)
    ```
    This handles user login securely.
    """
    code = "def authenticate(user):\n    return verify_password(user)"
    context = auto_tracker._extract_context(content, code)

    assert "authentication" in context.lower()
    assert "login" in context.lower()


def test_extract_decisions(auto_tracker: AutoTrackerService):
    """Test extracting decision points from conversation."""
    content = """
    We could use REST for the API. Alternatively, we could use GraphQL.
    Another option is gRPC for better performance.
    """

    decisions = auto_tracker._extract_decisions(content)
    assert len(decisions) >= 1
    assert any("REST" in d for d in decisions)


def test_extract_alternatives_numbered(auto_tracker: AutoTrackerService):
    """Test extracting numbered alternatives."""
    content = """
    Here are the options:
    1. Use PostgreSQL for reliability
    2. Use MongoDB for flexibility
    3. Use Redis for speed
    """

    alternatives = auto_tracker._extract_alternatives(content, "database options")
    assert len(alternatives) == 3
    assert any("PostgreSQL" in alt for alt in alternatives)
    assert any("MongoDB" in alt for alt in alternatives)


def test_extract_alternatives_bullets(auto_tracker: AutoTrackerService):
    """Test extracting bullet point alternatives."""
    content = """
    Consider these approaches:
    - Implement caching layer
    - Optimize database queries
    - Use CDN for static assets
    """

    alternatives = auto_tracker._extract_alternatives(content, "optimization")
    assert len(alternatives) == 3
    assert any("caching" in alt.lower() for alt in alternatives)


def test_has_significant_alternatives_true(auto_tracker: AutoTrackerService):
    """Test significant alternatives detection."""
    alternatives = [
        "Use React for component-based architecture",
        "Use Vue.js for simpler learning curve",
    ]
    assert auto_tracker._has_significant_alternatives(alternatives) is True


def test_has_significant_alternatives_false_too_few(auto_tracker: AutoTrackerService):
    """Test that single alternative is not significant."""
    alternatives = ["Use React"]
    assert auto_tracker._has_significant_alternatives(alternatives) is False


def test_has_significant_alternatives_false_too_short(auto_tracker: AutoTrackerService):
    """Test that very short alternatives are not significant."""
    alternatives = ["React", "Vue"]
    assert auto_tracker._has_significant_alternatives(alternatives) is False


def test_detect_skills_from_language(auto_tracker: AutoTrackerService):
    """Test skill detection from programming language."""
    skills = auto_tracker._detect_skills_from_language("python")
    assert skills == ["lang:python"]

    skills = auto_tracker._detect_skills_from_language("unknown")
    assert skills == []


def test_extract_decision_skills(auto_tracker: AutoTrackerService):
    """Test extracting skills from decision points."""
    from learnloop.services.auto_tracker_service import DecisionPoint

    decision = DecisionPoint(
        decision="We need to optimize database performance for queries",
        timestamp=datetime.now(timezone.utc),
        alternatives=["Add indexes", "Use caching"],
    )

    skills = auto_tracker._extract_decision_skills(decision)
    assert "decision-making" in skills
    assert "architecture" in skills
    assert "performance" in skills
    assert "database" in skills


def test_calculate_basic_complexity_trivial(auto_tracker: AutoTrackerService):
    """Test complexity calculation for trivial code.
    
    Requirement 18.9: Trivial code (<5 lines) scores below 0.2.
    """
    code = "x = 42\ny = 100"
    complexity = auto_tracker._calculate_basic_complexity(code)
    assert 0.0 <= complexity < 0.2


def test_calculate_basic_complexity_moderate(auto_tracker: AutoTrackerService):
    """Test complexity calculation for moderate code."""
    code = """
    def process(items):
        result = []
        for item in items:
            if item.valid:
                result.append(item.value)
        return result
    """
    complexity = auto_tracker._calculate_basic_complexity(code)
    assert 0.2 <= complexity <= 0.8


def test_calculate_basic_complexity_complex(auto_tracker: AutoTrackerService):
    """Test complexity calculation for complex code."""
    code = """
    def complex_algorithm(data):
        result = []
        for i in range(len(data)):
            if data[i] > 0:
                for j in range(i):
                    if data[j] < data[i]:
                        result.append((i, j))
            elif data[i] < 0:
                try:
                    result.append(process(data[i]))
                except Exception:
                    pass
        return result
    """
    complexity = auto_tracker._calculate_basic_complexity(code)
    assert 0.5 <= complexity <= 1.0


def test_calculate_basic_complexity_bounds(auto_tracker: AutoTrackerService):
    """Test that complexity score is always between 0.0 and 1.0.
    
    Requirement 18.7: Complexity score must be between 0.0 and 1.0.
    """
    # Test with various code samples
    test_cases = [
        "x = 1",  # Minimal
        "def foo(): pass" * 100,  # Very long but simple
        "if x: y\n" * 50,  # Many conditionals
    ]

    for code in test_cases:
        complexity = auto_tracker._calculate_basic_complexity(code)
        assert 0.0 <= complexity <= 1.0, f"Complexity {complexity} out of bounds for: {code[:50]}"


def test_calculate_confidence(auto_tracker: AutoTrackerService):
    """Test confidence score calculation for code segments."""
    from learnloop.services.auto_tracker_service import CodeSegment

    segment = CodeSegment(
        code="def hello(): pass",
        language="python",
        timestamp=datetime.now(timezone.utc),
        context="This is a simple greeting function for demonstration",
    )

    confidence = auto_tracker._calculate_confidence(segment, ["lang:python"], 0.5)
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.5  # Should be above base with boosts


def test_calculate_decision_confidence(auto_tracker: AutoTrackerService):
    """Test confidence score calculation for decisions."""
    from learnloop.services.auto_tracker_service import DecisionPoint

    decision = DecisionPoint(
        decision="Choose between REST and GraphQL",
        timestamp=datetime.now(timezone.utc),
        alternatives=[
            "REST API provides simplicity and wide adoption",
            "GraphQL offers flexible queries and reduces over-fetching",
        ],
    )

    confidence = auto_tracker._calculate_decision_confidence(decision)
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.5  # Should be above base with alternatives


def test_analyze_conversation_with_code(
    auto_tracker: AutoTrackerService, sample_project_id: str
):
    """Test full conversation analysis with code implementation.
    
    Requirements:
        - 3.1: Extract code blocks from assistant messages
        - 3.7: Assign confidence scores between 0.0 and 1.0
    """
    messages = [
        Message(
            role="user",
            content="How do I implement a function to calculate factorial?",
            timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ),
        Message(
            role="assistant",
            content="""
            Here's how to implement factorial:
            ```python
            def factorial(n):
                if n <= 1:
                    return 1
                else:
                    return n * factorial(n - 1)
            ```
            This recursive implementation is elegant and easy to understand.
            """,
            timestamp=datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc),
        ),
    ]

    events = auto_tracker.analyze_conversation(messages, sample_project_id)

    # Should detect at least one implementation event
    assert len(events) >= 1

    impl_events = [e for e in events if e.event_type == EventType.IMPLEMENTATION]
    assert len(impl_events) >= 1

    event = impl_events[0]
    assert event.project_id == sample_project_id
    assert event.source == EventSource.CONVERSATION
    assert 0.0 <= event.confidence <= 1.0
    assert "factorial" in event.content["code"]
    assert event.content["language"] == "python"
    assert "lang:python" in event.skills


def test_analyze_conversation_with_decision(
    auto_tracker: AutoTrackerService, sample_project_id: str
):
    """Test conversation analysis with decision points."""
    messages = [
        Message(
            role="user",
            content="What database should I use?",
            timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ),
        Message(
            role="assistant",
            content="""
            You have several options:
            1. PostgreSQL - Best for complex queries and ACID compliance
            2. MongoDB - Better for flexible schemas and horizontal scaling
            3. Redis - Optimal for caching and high-speed access
            
            Consider your data structure and query patterns when deciding.
            """,
            timestamp=datetime(2024, 1, 1, 10, 1, tzinfo=timezone.utc),
        ),
    ]

    events = auto_tracker.analyze_conversation(messages, sample_project_id)

    # Should detect decision events
    decision_events = [e for e in events if e.event_type == EventType.DECISION]
    assert len(decision_events) >= 1

    event = decision_events[0]
    assert event.project_id == sample_project_id
    assert event.source == EventSource.CONVERSATION
    assert 0.0 <= event.confidence <= 1.0
    assert "alternatives" in event.content
    assert len(event.content["alternatives"]) >= 2


def test_analyze_conversation_filters_trivial_code(
    auto_tracker: AutoTrackerService, sample_project_id: str
):
    """Test that trivial code is filtered out.
    
    Requirement 3.3: Filter by complexity threshold.
    """
    messages = [
        Message(
            role="assistant",
            content="""
            Set a variable like this:
            ```python
            x = 42
            ```
            """,
            timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ),
    ]

    events = auto_tracker.analyze_conversation(messages, sample_project_id)

    # Trivial code should be filtered out
    impl_events = [e for e in events if e.event_type == EventType.IMPLEMENTATION]
    assert len(impl_events) == 0


def test_deduplicate_events(auto_tracker: AutoTrackerService, sample_project_id: str):
    """Test event deduplication."""
    from learnloop.domain.learning_event import LearningEvent

    now = datetime.now(timezone.utc)

    # Create duplicate events
    events = [
        LearningEvent.create(
            id="1",
            project_id=sample_project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "def foo(): pass"},
            skills=["lang:python"],
            confidence=0.8,
            source=EventSource.CONVERSATION,
        ),
        LearningEvent.create(
            id="2",
            project_id=sample_project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "def foo(): pass"},
            skills=["lang:python"],
            confidence=0.8,
            source=EventSource.CONVERSATION,
        ),
    ]

    deduplicated = auto_tracker._deduplicate_events(events)
    assert len(deduplicated) == 1


def test_sort_by_relevance(auto_tracker: AutoTrackerService, sample_project_id: str):
    """Test sorting events by confidence score."""
    from learnloop.domain.learning_event import LearningEvent

    now = datetime.now(timezone.utc)

    events = [
        LearningEvent.create(
            id="1",
            project_id=sample_project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "x = 1"},
            skills=[],
            confidence=0.5,
            source=EventSource.CONVERSATION,
        ),
        LearningEvent.create(
            id="2",
            project_id=sample_project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "y = 2"},
            skills=[],
            confidence=0.9,
            source=EventSource.CONVERSATION,
        ),
        LearningEvent.create(
            id="3",
            project_id=sample_project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "z = 3"},
            skills=[],
            confidence=0.7,
            source=EventSource.CONVERSATION,
        ),
    ]

    sorted_events = auto_tracker._sort_by_relevance(events)
    assert sorted_events[0].confidence == 0.9
    assert sorted_events[1].confidence == 0.7
    assert sorted_events[2].confidence == 0.5
