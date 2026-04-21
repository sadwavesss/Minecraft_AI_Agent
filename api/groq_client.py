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

    def generate_analytics(self, session_summary: dict) -> Optional[str]:
        """
        Generate post-match tactical analysis based on session summary.
        BLOCKING - should be called from thread pool!

        Args:
            session_summary: Dict containing aggregated session stats

        Returns:
            Detailed markdown response with tactical analysis or None if fails
        """
        if not self.is_available():
            return None

        prompt = f"""You are an elite eSports coach and Minecraft tactical analyst.
The player has just finished a game session. Here is their performance summary:

Total Logs Analyzed: {session_summary.get('total_logs', 0)}
Deaths: {session_summary.get('deaths', 0)}
Low Health Warnings: {session_summary.get('low_health_warnings', 0)}
Hostile Encounters: {session_summary.get('hostile_encounters', 0)}

Significant events timeline:
{chr(10).join(session_summary.get('timeline', []))}

Provide a highly engaging, structured tactical review in Russian.
Include:
1. Оценка выживаемости (Survival Rating)
2. Главные ошибки (Critical Mistakes)
3. Советы на следующую сессию (Tips for next session)
Format using markdown for readability."""

        try:
            api_params = self._build_api_params()
            # We bypass max_tokens here for a full report if it's set too low for tips
            original_max_tokens = api_params.get("max_tokens", 100)
            if original_max_tokens < 500:
                api_params["max_tokens"] = 800

            api_params["messages"] = [{"role": "user", "content": prompt}]
            
            message = self.client.chat.completions.create(**api_params)
            response = _strip_thinking(message.choices[0].message.content)
            return response if response else None
        except Exception as e:
            logger.error(f"Groq analytics API error: {e}")
            return None

    async def generate_analytics_async(self, session_summary: dict) -> Optional[str]:
        """Async wrapper for generate_analytics."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(_executor, self.generate_analytics, session_summary)
            return response
        except Exception as e:
            logger.error(f"Async generate_analytics error: {e}")
            return None

    def search_crafting_recipe(self, query: str) -> Optional[dict]:
        """
        Uses LLM to search for a Minecraft crafting recipe and returns structured JSON representing a 3x3 grid.
        BLOCKING - should be called from thread pool!
        """
        if not self.is_available():
            return None

        prompt = f"""You are a perfect Minecraft Wiki for Java Edition version 1.20+. The user wants to craft: "{query}".
First, identify this item in English and retrieve its exact standard Minecraft vanilla 3x3 crafting recipe.
Then, translate the ingredients fully into Russian.
Respond ONLY with a JSON object. Do not wrap it in ```json.
Format:
{{
  "english_thought": "Step-by-step thinking about the English name and exact vanilla recipe layout",
  "name": "Точное название предмета на русском",
  "description": "Коротко как применяется",
  "grid": [
    ["пусто", "пусто", "пусто"],
    ["пусто", "пусто", "пусто"],
    ["пусто", "пусто", "пусто"]
  ]
}}
Empty slots MUST be exactly the string "пусто". Fill the 3x3 array strictly.
If the item is completely uncraftable (like Bedrock or Spawn Eggs), set grid all "пусто" and write "Невозможно скрафтить в выживании" in description."""

        try:
            api_params = self._build_api_params()
            api_params["messages"] = [{"role": "user", "content": prompt}]
            # Disable temp for deterministic recipes
            api_params["temperature"] = 0.0
            
            # Increase max_tokens since JSON recipes and thinking take > 100 tokens
            api_params["max_tokens"] = 500
            
            # Force JSON mode for better reliability (if using Groq SDK)
            if "groq" in str(type(self.client)).lower():
                api_params["response_format"] = {"type": "json_object"}
            
            message = self.client.chat.completions.create(**api_params)
            response = _strip_thinking(message.choices[0].message.content)
            
            # Clean up potential markdown formatting
            import json
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            return json.loads(response)
        except Exception as e:
            logger.error(f"Groq wiki API error: {e}")
            return None

    async def search_crafting_recipe_async(self, query: str) -> Optional[dict]:
        """Async wrapper for search_crafting_recipe."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(_executor, self.search_crafting_recipe, query)
            return response
        except Exception as e:
            logger.error(f"Async search_crafting_recipe error: {e}")
            return None
