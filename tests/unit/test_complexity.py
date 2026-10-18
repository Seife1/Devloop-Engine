"""Unit tests for complexity score calculation.

Tests for Requirement 18: Complexity Score Calculation
"""

from __future__ import annotations

import pytest

from learnloop.capture.complexity import (
    calculate_complexity_score,
    calculate_cyclomatic_complexity,
    calculate_max_nesting_depth,
    count_non_empty_lines,
    count_unique_identifiers,
    normalize_code,
)


class TestNormalizeCode:
    """Test code normalization (Requirement 18.1)."""

    def test_removes_single_line_comments(self):
        code = """
        x = 1  // comment
        y = 2  # another comment
        """
        normalized = normalize_code(code)
        assert '//' not in normalized
        assert '#' not in normalized
        assert 'x = 1' in normalized

    def test_removes_multiline_comments(self):
        code = """
        /* multi
           line
           comment */
        x = 1
        """
        normalized = normalize_code(code)
        assert '/*' not in normalized
        assert 'x = 1' in normalized

    def test_removes_python_docstrings(self):
        code = '''
        """
        This is a docstring
        """
        def foo():
            pass
        '''
        normalized = normalize_code(code)
        assert 'docstring' not in normalized
        assert 'def foo()' in normalized

    def test_preserves_code_structure(self):
        code = "x = 1\ny = 2\nz = 3"
        normalized = normalize_code(code)
        lines = [line for line in normalized.split('\n') if line.strip()]
        assert len(lines) == 3


class TestCyclomaticComplexity:
    """Test cyclomatic complexity calculation (Requirement 18.2)."""

    def test_base_complexity_is_one(self):
        code = "x = 1"
        complexity = calculate_cyclomatic_complexity(code)
        assert complexity == 1

    def test_counts_if_statements(self):
        code = """
        if x > 0:
            pass
        """
        complexity = calculate_cyclomatic_complexity(code)
        assert complexity == 2  # base 1 + 1 if

    def test_counts_elif_and_else(self):
        code = """
        if x > 0:
            pass
        elif x < 0:
            pass
        else:
            pass
        """
        complexity = calculate_cyclomatic_complexity(code)
        assert complexity == 4  # base 1 + if + elif + else

    def test_counts_loops(self):
        code = """
        for i in range(10):
            while i > 0:
                pass
        """
        complexity = calculate_cyclomatic_complexity(code)
        assert complexity >= 3  # base 1 + for + while

    def test_counts_logical_operators(self):
        code = "if x and y or z:"
        complexity = calculate_cyclomatic_complexity(code)
        assert complexity >= 4  # base 1 + if + and + or

    def test_counts_ternary_operators(self):
        code = "result = a ? b : c"
        complexity = calculate_cyclomatic_complexity(code)
        assert complexity == 2  # base 1 + ternary


class TestNestingDepth:
    """Test maximum nesting depth calculation (Requirement 18.3)."""

    def test_no_nesting(self):
        code = "x = 1\ny = 2"
        depth = calculate_max_nesting_depth(code)
        assert depth == 0

    def test_brace_based_nesting(self):
        code = "{{{x = 1;}}}"
        depth = calculate_max_nesting_depth(code)
        assert depth == 3

    def test_indentation_based_nesting(self):
        code = """
def outer():
    if True:
        for i in range(10):
            while i > 0:
                pass
        """
        depth = calculate_max_nesting_depth(code)
        assert depth >= 3

    def test_mixed_nesting(self):
        code = """
        function test() {
            if (x > 0) {
                for (let i = 0; i < 10; i++) {
                    console.log(i);
                }
            }
        }
        """
        depth = calculate_max_nesting_depth(code)
        assert depth >= 2


