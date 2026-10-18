"""Explanation prompt generation and depth calculation service."""

from __future__ import annotations

import re
from typing import Any

# Technical term patterns for depth calculation
TECHNICAL_PATTERNS = [
    r'\b(?:class|function|method|interface|abstract|async|await|callback)\b',
    r'\b(?:database|query|schema|index|transaction|migration)\b',
    r'\b(?:API|REST|HTTP|endpoint|request|response|middleware)\b',
    r'\b(?:algorithm|complexity|O\([^)]+\)|performance|optimization)\b',
    r'\b(?:pattern|singleton|factory|observer|decorator|strategy)\b',
    r'\b(?:thread|process|concurrent|parallel|synchronize|mutex|lock)\b',
    r'\b(?:cache|buffer|queue|stack|heap|pointer|reference)\b',
    r'\b(?:authentication|authorization|permission|security|encrypt)\b',
    r'\b(?:component|module|package|dependency|import|export)\b',
    r'\b(?:state|props|hook|reducer|action|dispatch)\b',
]

# Decision rationale indicators
RATIONALE_PATTERNS = [
    r'\b(?:because|since|as|therefore|thus|hence|so that)\b',
    r'\b(?:in order to|to ensure|to prevent|to avoid|to enable)\b',
    r'\b(?:the reason|the goal|the purpose|the benefit)\b',
    r'\b(?:decided|chose|selected|opted for|went with)\b',
]

# Alternative consideration indicators
ALTERNATIVE_PATTERNS = [
    r'\b(?:alternative|instead of|rather than|compared to|versus|vs)\b',
    r'\b(?:could have|might have|considered|evaluated|weighed)\b',
    r'\b(?:tradeoff|trade-off|compromise|balance)\b',
    r'\b(?:another option|other approach|different way)\b',
    r'\b(?:pros and cons|advantages|disadvantages|drawbacks)\b',
]


def generate_explanation_prompt(
    item_key: str,
    item_title: str,
    item_kind: str,
    item_band: str,
    tracked_files: list[str],
    code_context: str | None = None,
    max_context_lines: int = 50,
) -> dict[str, Any]:
    """Generate explanation prompt for a knowledge item.
    
    Args:
        item_key: Unique key for the knowledge item
        item_title: Title of the knowledge item
        item_kind: Kind of item (component, decision, concept, or bugfix)
        item_band: Complexity band (basic, intermediate, advanced)
        tracked_files: List of file paths tracked by this item
        code_context: Optional code snippet context (max 50 lines)
        max_context_lines: Maximum lines of code context to include
        
    Returns:
        dict with prompt text, questions, and metadata
    """
    # Generate depth-appropriate questions based on band
    questions = _generate_questions(item_kind, item_band, item_title)
    
    # Build the prompt
    prompt_parts = [
        f"**Explain: {item_title}**",
        "",
        "Now that you've implemented this, explain what you learned:",
        "",
    ]
    
    # Add code context if provided
    if code_context:
        # Limit to max_context_lines
        lines = code_context.strip().split('\n')
        if len(lines) > max_context_lines:
            lines = lines[:max_context_lines]
            context = '\n'.join(lines)
            context += f"\n... ({len(code_context.split('\n')) - max_context_lines} more lines)"
        else:
            context = '\n'.join(lines)
            
        prompt_parts.extend([
            "**Context:**",
            "```",
            context,
            "```",
            "",
        ])
    
    # Add file references
    if tracked_files:
        prompt_parts.append("**Files involved:**")
        for file_path in tracked_files[:5]:  # Limit to 5 files
            prompt_parts.append(f"- `{file_path}`")
        if len(tracked_files) > 5:
            prompt_parts.append(f"- ... and {len(tracked_files) - 5} more")
        prompt_parts.append("")
    
    # Add questions
    prompt_parts.append("**Questions to guide your explanation:**")
    for i, question in enumerate(questions, 1):
        prompt_parts.append(f"{i}. {question}")
    
    prompt_parts.extend([
        "",
        "**Self-rating:** On a scale of 1-5, how confident do you feel about this?",
        "- 1 = Still confused",
        "- 2 = Shaky understanding",
        "- 3 = Decent grasp",
        "- 4 = Confident",
        "- 5 = Could teach it",
    ])
    
    prompt_text = '\n'.join(prompt_parts)
    
    return {
        "prompt": prompt_text,
        "item_key": item_key,
        "questions": questions,
        "question_count": len(questions),
        "includes_code_context": code_context is not None,
    }


