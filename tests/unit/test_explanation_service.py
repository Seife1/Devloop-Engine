"""Unit tests for explanation service.

Tests Requirements:
- 8.1: Generate explanation prompts
- 8.2: Extract code snippets (max 50 lines)
- 8.3: Generate depth-appropriate questions (2-4 questions)
- 8.4: Tailor questions to skill complexity
- 8.5: Include self-rating encouragement (1-5 scale)
- 10.3: Analyze explanation text for technical terms
- 10.4: Calculate explanation depth score (0.0-1.0)
- 10.7: Detect low-quality explanations and suggest improvements
"""

from __future__ import annotations

import pytest

from learnloop.services.explanation_service import (
    calculate_explanation_depth,
    generate_explanation_prompt,
    generate_quality_feedback,
)


class TestExplanationPromptGeneration:
    """Test explanation prompt generation."""
    
    def test_basic_component_prompt(self):
        """Generate prompt for basic component item."""
        prompt_data = generate_explanation_prompt(
            item_key="test-component",
            item_title="Auth Service",
            item_kind="component",
            item_band="basic",
            tracked_files=["src/auth.py"],
        )
        
        assert "prompt" in prompt_data
        assert "questions" in prompt_data
        assert prompt_data["item_key"] == "test-component"
        assert prompt_data["question_count"] >= 2
        assert prompt_data["question_count"] <= 4
        assert "Self-rating" in prompt_data["prompt"]
        assert "1-5" in prompt_data["prompt"]
    
    def test_intermediate_decision_prompt(self):
        """Generate prompt for intermediate decision item."""
        prompt_data = generate_explanation_prompt(
            item_key="test-decision",
            item_title="Database Selection",
            item_kind="decision",
            item_band="intermediate",
            tracked_files=["docs/architecture.md"],
        )
        
        assert "questions" in prompt_data
        questions = prompt_data["questions"]
        assert len(questions) >= 2
        assert len(questions) <= 4
        # Intermediate items should ask about tradeoffs
        prompt_text = prompt_data["prompt"]
        assert "tradeoff" in prompt_text.lower() or "alternative" in prompt_text.lower()
    
    def test_advanced_bugfix_prompt(self):
        """Generate prompt for advanced bugfix item."""
        prompt_data = generate_explanation_prompt(
            item_key="test-bugfix",
            item_title="Race Condition Fix",
            item_kind="bugfix",
            item_band="advanced",
            tracked_files=["src/concurrent.py"],
        )
        
        assert "questions" in prompt_data
        questions = prompt_data["questions"]
        # Advanced items should ask about edge cases or failure modes
        prompt_text = prompt_data["prompt"]
        assert "edge case" in prompt_text.lower() or "failure" in prompt_text.lower()
    
    def test_code_context_included(self):
        """Prompt includes code context when provided."""
        code = """def authenticate(user, password):
    if not user or not password:
        return False
    return check_credentials(user, password)
"""
        prompt_data = generate_explanation_prompt(
            item_key="auth-func",
            item_title="Authentication Function",
            item_kind="component",
            item_band="basic",
            tracked_files=["src/auth.py"],
            code_context=code,
        )
        
        assert prompt_data["includes_code_context"]
        assert "```" in prompt_data["prompt"]
        assert "authenticate" in prompt_data["prompt"]
    
    def test_code_context_truncated(self):
        """Long code context is truncated to max lines."""
        # Create 100 lines of code
        code = "\n".join([f"line{i} = {i}" for i in range(100)])
        
        prompt_data = generate_explanation_prompt(
            item_key="long-code",
            item_title="Long Module",
            item_kind="component",
            item_band="intermediate",
            tracked_files=["src/long.py"],
            code_context=code,
            max_context_lines=50,
        )
        
        assert prompt_data["includes_code_context"]
        # Should mention truncation
        assert "more lines" in prompt_data["prompt"]
    
    def test_file_list_in_prompt(self):
        """Prompt includes tracked file list."""
        files = ["src/auth.py", "src/user.py", "src/session.py"]
        prompt_data = generate_explanation_prompt(
            item_key="auth-system",
            item_title="Authentication System",
            item_kind="component",
            item_band="intermediate",
            tracked_files=files,
        )
        
        for file in files:
            assert file in prompt_data["prompt"]