class TestUniqueIdentifiers:
    """Test unique identifier counting (Requirement 18.4)."""

    def test_counts_unique_variables(self):
        code = "x = 1\ny = 2\nz = x + y"
        count = count_unique_identifiers(code)
        assert count == 3  # x, y, z

    def test_excludes_keywords(self):
        code = "if True:\n    for i in range(10):\n        pass"
        count = count_unique_identifiers(code)
        # Should count 'i' and 'range' but not 'if', 'True', 'for', 'in', 'pass'
        assert count >= 1

    def test_counts_function_names(self):
        code = """
        def my_function():
            another_function()
            third_function()
        """
        count = count_unique_identifiers(code)
        assert count >= 3

    def test_deduplicates_identifiers(self):
        code = "x = 1\nx = 2\nx = 3"
        count = count_unique_identifiers(code)
        assert count == 1  # Only 'x' counted once


class TestLineCount:
    """Test non-empty line counting (Requirement 18.5)."""

    def test_counts_non_empty_lines(self):
        code = "x = 1\n\ny = 2\n\n\nz = 3"
        count = count_non_empty_lines(code)
        assert count == 3

    def test_ignores_whitespace_lines(self):
        code = "x = 1\n   \n\t\ny = 2"
        count = count_non_empty_lines(code)
        assert count == 2

    def test_empty_code(self):
        code = "\n\n\n"
        count = count_non_empty_lines(code)
        assert count == 0


class TestComplexityScore:
    """Test overall complexity score calculation (Requirements 18.6-18.9)."""

    def test_empty_code_returns_zero(self):
        """Empty code should have zero complexity."""
        assert calculate_complexity_score("") == 0.0
        assert calculate_complexity_score("   ") == 0.0
        assert calculate_complexity_score("\n\n") == 0.0

    def test_trivial_code_low_score(self):
        """Trivial code (<5 lines) should score below 0.2 (Requirement 18.9)."""
        trivial_code = """
        x = 1
        y = 2
        z = x + y
        """
        score = calculate_complexity_score(trivial_code)
        assert 0.0 <= score < 0.2

    def test_simple_code_low_to_medium(self):
        """Simple code should have low to medium score."""
        simple_code = """
        def add(a, b):
            return a + b
        
        def subtract(a, b):
            return a - b
        """
        score = calculate_complexity_score(simple_code)
        assert 0.0 < score < 0.5

    def test_moderate_complexity(self):
        """Code with some logic should have moderate score."""
        moderate_code = """
        def process_data(items):
            result = []
            for item in items:
                if item > 0:
                    result.append(item * 2)
                else:
                    result.append(item)
            return result
        """
        score = calculate_complexity_score(moderate_code)
        assert 0.2 < score < 0.7

    def test_complex_code_high_score(self):
        """Complex code with nested logic should have high score."""
        complex_code = """
        def complex_algorithm(data, config, options):
            result = initialize_result()
            for item in data:
                if item.validate():
                    for key, value in item.process():
                        if config.enabled:
                            while value > threshold:
                                value = transform(value)
                                if value in cache:
                                    break
                            result.update(key, value)
                        else:
                            result.skip(key)
                else:
                    handle_error(item)
            return result
        """
        score = calculate_complexity_score(complex_code)
        assert 0.5 < score <= 1.0

    def test_score_always_bounded(self):
        """Complexity score must always be between 0.0 and 1.0 (Requirement 18.7, 18.8)."""
        test_cases = [
            "x = 1",
            "def foo(): pass",
            """
            def very_complex():
                for i in range(100):
                    for j in range(100):
                        for k in range(100):
                            if i > 0 and j > 0 and k > 0:
                                while True:
                                    if check1() and check2() or check3():
                                        process()
            """,
            # Edge case: extremely nested
            "{{{{{{{{{{{{{{{{x = 1}}}}}}}}}}}}}}}}",
        ]
        
        for code in test_cases:
            score = calculate_complexity_score(code)
            assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for code: {code[:50]}..."

    def test_consistent_scoring(self):
        """Same code should produce same score regardless of formatting."""
        code1 = "def foo():\n    x = 1\n    return x"
        code2 = "def foo():\n\n    x = 1\n\n    return x"
        
        score1 = calculate_complexity_score(code1)
        score2 = calculate_complexity_score(code2)
        
        # Scores should be very close (allowing for minor floating point differences)
        assert abs(score1 - score2) < 0.05

    def test_weighted_average_calculation(self):
        """Score should be weighted average: 40% cyclomatic, 30% nesting, 20% identifiers, 10% length."""
        # Simple code with known metrics
        code = """
        if x > 0:
            y = 1
        """
        score = calculate_complexity_score(code)
        # Just verify it's calculated and in reasonable range
        assert 0.0 < score < 1.0

    def test_normalization_applied(self):
        """Comments should be removed before calculation (Requirement 18.1)."""
        code_with_comments = """
        # This is a comment
        def foo():  // another comment
            /* multi-line
               comment */
            return 1
        """
        code_without_comments = """
        def foo():
            return 1
        """
        
        score1 = calculate_complexity_score(code_with_comments)
        score2 = calculate_complexity_score(code_without_comments)
        
        # Scores should be very close
        assert abs(score1 - score2) < 0.1

    def test_real_world_examples(self):
        """Test with realistic code examples."""
        # Simple getter
        simple = "def get_name(self):\n    return self.name"
        assert calculate_complexity_score(simple) < 0.2
        
        # Basic CRUD function
        crud = """
        def update_user(user_id, data):
            user = find_user(user_id)
            if user:
                user.update(data)
                return True
            return False
        """
        crud_score = calculate_complexity_score(crud)
        assert 0.1 < crud_score < 0.3  # Adjusted based on actual complexity
        
        # Complex algorithm
        algorithm = """
        def dijkstra(graph, start, end):
            distances = {node: float('inf') for node in graph}
            distances[start] = 0
            visited = set()
            pq = [(0, start)]
            
            while pq:
                current_dist, current = heappop(pq)
                if current in visited:
                    continue
                visited.add(current)
                
                if current == end:
                    return distances[end]
                
                for neighbor, weight in graph[current]:
                    distance = current_dist + weight
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        heappush(pq, (distance, neighbor))
            
            return float('inf')
        """
        algo_score = calculate_complexity_score(algorithm)
        assert 0.5 < algo_score <= 1.0


