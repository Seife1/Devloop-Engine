"""Unit tests for skill detection from code."""

import pytest

from learnloop.capture.skill_mapper import detect_skills_in_code


class TestDetectSkillsInCode:
    """Test suite for detect_skills_in_code function."""
    
    def test_empty_code_returns_empty_list(self):
        """Empty or whitespace-only code should return no skills."""
        assert detect_skills_in_code("") == []
        assert detect_skills_in_code("   ") == []
        assert detect_skills_in_code("\n\n") == []
    
    def test_python_basic_detection(self):
        """Detect basic Python language from simple code."""
        code = """
def hello():
    return "world"
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python" in skill_names
        assert all(0.0 <= s["confidence"] <= 1.0 for s in skills)
    
    def test_python_auto_detection(self):
        """Auto-detect Python from code patterns."""
        code = """
import os
from pathlib import Path

def process_file(path: str) -> None:
    pass
"""
        skills = detect_skills_in_code(code)  # No language hint
        skill_names = [s["skill"] for s in skills]
        
        assert "python" in skill_names
    
    def test_python_testing_patterns(self):
        """Detect Python testing frameworks."""
        code = """
import pytest

def test_addition():
    assert 1 + 1 == 2

def test_with_fixture(mock_data):
    assert mock_data is not None
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.testing" in skill_names
        
        # Check confidence scores are reasonable
        testing_skill = next(s for s in skills if s["skill"] == "python.testing")
        assert testing_skill["confidence"] >= 0.8
    
    def test_python_mocking_patterns(self):
        """Detect Python mocking usage."""
        code = """
from unittest.mock import Mock, patch, MagicMock

def test_with_mock():
    mock_obj = Mock()
    with patch('module.function') as patched:
        patched.return_value = 42
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.testing.mocking" in skill_names
    
    def test_python_fastapi_detection(self):
        """Detect FastAPI framework."""
        code = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.web.fastapi" in skill_names
        assert "python.async" in skill_names
    
    def test_python_async_detection(self):
        """Detect async Python patterns."""
        code = """
async def fetch_data():
    result = await api_call()
    return result
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.async" in skill_names
    
    def test_python_database_patterns(self):
        """Detect database-related skills."""
        code = """
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "databases.orm.sqlalchemy" in skill_names
    
    def test_python_ast_class_detection(self):
        """Detect OOP patterns using AST."""
        code = """
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.oop" in skill_names
    
    def test_python_ast_decorators(self):
        """Detect decorator usage via AST."""
        code = """
@property
def name(self):
    return self._name

@staticmethod
def create():
    return MyClass()
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.decorators" in skill_names
    
    def test_python_ast_generators(self):
        """Detect generator functions via AST."""
        code = """
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.generators" in skill_names
    
    def test_python_ast_context_managers(self):
        """Detect context manager usage via AST."""
        code = """
def process_file():
    with open('file.txt', 'r') as f:
        data = f.read()
    return data
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.context-managers" in skill_names
    
    def test_python_ast_comprehensions(self):
        """Detect list/dict comprehensions via AST."""
        code = """
numbers = [x * 2 for x in range(10)]
squares = {x: x**2 for x in range(5)}
unique = {x for x in numbers}
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "python.comprehensions" in skill_names
    
    def test_javascript_detection(self):
        """Detect JavaScript language."""
        code = """
function greet(name) {
    return `Hello, ${name}`;
}

const add = (a, b) => a + b;
"""
        skills = detect_skills_in_code(code)
        skill_names = [s["skill"] for s in skills]
        
        assert "javascript" in skill_names
    
    def test_typescript_detection(self):
        """Detect TypeScript from type annotations."""
        code = """
interface User {
    name: string;
    age: number;
}

function greet(user: User): string {
    return `Hello, ${user.name}`;
}
"""
        skills = detect_skills_in_code(code)
        skill_names = [s["skill"] for s in skills]
        
        assert "typescript" in skill_names
    
    def test_javascript_testing_patterns(self):
        """Detect JavaScript testing frameworks."""
        code = """
describe('Calculator', () => {
    it('should add two numbers', () => {
        expect(add(2, 3)).toBe(5);
    });
    
    test('subtraction works', () => {
        expect(subtract(5, 3)).toBe(2);
    });
});
"""
        skills = detect_skills_in_code(code, "javascript")
        skill_names = [s["skill"] for s in skills]
        
        assert "javascript.testing" in skill_names
    
    def test_javascript_react_patterns(self):
        """Detect React framework."""
        code = """
import React, { useState, useEffect } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    
    useEffect(() => {
        document.title = `Count: ${count}`;
    }, [count]);
    
    return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
"""
        skills = detect_skills_in_code(code, "javascript")
        skill_names = [s["skill"] for s in skills]
        
        assert "javascript.react" in skill_names
    
    def test_javascript_async_patterns(self):
        """Detect JavaScript async patterns."""
        code = """
async function fetchData() {
    try {
        const response = await fetch('/api/data');
        return await response.json();
    } catch (error) {
        console.error(error);
    }
}

function oldStyle() {
    return promise.then(data => data).catch(err => console.error(err));
}
"""
        skills = detect_skills_in_code(code, "javascript")
        skill_names = [s["skill"] for s in skills]
        
        assert "javascript.async" in skill_names
    
    def test_sql_detection(self):
        """Detect SQL language."""
        code = """
SELECT users.name, orders.total
FROM users
INNER JOIN orders ON users.id = orders.user_id
WHERE orders.total > 100
ORDER BY orders.total DESC;
"""
        skills = detect_skills_in_code(code)
        skill_names = [s["skill"] for s in skills]
        
        assert "sql" in skill_names
    
    def test_sql_joins_detection(self):
        """Detect SQL join patterns."""
        code = """
SELECT * FROM users
LEFT JOIN profiles ON users.id = profiles.user_id
INNER JOIN orders ON users.id = orders.user_id;
"""
        skills = detect_skills_in_code(code, "sql")
        skill_names = [s["skill"] for s in skills]
        
        assert "databases.sql.joins" in skill_names
    
    def test_sql_transactions_detection(self):
        """Detect SQL transaction patterns."""
        code = """
BEGIN TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
"""
        skills = detect_skills_in_code(code, "sql")
        skill_names = [s["skill"] for s in skills]
        
        assert "databases.transactions" in skill_names
    
    def test_authentication_patterns(self):
        """Detect authentication/security patterns."""
        code = """
def login(username, password):
    hashed = hash_password(password)
    token = generate_jwt(username)
    return {"token": token, "authenticated": True}
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "security.auth" in skill_names
    
    def test_api_patterns(self):
        """Detect API/endpoint patterns."""
        code = """
