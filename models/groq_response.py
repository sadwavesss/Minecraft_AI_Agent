from pydantic import BaseModel, Field
from typing import Optional


class GroqAdvice(BaseModel):
    """Response model for LLM-generated RP response."""

    response: str
    confidence: float
    level: str  # INFO, WARNING, CRITICAL
    threats: list = Field(default_factory=list)
    source: str = "groq"  # Indicates this came from Groq LLM
    fallback: bool = False  # True if using fallback response due to API error
    mode: str = "chat"  # chat | action
    execute: bool = False
    command: Optional[str] = None
    action_type: Optional[str] = None
    item_id: Optional[str] = None
    item_count: Optional[int] = None
    entity_id: Optional[str] = None
    entity_count: Optional[int] = None
    error: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message from player."""
    text: str