class TestExplanationDepthCalculation:
    """Test explanation depth scoring."""
    
    def test_empty_explanation(self):
        """Empty explanation gets minimal score."""
        depth = calculate_explanation_depth("")
        assert depth == 0.0
    
    def test_very_short_explanation(self):
        """Very short explanations get low score."""
        depth = calculate_explanation_depth("It works fine.")
        assert depth < 0.3
    
    def test_technical_terms_boost_score(self):
        """Technical terms increase depth score."""
        technical_text = """
        This component implements an async authentication middleware
        using JWT tokens. The API endpoint validates the request
        headers and checks database credentials before allowing access.
        """
        depth = calculate_explanation_depth(technical_text)
        assert depth > 0.3
    
    def test_rationale_statements_boost_score(self):
        """Decision rationale increases depth score."""
        rationale_text = """
        I chose SQLite because it's lightweight and doesn't require
        a separate server process. The reason for this decision is
        to simplify deployment. Therefore, we can avoid the complexity
        of managing a database server.
        """
        depth = calculate_explanation_depth(rationale_text)
        assert depth > 0.3
    
    def test_alternatives_boost_score(self):
        """Considering alternatives increases depth score."""
        alternatives_text = """
        I used Redux instead of Context API for state management.
        The tradeoff is more boilerplate, but we gain better debugging tools.
        Compared to MobX, Redux has a larger ecosystem. Another option
        would have been Zustand, but Redux is more familiar to the team.
        """
        depth = calculate_explanation_depth(alternatives_text)
        assert depth > 0.4
    
    def test_comprehensive_explanation(self):
        """Comprehensive explanation with all elements gets high score."""
        comprehensive_text = """
        This authentication system uses JWT tokens for stateless authentication.
        I implemented it as middleware that intercepts API requests and validates
        the authorization header. The algorithm checks the token signature using
        HMAC-SHA256 and verifies the expiration timestamp.
        
        I chose JWT over session-based auth because we need to support multiple
        services without a shared session store. The tradeoff is that we can't
        revoke tokens immediately - they remain valid until expiration.
        
        I considered using OAuth2, but that would add complexity for our use case.
        Another option was Passport.js, but I wanted more control over the flow.
        
        For security, I ensure tokens are stored in httpOnly cookies to prevent
        XSS attacks. The refresh token rotation pattern prevents token reuse.
        """
        depth = calculate_explanation_depth(comprehensive_text)
        assert depth > 0.6
    
    def test_depth_bounded_zero_to_one(self):
        """Depth score is always between 0.0 and 1.0."""
        # Test with various inputs
        test_texts = [
            "",
            "Short.",
            "A" * 1000,  # Very long text
            "Technical API async await database query transaction " * 50,
        ]
        
        for text in test_texts:
            depth = calculate_explanation_depth(text)
            assert 0.0 <= depth <= 1.0


class TestQualityFeedback:
    """Test explanation quality feedback."""
    
    def test_high_quality_no_feedback(self):
        """High-quality explanation doesn't need improvement."""
        feedback = generate_quality_feedback(0.7, self_rating=4)
        assert not feedback["needs_improvement"]
        assert feedback["message"] is None
    
    def test_low_quality_gets_feedback(self):
        """Low-quality explanation gets improvement suggestions."""
        feedback = generate_quality_feedback(0.2, self_rating=2)
        assert feedback["needs_improvement"]
        assert feedback["message"] is not None
        assert len(feedback["suggestions"]) > 0
    
    def test_very_low_quality_specific_guidance(self):
        """Very low quality gets specific guidance."""
        feedback = generate_quality_feedback(0.1)
        assert feedback["needs_improvement"]
        assert "brief" in feedback["message"].lower()
        assert len(feedback["suggestions"]) >= 3
    
    def test_medium_quality_targeted_suggestions(self):
        """Medium quality gets targeted suggestions."""
        feedback = generate_quality_feedback(0.35)
        assert feedback["needs_improvement"]
        assert "Good start" in feedback["message"]
        assert len(feedback["suggestions"]) >= 3
    
    def test_self_rating_mismatch_warning(self):
        """High self-rating with low depth gets warning."""
        feedback = generate_quality_feedback(0.25, self_rating=5)
        assert feedback["needs_improvement"]
        assert "self-rating is high" in feedback["message"]
    
    def test_threshold_at_point_four(self):
        """Feedback threshold is at 0.4."""
        # Just below threshold
        feedback_low = generate_quality_feedback(0.39)
        assert feedback_low["needs_improvement"]
        
        # Just at/above threshold
        feedback_ok = generate_quality_feedback(0.4)
        assert not feedback_ok["needs_improvement"]


class TestQuestionGeneration:
    """Test question generation for different item types."""
    
    def test_component_questions(self):
        """Component items get component-specific questions."""
        prompt_data = generate_explanation_prompt(
            item_key="comp",
            item_title="User Service",
            item_kind="component",
            item_band="basic",
            tracked_files=["src/user.py"],
        )
        
        questions_text = " ".join(prompt_data["questions"]).lower()
        assert "what does" in questions_text or "how does" in questions_text
    
    def test_decision_questions(self):
        """Decision items ask about alternatives."""
        prompt_data = generate_explanation_prompt(
            item_key="dec",
            item_title="Framework Choice",
            item_kind="decision",
            item_band="intermediate",
            tracked_files=["docs/decision.md"],
        )
        
        questions_text = " ".join(prompt_data["questions"]).lower()
        assert "alternative" in questions_text or "problem" in questions_text
    
    def test_bugfix_questions(self):
        """Bugfix items ask about cause and fix."""
        prompt_data = generate_explanation_prompt(
            item_key="bug",
            item_title="Memory Leak Fix",
            item_kind="bugfix",
            item_band="advanced",
            tracked_files=["src/memory.py"],
        )
        
        questions_text = " ".join(prompt_data["questions"]).lower()
        assert "bug" in questions_text or "cause" in questions_text or "fix" in questions_text
    
    def test_concept_questions(self):
        """Concept items get general explanation questions."""
        prompt_data = generate_explanation_prompt(
            item_key="concept",
            item_title="Closures",
            item_kind="concept",
            item_band="intermediate",
            tracked_files=[],
        )
        
        questions_text = " ".join(prompt_data["questions"]).lower()
        assert "explain" in questions_text or "important" in questions_text