@app.post("/api/users")
def create_user(user: User):
    return db.create(user)

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    return db.get(user_id)
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "web.api" in skill_names
    
    def test_error_handling_patterns(self):
        """Detect error handling patterns."""
        code = """
try:
    risky_operation()
except ValueError as e:
    log_error(e)
except Exception:
    handle_generic_error()
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        assert "error-handling" in skill_names
    
    def test_confidence_scores_valid(self):
        """All confidence scores should be between 0.0 and 1.0."""
        code = """
import pytest
from fastapi import FastAPI

async def test_endpoint():
    assert True
"""
        skills = detect_skills_in_code(code, "python")
        
        for skill in skills:
            assert 0.0 <= skill["confidence"] <= 1.0
    
    def test_skills_sorted_by_confidence(self):
        """Skills should be sorted by confidence descending."""
        code = """
from fastapi import FastAPI
import pytest

app = FastAPI()

async def test_app():
    assert app is not None
"""
        skills = detect_skills_in_code(code, "python")
        
        # Check that confidences are in descending order
        confidences = [s["confidence"] for s in skills]
        assert confidences == sorted(confidences, reverse=True)
    
    def test_multiple_detection_methods_combine(self):
        """Pattern and AST detection should combine for higher confidence."""
        code = """
import pytest

@pytest.fixture
def mock_data():
    return {"key": "value"}

class TestAPI:
    def test_endpoint(self, mock_data):
        assert mock_data is not None
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        # Should detect from both patterns and AST
        assert "python.testing" in skill_names
        assert "python.oop" in skill_names
        assert "python.decorators" in skill_names
    
    def test_invalid_python_syntax_graceful(self):
        """Invalid Python syntax should not crash AST analysis."""
        code = """
def broken_function(
    # Missing closing paren
"""
        # Should not raise exception
        skills = detect_skills_in_code(code, "python")
        
        # May still detect some patterns
        assert isinstance(skills, list)
    
    def test_mixed_patterns_in_complex_code(self):
        """Complex code with multiple patterns should detect all relevant skills."""
        code = """
from fastapi import FastAPI
from sqlalchemy.orm import Session
import pytest

app = FastAPI()

class UserService:
    @staticmethod
    async def create_user(db: Session, name: str):
        with db.begin():
            user = User(name=name)
            db.add(user)
            await db.commit()
        return user

@pytest.fixture
async def test_create_user():
    async with TestClient(app) as client:
        response = await client.post("/users", json={"name": "Alice"})
        assert response.status_code == 201
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        # Should detect multiple skills
        assert "python" in skill_names
        assert "python.web.fastapi" in skill_names
        assert "python.async" in skill_names
        assert "databases.orm.sqlalchemy" in skill_names
        assert "python.testing" in skill_names
        assert "python.oop" in skill_names
        assert "python.decorators" in skill_names
        assert "python.context-managers" in skill_names
    
    def test_no_duplicate_skills(self):
        """Each skill should appear at most once in results."""
        code = """
async def func1():
    await something()

async def func2():
    await another()

async def func3():
    await third()
"""
        skills = detect_skills_in_code(code, "python")
        skill_names = [s["skill"] for s in skills]
        
        # Check no duplicates
        assert len(skill_names) == len(set(skill_names))
    
    def test_max_confidence_from_multiple_sources(self):
        """When same skill detected multiple ways, use max confidence."""
        code = """
async def test_async():
    result = await async_operation()
    assert result is not None
"""
        skills = detect_skills_in_code(code, "python")
        
        # async detected from both pattern and AST
        async_skills = [s for s in skills if s["skill"] == "python.async"]
        assert len(async_skills) == 1  # Should be deduplicated
        assert async_skills[0]["confidence"] >= 0.85  # Should have high confidence