def _generate_questions(item_kind: str, item_band: str, item_title: str) -> list[str]:
    """Generate depth-appropriate questions based on item characteristics.
    
    Args:
        item_kind: Kind of item (component, decision, concept, bugfix)
        item_band: Complexity band (basic, intermediate, advanced)
        item_title: Title to customize questions
        
    Returns:
        List of 2-4 open-ended questions
    """
    questions = []
    
    # Base questions by kind
    if item_kind == "component":
        questions.append(f"What does {item_title} do and why is it needed?")
        questions.append("How does it interact with other parts of the system?")
    elif item_kind == "decision":
        questions.append(f"What problem does this decision solve?")
        questions.append("What alternatives did you consider?")
    elif item_kind == "bugfix":
        questions.append("What was causing the bug?")
        questions.append("How does your fix address the root cause?")
    else:  # concept
        questions.append(f"Explain {item_title} in your own words.")
        questions.append("Why is this concept important here?")
    
    # Add depth-appropriate questions
    if item_band == "intermediate":
        questions.append("What tradeoffs or limitations should you be aware of?")
    elif item_band == "advanced":
        questions.append("What edge cases or failure modes need consideration?")
        if item_kind == "component":
            questions.append("How would you test or debug this if something goes wrong?")
    
    # Limit to 4 questions max
    return questions[:4]


def calculate_explanation_depth(explanation_text: str) -> float:
    """Calculate explanation depth score based on content analysis.
    
    Analyzes explanation text for:
    - Technical term usage
    - Decision rationale statements
    - Alternative consideration
    
    Args:
        explanation_text: The learner's explanation text
        
    Returns:
        Float score between 0.0 (superficial) and 1.0 (deep)
    """
    if not explanation_text or not explanation_text.strip():
        return 0.0
    
    text = explanation_text.lower()
    word_count = len(text.split())
    
    # Minimum length requirement
    if word_count < 20:
        return 0.1
    
    # Count technical terms (weighted 40%)
    technical_count = 0
    for pattern in TECHNICAL_PATTERNS:
        technical_count += len(re.findall(pattern, text, re.IGNORECASE))
    technical_score = min(1.0, technical_count / 5.0)  # Normalize to 0-1
    
    # Count decision rationale statements (weighted 30%)
    rationale_count = 0
    for pattern in RATIONALE_PATTERNS:
        rationale_count += len(re.findall(pattern, text, re.IGNORECASE))
    rationale_score = min(1.0, rationale_count / 3.0)  # Normalize to 0-1
    
    # Count alternative considerations (weighted 20%)
    alternative_count = 0
    for pattern in ALTERNATIVE_PATTERNS:
        alternative_count += len(re.findall(pattern, text, re.IGNORECASE))
    alternative_score = min(1.0, alternative_count / 2.0)  # Normalize to 0-1
    
    # Length bonus (weighted 10%)
    # Reward substantial explanations (100+ words)
    length_score = min(1.0, word_count / 100.0)
    
    # Weighted combination
    depth_score = (
        technical_score * 0.4 +
        rationale_score * 0.3 +
        alternative_score * 0.2 +
        length_score * 0.1
    )
    
    # Ensure result is in valid range
    return max(0.0, min(1.0, depth_score))


def generate_quality_feedback(depth_score: float, self_rating: int | None = None) -> dict[str, Any]:
    """Generate feedback for low-quality explanations.
    
    Args:
        depth_score: Calculated depth score (0.0-1.0)
        self_rating: Optional self-rating (1-5)
        
    Returns:
        dict with feedback message and suggestions
    """
    if depth_score >= 0.4:
        return {
            "needs_improvement": False,
            "message": None,
            "suggestions": [],
        }
    
    suggestions = []
    message_parts = ["Your explanation could be deeper. Consider:"]
    
    # Provide specific guidance based on what's missing
    if depth_score < 0.2:
        suggestions.append("Add more technical details about how it works")
        suggestions.append("Explain the reasoning behind your decisions")
        suggestions.append("Describe what alternatives you considered")
        message_parts.append("This explanation is quite brief. Try to be more specific about what you learned.")
    elif depth_score < 0.4:
        suggestions.append("Include more reasoning about why you made certain choices")
        suggestions.append("Discuss tradeoffs or alternatives you considered")
        suggestions.append("Add more technical terminology to show your understanding")
        message_parts.append("Good start! Try adding more depth about the reasoning and alternatives.")
    
    # Add self-rating mismatch warning
    if self_rating and self_rating >= 4 and depth_score < 0.3:
        message_parts.append(
            "\n**Note:** Your self-rating is high but your explanation is brief. "
            "Take a moment to articulate what makes you confident."
        )
    
    return {
        "needs_improvement": True,
        "message": "\n".join(message_parts),
        "suggestions": suggestions,
        "depth_score": depth_score,
    }
