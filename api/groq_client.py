import os
from typing import Optional
import logging
from groq import Groq

logger = logging.getLogger(__name__)


class GroqClient:
    """Wrapper for Groq API calls with context about Minecraft game state."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = "mixtral-8x7b-32768"
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self.client = None

    def is_available(self) -> bool:
        """Check if Groq API is configured and ready."""
        return self.client is not None and self.api_key is not None

    def generate_tip(self, recent_logs: list) -> Optional[str]:
        """
        Generate a short tip based on recent game state logs.

        Args:
            recent_logs: List of recent LogEntry objects (last 5 events)

        Returns:
            Short tip string or None if API call fails
        """
        if not self.is_available():
            return None

        # Format recent logs into a context string
        context = self._format_logs_context(recent_logs)

        prompt = f"""You are a helpful Minecraft game assistant. Based on the player's recent game state, provide a SHORT (1-2 sentences) and ACTIONABLE tip in Russian.

Recent game events:
{context}

Rules:
- Keep it SHORT (max 1-2 sentences)
- Be SPECIFIC to what's happening
- Include what the player should DO (actionable)
- Use Russian language
- Focus on survival and safety

Provide only the tip, nothing else."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            tip = message.content[0].text.strip()
            return tip if tip else None
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

    def _format_logs_context(self, recent_logs: list) -> str:
        """Format recent logs into readable context for the LLM."""
        if not recent_logs:
            return "No recent events recorded."

        lines = []
        for log in recent_logs:
            event_type = getattr(log, "event_type", None)
            event_data = getattr(log, "event_data", None)
            player_health = getattr(log, "player_health", None)
            threats = getattr(log, "threats_detected", None)

            # Build event description
            if event_type:
                lines.append(f"- Event: {event_type}")
                if event_data:
                    lines.append(f"  Details: {event_data}")

            # Add state info
            if player_health is not None:
                lines.append(f"- Health: {player_health}")
            if threats:
                lines.append(f"- Threats detected: {len(threats)} active")

        return "\n".join(lines) if lines else "No recent events recorded."