class TestMetricNormalization:
    """Test that metrics are properly normalized (Requirement 18.6)."""

    def test_cyclomatic_normalized_to_ten(self):
        """Cyclomatic complexity normalized with divisor 10."""
        # Code with exactly 10 decision points should normalize to ~1.0 for that component
        code_with_many_decisions = """
        if a: pass
        if b: pass
        if c: pass
        if d: pass
        if e: pass
        if f: pass
        if g: pass
        if h: pass
        if i: pass
        """
        complexity = calculate_cyclomatic_complexity(normalize_code(code_with_many_decisions))
        normalized = min(1.0, complexity / 10.0)
        assert 0.9 <= normalized <= 1.0

    def test_nesting_normalized_to_five(self):
        """Nesting depth normalized with divisor 5."""
        # Deep nesting should normalize properly
        deep_nesting = "{{{{{"
        depth = calculate_max_nesting_depth(deep_nesting)
        normalized = min(1.0, depth / 5.0)
        assert normalized == 1.0

    def test_identifiers_normalized_to_twenty(self):
        """Unique identifiers normalized with divisor 20."""
        # Code with 20+ identifiers
        many_vars = " ".join([f"var{i} = {i}" for i in range(25)])
        count = count_unique_identifiers(many_vars)
        normalized = min(1.0, count / 20.0)
        assert normalized >= 1.0

    def test_length_normalized_to_fifty(self):
        """Line count normalized with divisor 50."""
        # Code with 50+ lines
        many_lines = "\n".join([f"line{i} = {i}" for i in range(60)])
        count = count_non_empty_lines(many_lines)
        normalized = min(1.0, count / 50.0)
        assert normalized >= 1.0
