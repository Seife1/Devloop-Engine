"""Suggest skills for changed files. Used to help the agent explain an 'unexplained' commit;
suggestions NEVER create exposure on their own."""

from __future__ import annotations

import ast
import re
import sqlite3
from typing import TypedDict


class SkillDetection(TypedDict):
    """Detected skill with confidence score."""
    skill: str
    confidence: float


def _rules(path: str) -> list[str]:
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    out: list[str] = []
    if p.endswith(".py"):
        out.append("python")
        if name.startswith("test_") or name.endswith("_test.py") or "/tests/" in f"/{p}":
            out.append("python.testing")
        if name == "conftest.py":
            out.append("python.testing.fixtures")
    if p.endswith((".ts", ".tsx")):
        out.append("typescript")
    if p.endswith((".js", ".jsx", ".mjs")):
        out.append("javascript")
    if p.endswith(".sql"):
        out.append("databases.sql")
    if "migration" in p or "alembic" in p:
        out.append("databases.migrations")
    if name == "dockerfile" or name.startswith("docker-compose"):
        out.append("devops.docker")
    if p.startswith(".github/workflows/"):
        out.append("devops.ci")
    if name in ("pyproject.toml", "setup.py", "setup.cfg"):
        out.append("python.packaging")
    if "auth" in p or "login" in p:
        out.append("web.auth")
    return out


def suggest_skills(conn: sqlite3.Connection, files: list[str]) -> list[str]:
    known = {r["id"] for r in conn.execute("SELECT id FROM skills")}
    found: list[str] = []
    for f in files:
        for s in _rules(f):
            if s in known and s not in found:
                found.append(s)
    return found


def get_file_skill_map(files: list[str]) -> dict[str, list[str]]:
    """Map each file path to skills inferred by rule heuristics."""
    return {f: _rules(f) for f in files}


def detect_skills_in_code(code: str, language: str | None = None) -> list[SkillDetection]:
    """Detect skills from code using pattern matching and AST analysis.
    
    Combines:
    - Pattern matching for common frameworks and libraries
    - AST-based analysis for language constructs (Python only)
    - Returns list of skill tags with confidence scores (0.0-1.0)
    
    Args:
        code: Source code string to analyze
        language: Optional language hint (e.g., "python", "javascript", "typescript")
        
    Returns:
        List of detected skills with confidence scores
    """
    if not code or not code.strip():
        return []
    
    # Auto-detect language if not provided
    if language is None:
        language = _detect_language(code)
    
    skills: dict[str, float] = {}  # skill -> max confidence
    
    # Pattern-based detection for all languages
    pattern_skills = _detect_patterns(code, language)
    for skill, confidence in pattern_skills:
        skills[skill] = max(skills.get(skill, 0.0), confidence)
    
    # AST-based analysis for Python
    if language == "python":
        ast_skills = _detect_python_ast_patterns(code)
        for skill, confidence in ast_skills:
            skills[skill] = max(skills.get(skill, 0.0), confidence)
    
    # Convert to list and sort by confidence (descending)
    result = [{"skill": skill, "confidence": conf} for skill, conf in skills.items()]
    result.sort(key=lambda x: x["confidence"], reverse=True)
    
    return result


def _detect_language(code: str) -> str:
    """Auto-detect programming language from code patterns."""
    # Check for Python indicators
    if re.search(r'\bdef\s+\w+\(|^import\s+\w+|^from\s+\w+\s+import|\bclass\s+\w+|async\s+def|await\s+', code, re.MULTILINE):
        return "python"
    
    # Check for TypeScript/JavaScript indicators
    if re.search(r'\bfunction\s+\w+\(|=>|^import\s+.*\s+from\s+[\'"]|^const\s+\w+', code, re.MULTILINE):
        if re.search(r':\s*(string|number|boolean|any|void|interface|type\s+\w+\s*=)', code):
            return "typescript"
        return "javascript"
    
    # Check for SQL
    if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b', code, re.IGNORECASE):
        return "sql"
    
    return "unknown"


