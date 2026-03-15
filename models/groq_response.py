from pydantic import BaseModel
from typing import Optional


class GroqAdvice(BaseModel):
    """Response model for LLM-generated RP response."""

    response: str
    confidence: float
    level: str  # INFO, WARNING, CRITICAL
    threats: list = []
    source: str = "groq"  # Indicates this came from Groq LLM
    fallback: bool = False  # True if using fallback response due to API error


class ChatMessage(BaseModel):
    """Chat message from player."""
    text: str
