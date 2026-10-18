"""Demonstration that skill detection meets all task requirements."""

from learnloop.capture.skill_mapper import detect_skills_in_code


def test_task_requirements_demo():
    """Demonstrate all task requirements are met.
    
    Task 6.3 Requirements:
    - Create detect_skills_in_code() function ✓
    - Pattern matching for common frameworks and libraries ✓
    - AST-based analysis for language constructs ✓
    - Return list of skill tags with confidence ✓
    - Requirements: 3.4 (identify associated skills from code patterns) ✓
    """
    
    # Example: Complex Python code with multiple patterns
    code = """
from fastapi import FastAPI
from sqlalchemy.orm import Session
import pytest

app = FastAPI()

class UserRepository:
    '''Repository pattern for user data access.'''
    
    @staticmethod
    async def get_user(db: Session, user_id: int):
        with db.begin():
            user = await db.execute(
                select(User).where(User.id == user_id)
            )
            return user.scalar_one_or_none()
    
    async def create_user(self, db: Session, name: str):
        user = User(name=name)
        db.add(user)
        await db.commit()
        return user

@app.get("/users/{user_id}")
async def read_user(user_id: int, db: Session = Depends(get_db)):
    user = await UserRepository.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

@pytest.fixture
async def test_client():
    async with AsyncClient(app=app) as client:
        yield client

async def test_read_user(test_client):
    response = await test_client.get("/users/1")
    assert response.status_code in [200, 404]
"""
    
    # ✓ Function exists and is callable
    result = detect_skills_in_code(code, "python")
    
    # ✓ Returns list of skill detections
    assert isinstance(result, list)
    assert len(result) > 0
    
    # ✓ Each detection has skill and confidence
    for detection in result:
        assert "skill" in detection
        assert "confidence" in detection
        assert isinstance(detection["skill"], str)
        assert isinstance(detection["confidence"], float)
        assert 0.0 <= detection["confidence"] <= 1.0
    
    skill_names = [d["skill"] for d in result]
    
    # ✓ Pattern matching for frameworks (FastAPI, SQLAlchemy, pytest)
    assert "python.web.fastapi" in skill_names, "Should detect FastAPI framework"
    assert "databases.orm.sqlalchemy" in skill_names, "Should detect SQLAlchemy ORM"
    assert "python.testing" in skill_names, "Should detect pytest framework"
    
    # ✓ AST-based analysis for language constructs
    assert "python.oop" in skill_names, "Should detect class definitions via AST"
    assert "python.async" in skill_names, "Should detect async functions via AST"
    assert "python.decorators" in skill_names, "Should detect decorators via AST"
    assert "python.context-managers" in skill_names, "Should detect context managers via AST"
    
    # ✓ Pattern matching for common patterns (API, error handling)
    assert "web.api" in skill_names, "Should detect API endpoint patterns"
    
    print("\n✓ All task requirements verified:")
    print(f"  - Function created: detect_skills_in_code()")
    print(f"  - Pattern matching: {sum(1 for s in skill_names if 'web' in s or 'testing' in s or 'databases' in s)} framework/library patterns detected")
    print(f"  - AST analysis: {sum(1 for s in skill_names if any(x in s for x in ['oop', 'decorators', 'context', 'async']))} language constructs detected")
    print(f"  - Returns skill tags with confidence: {len(result)} skills with confidence scores")
    print(f"\nDetected skills:")
    for detection in result[:10]:  # Show top 10
        print(f"  - {detection['skill']}: {detection['confidence']:.2f}")


def test_requirement_3_4_compliance():
    """Verify compliance with Requirement 3.4.
    
    Requirement 3.4: "WHEN detecting learning events, THE Auto_Tracker 
    SHALL identify associated skills from code patterns"
    """
    
    # Test various code patterns
    test_cases = [
        ("async def fetch(): await api()", "python.async"),
        ("@app.get('/api')\ndef endpoint(): pass", "web.api"),
        ("import pytest\ndef test_it(): assert True", "python.testing"),
        ("SELECT * FROM users JOIN orders", "databases.sql.joins"),
        ("class Animal:\n    pass", "python.oop"),
    ]
    
    for code, expected_skill in test_cases:
        skills = detect_skills_in_code(code)
        skill_names = [s["skill"] for s in skills]
        assert expected_skill in skill_names, f"Should detect {expected_skill} from pattern"
    
    print("\n✓ Requirement 3.4 verified: Skills identified from code patterns")


if __name__ == "__main__":
    test_task_requirements_demo()
    test_requirement_3_4_compliance()
    print("\n✅ Task 6.3 implementation complete and verified!")
