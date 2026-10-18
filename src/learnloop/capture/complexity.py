"""Complexity score calculation for code blocks.

Implements Requirement 18: Complexity Score Calculation
Calculates a complexity score between 0.0 and 1.0 based on:
- Cyclomatic complexity (40% weight)
- Maximum nesting depth (30% weight)
- Unique identifiers (20% weight)
- Line count (10% weight)
"""

from __future__ import annotations

import re
from typing import Pattern


def normalize_code(code: str) -> str:
    """Normalize code by removing comments and excess whitespace.
    
    Args:
        code: Raw source code string
        
    Returns:
        Normalized code with comments and excess whitespace removed
    """
    # Remove single-line comments (// and #)
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    code = re.sub(r'#.*?$', '', code, flags=re.MULTILINE)
    
    # Remove multi-line comments (/* */ and """ """)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
    
    # Remove excess whitespace but preserve line structure
    lines = code.split('\n')
    normalized_lines = [line.strip() for line in lines]
    
    return '\n'.join(normalized_lines)


def calculate_cyclomatic_complexity(code: str) -> int:
    """Calculate cyclomatic complexity by counting decision points.
    
    Counts: if, elif, else, for, while, case, catch, and, or, ?, &&, ||
    
    Args:
        code: Normalized source code
        
    Returns:
        Cyclomatic complexity count (starts at 1)
    """
    complexity = 1  # Base complexity
    
    # Decision keywords
    keywords = [
        r'\bif\b', r'\belif\b', r'\belse\b',
        r'\bfor\b', r'\bwhile\b', 
        r'\bcase\b', r'\bcatch\b',
        r'\band\b', r'\bor\b',
    ]
    
    # Operators
    operators = [
        r'\?',      # Ternary operator
        r'&&',      # Logical AND
        r'\|\|',    # Logical OR
    ]
    
    for pattern in keywords + operators:
        complexity += len(re.findall(pattern, code))
    
    return complexity


def calculate_max_nesting_depth(code: str) -> int:
    """Calculate maximum nesting depth by tracking braces and indentation.
    
    Args:
        code: Normalized source code
        
    Returns:
        Maximum nesting depth
    """
    max_depth = 0
    current_depth = 0
    
    # Count brace-based nesting (C-like languages)
    brace_depth = 0
    max_brace_depth = 0
    
    for char in code:
        if char == '{':
            brace_depth += 1
            max_brace_depth = max(max_brace_depth, brace_depth)
        elif char == '}':
            brace_depth = max(0, brace_depth - 1)
    
    # Count indentation-based nesting (Python-like languages)
    indent_depth = 0
    max_indent_depth = 0
    
    lines = code.split('\n')
    for line in lines:
        if not line or line.isspace():
            continue
        
        # Count leading spaces/tabs
        leading_ws = len(line) - len(line.lstrip())
        # Assume 4 spaces or 1 tab = 1 level
        if '\t' in line[:leading_ws]:
            depth = line[:leading_ws].count('\t')
        else:
            depth = leading_ws // 4
        
        max_indent_depth = max(max_indent_depth, depth)
    
    # Return the greater of the two methods
    return max(max_brace_depth, max_indent_depth)


def count_unique_identifiers(code: str) -> int:
    """Count unique variable/function names in the code.
    
    Args:
        code: Normalized source code
        
    Returns:
        Count of unique identifiers
    """
    # Match valid identifiers (alphanumeric + underscore, starting with letter or underscore)
    identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    identifiers = re.findall(identifier_pattern, code)
    
    # Filter out common keywords to avoid counting them
    keywords = {
        'if', 'else', 'elif', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue',
        'return', 'def', 'class', 'function', 'const', 'let', 'var', 'import', 'from',
        'try', 'catch', 'finally', 'throw', 'new', 'this', 'self', 'true', 'false',
        'null', 'undefined', 'None', 'True', 'False', 'and', 'or', 'not', 'in', 'is',
        'async', 'await', 'yield', 'lambda', 'with', 'as', 'pass', 'assert', 'del',
        'raise', 'except', 'public', 'private', 'protected', 'static', 'final', 'abstract',
        'interface', 'extends', 'implements', 'package', 'enum', 'struct', 'typedef',
    }
    
    unique_identifiers = {ident for ident in identifiers if ident.lower() not in keywords}
    
    return len(unique_identifiers)


def count_non_empty_lines(code: str) -> int:
    """Count non-empty lines in normalized code.
    
    Args:
        code: Normalized source code
        
    Returns:
        Count of non-empty lines
    """
    lines = code.split('\n')
    non_empty = [line for line in lines if line.strip()]
    return len(non_empty)


def calculate_complexity_score(code: str) -> float:
    """Calculate overall complexity score for a code block.
    
    Implements Requirement 18: Complexity Score Calculation
    
    The score is computed as a weighted average of:
    - Cyclomatic complexity (40% weight)
    - Maximum nesting depth (30% weight)
    - Unique identifiers (20% weight)
    - Line count (10% weight)
    
    Each metric is normalized to 0-1 scale before weighting.
    
    Args:
        code: Source code string to analyze
        
    Returns:
        Float between 0.0 (trivial) and 1.0 (highly complex)
        
    Postconditions:
        - Return value is between 0.0 and 1.0 inclusive
        - Trivial code (<5 lines) scores below 0.2
        - Consistent scoring for same code regardless of formatting
    """
    if not code or not code.strip():
        return 0.0
    
    # Normalize code (remove comments, whitespace)
    normalized = normalize_code(code)
    
    if not normalized.strip():
        return 0.0
    
    # Calculate component metrics
    cyclomatic = calculate_cyclomatic_complexity(normalized)
    nesting = calculate_max_nesting_depth(normalized)
    unique_identifiers = count_unique_identifiers(normalized)
    line_count = count_non_empty_lines(normalized)
    
    # Normalize each metric to 0-1 scale
    # Using thresholds based on design spec
    cyclomatic_score = min(1.0, cyclomatic / 10.0)
    nesting_score = min(1.0, nesting / 5.0)
    identifier_score = min(1.0, unique_identifiers / 20.0)
    length_score = min(1.0, line_count / 50.0)
    
    # Weighted average (40%, 30%, 20%, 10%)
    complexity_score = (
        cyclomatic_score * 0.4 +
        nesting_score * 0.3 +
        identifier_score * 0.2 +
        length_score * 0.1
    )
    
    # Ensure bounds
    complexity_score = max(0.0, min(1.0, complexity_score))
    
    return complexity_score
