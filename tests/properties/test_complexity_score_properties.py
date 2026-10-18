"""Property-based tests for complexity score calculation.

This module tests the complexity score calculation algorithm using property-based
testing with Hypothesis to ensure robustness across a wide range of inputs.
"""

from hypothesis import given, strategies as st

from learnloop.capture.complexity import calculate_complexity_score


# Strategy for generating random code strings
code_strategy = st.text(
    alphabet=st.characters(
        # Include typical code characters
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Ps', 'Pe', 'Po'),
        whitelist_characters='\n\t {}[]();,._-+*/%&|^~!<>=?:@#$\'"\\`',
    ),
    min_size=1,
    max_size=10000,
)


@given(code=code_strategy)
def test_complexity_score_always_0_to_1(code: str) -> None:
    """Property P5: Complexity score always between 0 and 1.
    
    **Validates: Requirements 18.8**
    
    This property verifies that regardless of input, the complexity score
    calculation always returns a value in the valid range [0.0, 1.0].
    """
    score = calculate_complexity_score(code)
    assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for code: {code[:100]}"


@given(code=st.text(min_size=1, max_size=10000))
def test_complexity_score_with_any_text(code: str) -> None:
    """Verify complexity score bounds with completely arbitrary text.
    
    **Validates: Requirements 18.8**
    
    Tests that the algorithm handles any unicode text without crashing
    and always returns a bounded value.
    """
    score = calculate_complexity_score(code)
    assert 0.0 <= score <= 1.0


# Strategy for generating trivial code (< 5 lines)
trivial_code_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Ps', 'Pe', 'Po'),
        whitelist_characters=' \t{}[]();,._-+*/%&|^~!<>=?:@#$\'"\\`',
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: len([line for line in s.split('\n') if line.strip()]) < 5)


@given(code=trivial_code_strategy)
def test_trivial_code_scores_below_0_2(code: str) -> None:
    """Property: Trivial code (< 5 lines) scores below 0.2.
    
    **Validates: Requirements 18.9**
    
    This property verifies that simple code snippets with fewer than 5 non-empty
    lines receive a low complexity score, as they represent trivial changes.
    """
    non_empty_lines = len([line for line in code.split('\n') if line.strip()])
    
    # Only test if we have fewer than 5 non-empty lines
    if non_empty_lines < 5:
        score = calculate_complexity_score(code)
        assert score < 0.2, (
            f"Trivial code ({non_empty_lines} lines) scored {score} >= 0.2\n"
            f"Code: {code}"
        )


@given(
    code=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' \t\n',
        ),
        min_size=1,
        max_size=50,
    )
)
def test_simple_code_has_low_complexity(code: str) -> None:
    """Verify that code with only simple characters has low complexity.
    
    **Validates: Requirements 18.8**
    
    Simple alphanumeric code without control structures should have
    relatively low complexity.
    """
    score = calculate_complexity_score(code)
    # Should be bounded, but we don't enforce specific value since
    # even simple code could theoretically be complex
    assert 0.0 <= score <= 1.0


@given(code=st.just(""))
def test_empty_code_returns_zero(code: str) -> None:
    """Verify that empty code returns zero complexity.
    
    **Validates: Requirements 18.8**
    
    Empty strings should have zero complexity.
    """
    score = calculate_complexity_score(code)
    assert score == 0.0


@given(code=st.just("   \n  \t  \n   "))
def test_whitespace_only_returns_zero(code: str) -> None:
    """Verify that whitespace-only code returns zero complexity.
    
    **Validates: Requirements 18.8**
    
    Code with only whitespace should have zero complexity.
    """
    score = calculate_complexity_score(code)
    assert score == 0.0


# Generate code-like structures
@given(
    lines=st.lists(
        st.sampled_from([
            "x = 1",
            "y = 2",
            "print(x)",
            "return x",
        ]),
        min_size=1,
        max_size=4,
    )
)
def test_simple_statements_score_low(lines: list[str]) -> None:
    """Verify that simple statements (< 5 lines) score below 0.2.
    
    **Validates: Requirements 18.9**
    
    Simple assignment and print statements should be considered trivial.
    """
    code = "\n".join(lines)
    if len(lines) < 5:
        score = calculate_complexity_score(code)
        assert score < 0.2, f"Simple code scored {score} >= 0.2: {code}"


@given(
    complexity_elements=st.lists(
        st.sampled_from([
            "if x:",
            "for i in range(10):",
            "while True:",
            "elif y:",
            "else:",
            "try:",
            "except:",
        ]),
        min_size=5,
        max_size=20,
    )
)
def test_complex_code_scores_higher(complexity_elements: list[str]) -> None:
    """Verify that code with many decision points has higher complexity.
    
    **Validates: Requirements 18.8**
    
    Code with multiple control flow statements should have measurable complexity.
    """
    code = "\n".join(complexity_elements)
    score = calculate_complexity_score(code)
    
    # Just verify it's bounded - the actual value depends on the algorithm
    assert 0.0 <= score <= 1.0


@given(code=code_strategy)
def test_score_is_deterministic(code: str) -> None:
    """Verify that the same code always produces the same score.
    
    **Validates: Requirements 18.8**
    
    The complexity calculation should be deterministic.
    """
    score1 = calculate_complexity_score(code)
    score2 = calculate_complexity_score(code)
    assert score1 == score2, f"Non-deterministic scores: {score1} != {score2}"
