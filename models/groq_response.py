from pydantic import BaseModel
from typing import Optional


class GroqAdvice(BaseModel):
    """Response model for LLM-generated advice."""

    advice: str
    confidence: float
    level: str  # INFO, WARNING, CRITICAL
    threats: list = []
    source: str = "groq"  # Indicates this came from Groq LLM
    fallback: bool = False  # True if using fallback advice due to API error
