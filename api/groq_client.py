import os
import re
from typing import Optional
import logging
from groq import Groq
from openai import OpenAI as OllamaClient
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Thread pool for blocking LLM API calls
_executor = ThreadPoolExecutor(max_workers=2)


def _strip_thinking(text: str) -> str:
    """Strip <think>...</think> reasoning blocks from LLM output (Qwen3 etc.)."""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()


class GroqClient:
    """Wrapper for LLM API calls (Groq or Ollama) with Minecraft game state context."""

    def __init__(self, llm_config=None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.llm_config = llm_config
        self.model = None
        self.provider = "groq"  # default

        if llm_config:
            self.model = llm_config.get_model_name()
            active = llm_config.get_active_model()
            self.provider = getattr(active, "provider", "groq")
        else:
            self.model = "llama-3.1-8b-instant"

        if self.provider == "ollama":
            try:
                self.client = OllamaClient(base_url=OLLAMA_BASE_URL, api_key="ollama")
                print(f"[LLM] Using Ollama | model: {self.model} | url: {OLLAMA_BASE_URL}")
                logger.info(f"Initialized Ollama client with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                self.client = None
        else:
            if self.api_key:
                try:
                    self.client = Groq(api_key=self.api_key)
                    print(f"[LLM] Using Groq | model: {self.model}")
                    logger.info(f"Initialized Groq client with model: {self.model}")
                except Exception as e:
                    logger.error(f"Failed to initialize Groq client: {e}")
                    self.client = None
            else:
                print("[LLM] WARNING: GROQ_API_KEY not set — Groq unavailable")
                logger.warning("GROQ_API_KEY not set")

    def is_available(self) -> bool:
        """Check if LLM API is configured and ready."""
        if self.provider == "ollama":
            return self.client is not None
        return self.client is not None and self.api_key is not None

    def _get_max_tokens(self) -> int:
        """Get max tokens from config or default."""
        if self.llm_config:
            return self.llm_config.get_parameter("max_tokens", 100)
        return 100

    def _get_temperature(self) -> float:
        """Get temperature from config or default."""
        if self.llm_config:
            return self.llm_config.get_parameter("temperature", 0.7)
        return 0.7

    def _build_api_params(self) -> dict:
        """Build API parameters based on model config."""
        params = {
            "model": self.model,
            "max_tokens": self._get_max_tokens(),
            "messages": [],  # Will be set by caller
        }
        
        # Add temperature if it exists
        if self.llm_config and self.llm_config.has_parameter("temperature"):
            params["temperature"] = self._get_temperature()
        
        # Add reasoning_effort if it exists (only for Qwen)
        if self.llm_config and self.llm_config.has_parameter("reasoning_effort"):
            params["reasoning_effort"] = self.llm_config.get_parameter("reasoning_effort")
        
        return params

    def generate_tip(self, recent_logs: list) -> Optional[str]:
        """
        Generate a role-play response based on recent game state logs.
        BLOCKING - should be called from thread pool!

        Args:
            recent_logs: List of recent LogEntry objects (last 5 events)

        Returns:
            Short RP response string or None if API call fails
        """
        if not self.is_available():
            return None

        # Format recent logs into a context string
        context = self._format_logs_context(recent_logs)

        # Get prompt template from config
        if self.llm_config:
            prompt_template = self.llm_config.get_state_prompt_template()
            prompt = prompt_template.format(context=context)
        else:
            prompt = f"""You are a role-playing Minecraft game companion. Based on the player's recent game state, provide a SHORT (1-2 sentences) humorous or sarcastic response in Russian.

Recent game events:
{context}

Rules:
- Keep it SHORT (max 1-2 sentences)
- Be SPECIFIC to what's happening
- Use Russian language

Provide only the role-play response, nothing else."""

        try:
            # Build API parameters based on model configuration
            api_params = self._build_api_params()
            api_params["messages"] = [{"role": "user", "content": prompt}]
            
            message = self.client.chat.completions.create(**api_params)
            tip = _strip_thinking(message.choices[0].message.content)
            return tip if tip else None
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

    def generate_chat_response(self, player_message: str, recent_logs: list) -> Optional[str]:
        """
        Generate a role-play response to player's chat message.
        BLOCKING - should be called from thread pool!

        Args:
            player_message: The player's chat message
            recent_logs: List of recent LogEntry objects (last 5 events)

        Returns:
            RP response to player's message or None if API call fails
        """
        if not self.is_available():
            return None

        context = self._format_logs_context(recent_logs)

        # Get prompt template from config
        if self.llm_config:
            prompt_template = self.llm_config.get_chat_prompt_template()
            prompt = prompt_template.format(player_message=player_message, context=context)
        else:
            prompt = f"""You are a role-playing Minecraft game companion talking to a player. The player just said:
"{player_message}"

Current game context:
{context}

Respond in character as a helpful, humorous companion in Russian. Keep it SHORT (1 sentence max).
Respond only with the RP response, nothing else."""

        try:
            # Build API parameters based on model configuration
            api_params = self._build_api_params()
            api_params["messages"] = [{"role": "user", "content": prompt}]
            
            message = self.client.chat.completions.create(**api_params)
            response = _strip_thinking(message.choices[0].message.content)
            return response if response else None
        except Exception as e:
            logger.error(f"Groq chat API error: {e}")
            return None

    async def generate_tip_async(self, recent_logs: list) -> Optional[str]:
        """
        Async wrapper for generate_tip that doesn't block the event loop.
        
        Args:
            recent_logs: List of recent LogEntry objects
            
        Returns:
            Short RP response string or None if API call fails
        """
        try:
            # Run blocking call in thread pool
            loop = asyncio.get_event_loop()
            tip = await loop.run_in_executor(_executor, self.generate_tip, recent_logs)
            return tip
        except Exception as e:
            logger.error(f"Async generate_tip error: {e}")
            return None

    async def generate_chat_response_async(self, player_message: str, recent_logs: list) -> Optional[str]:
        """
        Async wrapper for generate_chat_response that doesn't block the event loop.
        
        Args:
            player_message: The player's chat message
            recent_logs: List of recent LogEntry objects
            
        Returns:
            RP response or None if API call fails
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(_executor, self.generate_chat_response, player_message, recent_logs)
            return response
        except Exception as e:
            logger.error(f"Async generate_chat_response error: {e}")
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