def _detect_patterns(code: str, language: str) -> list[tuple[str, float]]:
    """Detect skills using regex pattern matching for frameworks and libraries."""
    detections: list[tuple[str, float]] = []
    code_lower = code.lower()
    
    # Base language skill with medium confidence
    if language in ("python", "javascript", "typescript", "sql"):
        detections.append((language, 0.7))
    
    # Python framework and library patterns
    if language == "python":
        # Testing frameworks
        if re.search(r'\b(pytest|unittest|mock|fixture|assert\s+\w+\s*==)', code):
            detections.append(("python.testing", 0.85))
        if re.search(r'\bMock\(|patch\(|MagicMock', code):
            detections.append(("python.testing.mocking", 0.9))
        
        # Web frameworks
        if re.search(r'from\s+fastapi|import\s+fastapi|@app\.(get|post|put|delete)', code):
            detections.append(("python.web.fastapi", 0.9))
        if re.search(r'from\s+flask|import\s+flask|@app\.route', code):
            detections.append(("python.web.flask", 0.9))
        if re.search(r'from\s+django|import\s+django', code):
            detections.append(("python.web.django", 0.9))
        
        # Async patterns
        if re.search(r'\basync\s+def\b|\bawait\s+\w+', code):
            detections.append(("python.async", 0.85))
        
        # Database patterns
        if re.search(r'sqlalchemy|from\s+sqlalchemy', code_lower):
            detections.append(("databases.orm.sqlalchemy", 0.9))
        if re.search(r'\.execute\(|\.fetchall\(|\.fetchone\(|cursor', code_lower):
            detections.append(("databases.sql", 0.8))
        
        # Data science libraries
        if re.search(r'import\s+pandas|from\s+pandas', code):
            detections.append(("python.data.pandas", 0.9))
        if re.search(r'import\s+numpy|from\s+numpy', code):
            detections.append(("python.data.numpy", 0.9))
    
    # JavaScript/TypeScript patterns
    elif language in ("javascript", "typescript"):
        # Testing frameworks
        if re.search(r'\b(describe|it|test|expect)\s*\(', code):
            detections.append(("javascript.testing", 0.85))
        
        # React patterns
        if re.search(r'import\s+React|from\s+[\'"]react[\'"]|useState|useEffect', code):
            detections.append(("javascript.react", 0.9))
        
        # Node.js patterns
        if re.search(r'require\(|module\.exports|process\.env', code):
            detections.append(("javascript.nodejs", 0.85))
        
        # Async patterns
        if re.search(r'\basync\s+function|\basync\s+\(|\.then\(|\.catch\(|await\s+', code):
            detections.append(("javascript.async", 0.85))
    
    # SQL patterns
    elif language == "sql":
        if re.search(r'\b(JOIN|LEFT JOIN|INNER JOIN|OUTER JOIN)\b', code, re.IGNORECASE):
            detections.append(("databases.sql.joins", 0.9))
        if re.search(r'\b(BEGIN|COMMIT|ROLLBACK|TRANSACTION)\b', code, re.IGNORECASE):
            detections.append(("databases.transactions", 0.9))
    
    # Cross-language patterns
    
    # Authentication/Security
    if re.search(r'jwt|token|auth|login|password|hash|encrypt|decrypt', code_lower):
        detections.append(("security.auth", 0.75))
    
    # API patterns
    if re.search(r'@(get|post|put|delete|patch)|\.get\(|\.post\(|api|endpoint|route', code_lower):
        detections.append(("web.api", 0.75))
    
    # Error handling
    if re.search(r'\btry\s*{|\btry:|\bcatch\s*\(|\bexcept\s+\w+:', code):
        detections.append(("error-handling", 0.8))
    
    return detections


def _detect_python_ast_patterns(code: str) -> list[tuple[str, float]]:
    """Detect Python skills using AST analysis for language constructs."""
    detections: list[tuple[str, float]] = []
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # If code doesn't parse, return empty list
        return []
    
    # Analyze AST nodes
    has_classes = False
    has_decorators = False
    has_generators = False
    has_context_managers = False
    has_comprehensions = False
    has_async = False
    
    for node in ast.walk(tree):
        # Class definitions
        if isinstance(node, ast.ClassDef):
            has_classes = True
            # Check for decorators on classes
            if node.decorator_list:
                has_decorators = True
        
        # Function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Async functions
            if isinstance(node, ast.AsyncFunctionDef):
                has_async = True
            
            # Decorators
            if node.decorator_list:
                has_decorators = True
            
            # Generator functions
            for subnode in ast.walk(node):
                if isinstance(subnode, (ast.Yield, ast.YieldFrom)):
                    has_generators = True
        
        # Context managers (with statement)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            has_context_managers = True
            if isinstance(node, ast.AsyncWith):
                has_async = True
        
        # Comprehensions
        if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            has_comprehensions = True
        
        # Async operations
        if isinstance(node, (ast.Await, ast.AsyncFor)):
            has_async = True
    
    # Add detections based on AST analysis
    if has_classes:
        detections.append(("python.oop", 0.85))
    
    if has_decorators:
        detections.append(("python.decorators", 0.9))
    
    if has_generators:
        detections.append(("python.generators", 0.9))
    
    if has_context_managers:
        detections.append(("python.context-managers", 0.85))
    
    if has_comprehensions:
        detections.append(("python.comprehensions", 0.8))
    
    if has_async:
        detections.append(("python.async", 0.9))
    
    return detections

