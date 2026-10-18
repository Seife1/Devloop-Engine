"""Auto-Tracker service for automatic learning event detection.

This service analyzes AI assistant conversations to automatically detect learning
opportunities without manual tracking. It extracts code blocks, detects decision
points, and assigns confidence scores to learning events.

Requirements: 3.1, 3.2, 3.7, 3.9
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from learnloop.domain.learning_event import EventSource, EventType, LearningEvent

# Thresholds for event detection
SIGNIFICANCE_THRESHOLD = 0.3  # Minimum complexity for significant learning
AUTO_TRACK_THRESHOLD = 0.7  # Minimum confidence to auto-store events


@dataclass
class Message:
    """A conversation message from user or assistant.
    
    Attributes:
        role: Either 'user' or 'assistant'
        content: The text content of the message
        timestamp: When the message was sent (UTC)
    """

    role: str
    content: str
    timestamp: datetime


@dataclass
class CodeSegment:
    """An extracted code block from conversation.
    
    Attributes:
        code: The actual code content
        language: Detected programming language
        timestamp: When this code appeared
        context: Surrounding text context
    """

    code: str
    language: str
    timestamp: datetime
    context: str


@dataclass
class DecisionPoint:
    """A detected decision point from conversation.
    
    Attributes:
        decision: The decision description
        timestamp: When this decision appeared
        alternatives: List of alternative approaches discussed
    """

    decision: str
    timestamp: datetime
    alternatives: list[str]


class AutoTrackerService:
    """Service for automatic learning event detection from conversations.
    
    This service analyzes AI assistant conversation history to detect learning
    opportunities automatically, without requiring manual intent declarations.
    """

    def __init__(self) -> None:
        """Initialize the auto-tracker service."""
        # Language detection patterns - match common code block fence markers
        self._language_patterns = {
            "python": r"```python|```py|def |class |import |from .+ import",
            "javascript": r"```javascript|```js|function |const |let |var |=>|require\(|import .+ from",
            "typescript": r"```typescript|```ts|interface |type |: string|: number|: boolean",
            "java": r"```java|public class |private |protected |void |@Override",
            "rust": r"```rust|fn |let mut|impl |trait |pub |use crate::",
            "go": r"```go|func |package |import \(|type .+ struct",
            "sql": r"```sql|SELECT |INSERT |UPDATE |DELETE |CREATE TABLE",
            "bash": r"```bash|```sh|#!/bin/bash|export |alias ",
        }

        # Decision keyword patterns
        self._decision_keywords = [
            r"we could",
            r"you could",
            r"alternatively",
            r"another option",
            r"instead of",
            r"consider",
            r"trade-?off",
            r"option \d+",
            r"approach \d+",
            r"versus|vs\.|vs ",
        ]

    def analyze_conversation(
        self, messages: list[Message], project_id: str
    ) -> list[LearningEvent]:
        """Extract learning events from AI conversation history.
        
        Analyzes conversation messages to detect:
        - Code implementations (from code blocks)
        - Decision points (from alternatives discussion)
        - Questions and explanations
        
        Args:
            messages: List of conversation messages (chronologically ordered)
            project_id: ID of the project context
            
        Returns:
            List of detected learning events with confidence scores
            
        Requirements:
            - 3.1: Extract code blocks from assistant messages
            - 3.2: Calculate complexity scores for code
            - 3.7: Assign confidence scores between 0.0 and 1.0
            - 3.9: Complete analysis in under 200ms for 100 messages
        """
        if not messages:
            return []

        learning_events: list[LearningEvent] = []
        code_segments: list[CodeSegment] = []
        decision_points: list[DecisionPoint] = []

        # Step 1: Extract code segments and decisions from assistant messages
        for message in messages:
            if message.role == "assistant":
                # Extract code blocks (Requirement 3.1)
                blocks = self._extract_code_blocks(message.content)
                for block in blocks:
                    if self._is_significant_code(block["code"]):
                        language = self._detect_language(block["code"], message.content)
                        context = self._extract_context(message.content, block["code"])
                        code_segments.append(
                            CodeSegment(
                                code=block["code"],
                                language=language,
                                timestamp=message.timestamp,
                                context=context,
                            )
                        )

                # Extract decision points
                decisions = self._extract_decisions(message.content)
                for decision in decisions:
                    alternatives = self._extract_alternatives(message.content, decision)
                    decision_points.append(
                        DecisionPoint(
                            decision=decision,
                            timestamp=message.timestamp,
                            alternatives=alternatives,
                        )
                    )

        # Step 2: Create learning events from code segments
        for segment in code_segments:
            skills = self._detect_skills_from_language(segment.language)
            complexity = self._calculate_basic_complexity(segment.code)

            # Requirement 3.3: Filter by significance threshold
            if complexity > SIGNIFICANCE_THRESHOLD:
                confidence = self._calculate_confidence(segment, skills, complexity)

                # Requirement 3.7: Confidence must be between 0.0 and 1.0
                event = LearningEvent.create(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type=EventType.IMPLEMENTATION,
                    timestamp=segment.timestamp,
                    content={
                        "code": segment.code,
                        "language": segment.language,
                        "context": segment.context,
                        "complexity": complexity,
                    },
                    skills=skills,
                    confidence=confidence,
                    source=EventSource.CONVERSATION,
                )
                learning_events.append(event)

        # Step 3: Create learning events from decision points
        for decision in decision_points:
            if self._has_significant_alternatives(decision.alternatives):
                skills = self._extract_decision_skills(decision)
                confidence = self._calculate_decision_confidence(decision)

                event = LearningEvent.create(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type=EventType.DECISION,
                    timestamp=decision.timestamp,
                    content={
                        "decision": decision.decision,
                        "alternatives": decision.alternatives,
                    },
                    skills=skills,
                    confidence=confidence,
                    source=EventSource.CONVERSATION,
                )
                learning_events.append(event)

        # Step 4: Deduplicate and rank events
        learning_events = self._deduplicate_events(learning_events)
        learning_events = self._sort_by_relevance(learning_events)

        return learning_events

    def _extract_code_blocks(self, content: str) -> list[dict[str, str]]:
        """Extract code blocks from markdown-formatted content.
        
        Supports both fenced code blocks (```) and indented code blocks.
        
        Args:
            content: Message content possibly containing code blocks
            
        Returns:
            List of dicts with 'code' and optional 'language' keys
        """
        blocks: list[dict[str, str]] = []

        # Match fenced code blocks with optional language specifier
        # Pattern: ```language\ncode\n``` or ```\ncode\n```
        fence_pattern = r"```(\w+)?\n(.*?)```"
        for match in re.finditer(fence_pattern, content, re.DOTALL):
            language = match.group(1) or ""
            code = match.group(2).strip()
            if code:
                blocks.append({"code": code, "language": language})

        return blocks

    def _detect_language(self, code: str, context: str) -> str:
        """Detect programming language from code and context.
        
        Uses pattern matching against common language constructs.
        
        Args:
            code: The code content
            context: Surrounding message context
            
        Returns:
            Detected language name or 'unknown'
        """
        combined = code + "\n" + context

        for language, pattern in self._language_patterns.items():
            if re.search(pattern, combined, re.IGNORECASE):
                return language

        return "unknown"

    def _is_significant_code(self, code: str) -> bool:
        """Check if code is significant enough to track.
        
        Filters out trivial code snippets like single variable assignments.
        
        Args:
            code: Code content to check
            
        Returns:
            True if code is significant, False otherwise
        """
        # Remove empty lines and comments
        lines = [
            line.strip()
            for line in code.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        # Need at least 3 lines of non-trivial code
        if len(lines) < 3:
            return False

        # Check for substance (not just variable declarations)
        has_logic = any(
            keyword in code.lower()
            for keyword in ["if", "for", "while", "def", "class", "function", "=>"]
        )

        return has_logic or len(lines) >= 5

    def _extract_context(self, content: str, code: str) -> str:
        """Extract surrounding text context for a code block.
        
        Gets the explanatory text around the code to provide context.
        
        Args:
            content: Full message content
            code: The code block
            
        Returns:
            Context string (up to 200 characters before and after)
        """
        # Try to find code position - handle potential whitespace differences
        code_pos = content.find(code)
        
        # If exact match fails, try to find a normalized version
        if code_pos == -1:
            # Normalize both strings for comparison
            normalized_content = re.sub(r'\s+', ' ', content)
            normalized_code = re.sub(r'\s+', ' ', code)
            code_pos = normalized_content.find(normalized_code)
            
            # If still not found, just return first 200 chars of content
            if code_pos == -1:
                return content[:200].strip()

        # Extract context before and after
        before_start = max(0, code_pos - 200)
        before = content[before_start:code_pos].strip()

        after_end = min(len(content), code_pos + len(code) + 200)
        after = content[code_pos + len(code) : after_end].strip()

        context_parts = []
        if before:
            context_parts.append(before)
        if after:
            context_parts.append(after)

        return " ... ".join(context_parts)

    def _extract_decisions(self, content: str) -> list[str]:
        """Extract decision points from conversation content.
        
        Looks for sentences discussing alternatives or tradeoffs.
        
        Args:
            content: Message content
            
        Returns:
            List of decision descriptions
        """
        decisions: list[str] = []

        # Split into sentences
        sentences = re.split(r"[.!?]\s+", content)

        for sentence in sentences:
            # Check if sentence contains decision keywords
            for keyword_pattern in self._decision_keywords:
                if re.search(keyword_pattern, sentence, re.IGNORECASE):
                    decisions.append(sentence.strip())
                    break  # Only add each sentence once

        return decisions

    def _extract_alternatives(self, content: str, decision: str) -> list[str]:
        """Extract alternative approaches from decision context.
        
        Args:
            content: Full message content
            decision: The decision statement
            
        Returns:
            List of alternative approaches
        """
        alternatives: list[str] = []

        # Look for numbered options (1., 2., etc.)
        option_pattern = r"(?:^|\n)\s*(\d+)[.):]\s*([^\n]+)"
        for match in re.finditer(option_pattern, content):
            alternatives.append(match.group(2).strip())

        # Look for bullet points
        bullet_pattern = r"(?:^|\n)\s*[-*]\s*([^\n]+)"
        if not alternatives:  # Only use bullets if no numbered options
            for match in re.finditer(bullet_pattern, content):
                alternatives.append(match.group(1).strip())

        return alternatives[:5]  # Limit to 5 alternatives

    def _has_significant_alternatives(self, alternatives: list[str]) -> bool:
        """Check if alternatives list is significant enough to track.
        
        Args:
            alternatives: List of alternative approaches
            
        Returns:
            True if alternatives are significant
        """
        # Need at least 2 alternatives
        if len(alternatives) < 2:
            return False

        # Each alternative should have some substance (>10 chars)
        return all(len(alt) > 10 for alt in alternatives)

    def _detect_skills_from_language(self, language: str) -> list[str]:
        """Detect skill tags based on programming language.
        
        Args:
            language: Detected programming language
            
        Returns:
            List of skill identifiers
        """
        # Basic language-based skills
        if language != "unknown":
            return [f"lang:{language}"]
        return []

    def _extract_decision_skills(self, decision: DecisionPoint) -> list[str]:
        """Extract skills from a decision point.
        
        Args:
            decision: Decision point with alternatives
            
        Returns:
            List of skill identifiers
        """
        skills = ["decision-making", "architecture"]

        # Check for specific decision types
        decision_text = decision.decision.lower()
        if any(word in decision_text for word in ["performance", "optimization", "efficiency"]):
            skills.append("performance")
        if any(word in decision_text for word in ["security", "authentication", "authorization"]):
            skills.append("security")
        if any(word in decision_text for word in ["database", "sql", "query"]):
            skills.append("database")

        return skills

    def _calculate_basic_complexity(self, code: str) -> float:
        """Calculate a basic complexity score for code.
        
        This is a simplified version for the conversation analyzer.
        More detailed complexity calculation in separate service.
        
        Args:
            code: Code content
            
        Returns:
            Complexity score between 0.0 and 1.0
            
        Requirements:
            - 18.7: Score must be between 0.0 and 1.0
            - 18.9: Trivial code (<5 lines) scores below 0.2
        """
        lines = [line.strip() for line in code.split("\n") if line.strip()]
        line_count = len(lines)

        # Trivial code check (Requirement 18.9)
        if line_count < 5:
            return min(0.19, line_count * 0.03)

        # Count control flow structures
        control_flow = len(
            re.findall(r"\b(if|for|while|switch|case|catch|try|else|elif)\b", code, re.IGNORECASE)
        )

        # Count function/class definitions
        definitions = len(re.findall(r"\b(def|class|function|interface|trait)\b", code, re.IGNORECASE))

        # Normalize metrics with better ranges
        line_score = min(1.0, line_count / 20)  # Normalize around 20 lines
        control_score = min(1.0, control_flow / 5)  # Normalize around 5 branches
        definition_score = min(1.0, definitions / 2)  # Normalize around 2 definitions

        # Weighted average - emphasize control flow and definitions more
        complexity = 0.3 * line_score + 0.5 * control_score + 0.2 * definition_score

        # Ensure bounds (Requirement 18.7)
        return max(0.0, min(1.0, complexity))

    def _calculate_confidence(
        self, segment: CodeSegment, skills: list[str], complexity: float
    ) -> float:
        """Calculate confidence score for a code segment event.
        
        Args:
            segment: Code segment
            skills: Detected skills
            complexity: Complexity score
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # Boost confidence for known languages
        if segment.language != "unknown":
            confidence += 0.2

        # Boost confidence for higher complexity
        confidence += complexity * 0.2

        # Boost confidence if we have context
        if len(segment.context) > 50:
            confidence += 0.1

        # Ensure bounds
        return max(0.0, min(1.0, confidence))

    def _calculate_decision_confidence(self, decision: DecisionPoint) -> float:
        """Calculate confidence score for a decision point event.
        
        Args:
            decision: Decision point
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence

        # More alternatives = higher confidence
        alt_count = len(decision.alternatives)
        confidence += min(0.3, alt_count * 0.1)

        # Longer alternatives = more detailed = higher confidence
        avg_alt_length = sum(len(alt) for alt in decision.alternatives) / max(alt_count, 1)
        if avg_alt_length > 50:
            confidence += 0.2

        # Ensure bounds
        return max(0.0, min(1.0, confidence))

    def _deduplicate_events(self, events: list[LearningEvent]) -> list[LearningEvent]:
        """Remove duplicate learning events.
        
        Args:
            events: List of learning events
            
        Returns:
            Deduplicated list
        """
        # Simple deduplication based on content similarity
        # For now, keep all events (more sophisticated dedup can be added later)
        seen_contents: set[str] = set()
        unique_events: list[LearningEvent] = []

        for event in events:
            # Create a simple hash of content
            if event.event_type == EventType.IMPLEMENTATION:
                content_hash = event.content.get("code", "")[:100]
            else:
                content_hash = event.content.get("decision", "")[:100]

            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_events.append(event)

        return unique_events

    def _sort_by_relevance(self, events: list[LearningEvent]) -> list[LearningEvent]:
        """Sort events by relevance (confidence score).
        
        Args:
            events: List of learning events
            
        Returns:
            Sorted list (highest confidence first)
        """
        return sorted(events, key=lambda e: e.confidence, reverse=True)
