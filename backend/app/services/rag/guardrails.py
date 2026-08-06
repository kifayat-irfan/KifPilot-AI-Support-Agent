import re
from typing import List, Tuple
from app.services.rag.exceptions import (
    EmptyQuestionError,
    PromptInjectionError,
    QuestionTooLongError,
)


class Guardrails:
    """Input validation and safety guardrails for RAG pipeline."""

    # Patterns that indicate prompt injection attempts
    INJECTION_PATTERNS = [
        r"ignore\s+(?:previous|above|all)\s+instructions?",
        r"forget\s+(?:everything|all|previous)",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"act\s+as\s+(?:if|a|an)",
        r"pretend\s+to\s+be",
        r"disregard\s+(?:previous|above|all)",
        r"override\s+(?:previous|instructions?)",
        r"ignore\s+the\s+(?:context|system)",
        r"new\s+instructions?:",
        r"answer\s+without\s+(?:context|retrieval)",
        r"bypass",
        r"jailbreak",
    ]

    # Maximum question length
    MAX_QUESTION_LENGTH = 2000

    # Patterns for requests to reveal system prompt
    SYSTEM_PROMPT_PATTERNS = [
        r"(?:show|reveal|display|print|output)\s+(?:the\s+)?system\s+prompt",
        r"what\s+(?:is|was)\s+(?:your|the)\s+system\s+prompt",
        r"tell\s+me\s+(?:your|the)\s+system\s+prompt",
    ]

    @classmethod
    def validate_question(cls, question: str) -> str:
        """
        Validate question against all guardrails.
        
        Args:
            question: User's question
            
        Returns:
            Cleaned question string
            
        Raises:
            EmptyQuestionError: If question is empty
            QuestionTooLongError: If question exceeds max length
            PromptInjectionError: If prompt injection detected
        """
        if not question or not question.strip():
            raise EmptyQuestionError()

        cleaned = question.strip()

        if len(cleaned) > cls.MAX_QUESTION_LENGTH:
            raise QuestionTooLongError(len(cleaned), cls.MAX_QUESTION_LENGTH)

        cls._check_injection(cleaned)
        cls._check_system_prompt_request(cleaned)

        return cleaned

    @classmethod
    def _check_injection(cls, question: str) -> None:
        """Check for prompt injection attempts."""
        lower = question.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                raise PromptInjectionError()

    @classmethod
    def _check_system_prompt_request(cls, question: str) -> None:
        """Check for requests to reveal system prompt."""
        lower = question.lower()
        for pattern in cls.SYSTEM_PROMPT_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                raise PromptInjectionError()

    @classmethod
    def sanitize_context(cls, context: str) -> str:
        """
        Sanitize context to remove any potential injection vectors.
        
        Args:
            context: Retrieved context string
            
        Returns:
            Sanitized context
        """
        # Remove any potential control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', context)
        return sanitized