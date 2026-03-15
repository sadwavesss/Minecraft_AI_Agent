from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect
from typing import Any, Dict, List, Optional, Set
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import time

from api.logs import logs_db
from api.settings import current_settings
from api.groq_client import GroqClient
from api.llm_config_manager import get_llm_config, set_model_type, get_available_models, get_model_info
from models.groq_response import GroqAdvice, ChatMessage

load_dotenv()

router = APIRouter(prefix="/api/rp", tags=["roleplay"])

# Initialize groq_client with LLM config
llm_config = get_llm_config()
groq_client = GroqClient(llm_config=llm_config)

# Critical events that require immediate response (no rate limiting)
CRITICAL_EVENTS = {"death"}

# Rate limiting and change detection
_last_rp_response_time = 0
_last_rp_response = None
_min_interval_seconds = 20  # Default 20 seconds between routine RP responses
_processed_log_ids: Set[int] = set()  # Track which logs we've responded to

# Response history for the admin panel
_response_history: List[Dict[str, Any]] = []
MAX_RESPONSE_HISTORY = 200
_response_ws_clients: List[WebSocket] = []


def _add_to_history(response: Dict[str, Any], player_message: Optional[str] = None) -> Dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": response.get("response", ""),
        "source": response.get("source", "unknown"),
        "level": response.get("level", "INFO"),
        "confidence": response.get("confidence", 0.0),
        "player_message": player_message,
    }
    _response_history.append(entry)
    if len(_response_history) > MAX_RESPONSE_HISTORY:
        _response_history.pop(0)
    return entry


async def _broadcast_response(entry: Dict[str, Any]):
    dead = []
    for ws in _response_ws_clients:
        try:
            await ws.send_json(jsonable_encoder(entry))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _response_ws_clients.remove(ws)


def _safe_last_log() -> Optional[Any]:
    if not logs_db:
        return None
    return logs_db[-1]


def _get_log_id(log_entry: Any) -> int:
    """Get a unique identifier for a log entry based on its index in logs_db."""
    if log_entry in logs_db:
        return id(log_entry)  # Use Python's id() for uniqueness
    return 0


def _has_unprocessed_critical_event() -> Optional[Any]:
    """Check if there's a new critical event that hasn't been processed yet.
    
    Returns the critical event if found, None otherwise.
    """
    for event_type in CRITICAL_EVENTS:
        event = _find_last_event(event_type, limit=10)
        if event and id(event) not in _processed_log_ids:
            return event
    return None


def _recent_logs(limit: int = 50) -> List[Any]:
    if not logs_db:
        return []
    return logs_db[-max(1, int(limit)) :]


def _find_last_event(event_type: str, limit: int = 50) -> Optional[Any]:
    for e in reversed(_recent_logs(limit)):
        if getattr(e, "event_type", None) == event_type:
            return e
    return None


def _extract_threat_score(threats: Optional[list]) -> float:
    if not threats:
        return 0.0

    scores: List[float] = []
    for t in threats:
        if isinstance(t, dict):
            s = t.get("score")
            if isinstance(s, (int, float)):
                scores.append(float(s))
    if not scores:
        return 0.0
    return max(scores)


def _determine_severity_level(last: Any, threats: Optional[list]) -> str:
    """Determine severity level based on health and threats."""
    health = getattr(last, "player_health", None)
    threat_score = _extract_threat_score(threats)
    threshold = getattr(current_settings, "threat_threshold", 0.7)

    if isinstance(health, (int, float)) and health <= 4:
        return "CRITICAL"
    elif isinstance(health, (int, float)) and health <= 8:
        return "WARNING"
    elif threat_score >= float(threshold):
        return "WARNING"
    else:
        return "INFO"


def _get_fallback_rp_response(last: Any) -> Dict[str, Any]:
    """Fallback rule-based RP response when Groq is unavailable."""
    # Check for death event first (highest priority)
    death = _find_last_event("death", limit=5)
    if death is not None:
        ed = getattr(death, "event_data", None) or {}
        cause = ed.get("cause", "unknown")
        return {
            "response": f"[STATIC] О нет! Ты умер от {cause}. Может быть, в следующий раз будешь осторожнее?",
            "confidence": 1.0,
            "level": "CRITICAL",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    # Check recent critical events
    low_health = _find_last_event("low_health", limit=30)
    if low_health is not None:
        ed = getattr(low_health, "event_data", None) or {}
        hp = ed.get("health")
        food = ed.get("food")
        return {
            "response": f"[STATIC] Эй, твоё здоровье падает ({hp})! Может быть, поешь что-нибудь?",
            "confidence": 0.85,
            "level": "WARNING",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    hunger_low = _find_last_event("hunger_low", limit=40)
    if hunger_low is not None:
        ed = getattr(hunger_low, "event_data", None) or {}
        food = ed.get("food")
        # Note: Hunger value ranges from 0-20 (20 = full)
        # This response should only trigger when food < 10 (mod needs to enforce this)
        return {
            "response": f"[STATIC] Хм, ты кажется голоден ({food}). Может быть, пора что-нибудь поесть?",
            "confidence": 0.75,
            "level": "INFO",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    near_hostile = _find_last_event("near_hostile", limit=50)
    if near_hostile is not None:
        ed = getattr(near_hostile, "event_data", None) or {}
        cnt = ed.get("count")
        radius = ed.get("radius")
        types = ed.get("types")
        suffix = f" (примерно {cnt} в радиусе {radius})" if cnt is not None and radius is not None else ""
        if isinstance(types, list) and types:
            suffix += f"; типы: {', '.join([str(t) for t in types[:3]])}"
        return {
            "response": "[STATIC] Слышишь? Рядом враждебные мобы" + suffix + ". Будь осторожен!",
            "confidence": 0.8,
            "level": "WARNING",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    night = _find_last_event("night", limit=80)
    if night is not None:
        return {
            "response": "[STATIC] Ночь наступила! Может быть, спать пойдёшь или хотя бы факелы зажжёшь?",
            "confidence": 0.65,
            "level": "INFO",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    health = getattr(last, "player_health", None)
    threats = getattr(last, "threats_detected", None)

    threshold = getattr(current_settings, "threat_threshold", 0.7)
    threat_score = _extract_threat_score(threats)

    if isinstance(health, (int, float)) and health <= 6:
        return {
            "response": "[STATIC] Ты в опасности! Низкое здоровье. Может быть, спрячешься?",
            "confidence": 0.8,
            "level": "WARNING",
            "threats": threats or [],
            "source": "fallback",
        }

    if threat_score >= float(threshold):
        return {
            "response": "[STATIC] Чувствую опасность где-то рядом. Будь начеку!",
            "confidence": 0.75,
            "level": "WARNING",
            "threats": threats or [],
            "source": "fallback",
        }

    return {
        "response": "[STATIC] Как твои дела? Всё спокойно, похоже.",
        "confidence": 0.6,
        "level": "INFO",
        "threats": threats or [],
        "source": "fallback",
    }


def _format_rp_response(text: str, max_length: int = 100) -> str:
    """Format RP response text to fit on screen, breaking long lines if needed.
    
    Args:
        text: The RP response text
        max_length: Maximum length per line (for Minecraft chat display)
    
    Returns:
        Formatted text (can include newlines for long text)
    """
    if len(text) <= max_length:
        return text
    
    # Try to break at sentence boundaries
    sentences = text.split('. ')
    if len(sentences) > 1:
        # If we have multiple sentences, put them on separate lines
        return '. '.join([s.strip() for s in sentences if s.strip()])
    
    # Otherwise just return the original (Minecraft will wrap it)
    return text


def _has_situation_changed(current_response: Dict[str, Any]) -> bool:
    """Check if RP response has changed from last time.
    
    Returns True if situation has changed (different level or source),
    False if same response was just sent.
    """
    global _last_rp_response
    
    if _last_rp_response is None:
        return True
    
    # Consider changed if level or source is different
    if current_response.get("level") != _last_rp_response.get("level"):
        return True
    if current_response.get("source") != _last_rp_response.get("source"):
        return True
    # If response text significantly changed, it's different
    if current_response.get("response", "")[:20] != _last_rp_response.get("response", "")[:20]:
        return True
    
    return False


def _should_send_response(is_critical: bool = False) -> bool:
    """Check if enough time has passed since last RP response.
    
    Args:
        is_critical: If True, bypass rate limiting (for death/critical events)
    
    Returns True if response should be sent, False if rate-limited.
    """
    global _last_rp_response_time
    current_time = time.time()
    
    # Critical events bypass rate limiting
    if is_critical:
        return True
    
    if current_time - _last_rp_response_time < _min_interval_seconds:
        return False
    
    return True


@router.get("/")
async def get_rp_response() -> GroqAdvice:
    """Return a role-play response based on player's game state.

    Uses Groq LLM with last 5 logs as context. Falls back to simple response if unavailable.
    
    Critical events (death, etc.) get immediate response.
    Regular responses are rate-limited to 20 seconds minimum.
    """
    global _last_rp_response_time, _last_rp_response, _processed_log_ids

    last = _safe_last_log()
    if last is None:
        return GroqAdvice(
            response="Хм, я пока ничего не вижу. Может быть, давай запустим Minecraft?",
            confidence=0.2,
            level="INFO",
            threats=[],
            source="fallback",
        )

    # Check for unprocessed critical events (death, etc.)
    critical_event = _has_unprocessed_critical_event()
    is_critical = critical_event is not None
    
    if is_critical:
        # Mark this critical event as processed
        _processed_log_ids.add(id(critical_event))

    # Try to get LLM-based RP response (async to avoid blocking)
    if groq_client.is_available():
        recent_logs = _recent_logs(limit=5)
        llm_response = await groq_client.generate_tip_async(recent_logs)
        if llm_response:
            threats = getattr(last, "threats_detected", None) or []
            # Determine severity level based on threats and health
            level = _determine_severity_level(last, threats)
            current_response = {
                "response": _format_rp_response(llm_response),
                "confidence": 0.8,
                "level": level,
                "threats": threats,
                "source": "groq",
            }
            
            # Check if we should send this response
            if _should_send_response(is_critical=is_critical) and _has_situation_changed(current_response):
                _last_rp_response_time = time.time()
                _last_rp_response = current_response
                entry = _add_to_history(current_response)
                await _broadcast_response(entry)
                return GroqAdvice(**current_response)
            elif _last_rp_response:
                return GroqAdvice(**_last_rp_response)

    # Fallback to rule-based logic if Groq is unavailable or fails
    current_response = _get_fallback_rp_response(last)
    
    # Check if we should send this response
    if _should_send_response(is_critical=is_critical) and _has_situation_changed(current_response):
        _last_rp_response_time = time.time()
        _last_rp_response = current_response
        entry = _add_to_history(current_response)
        await _broadcast_response(entry)
        return GroqAdvice(**current_response)
    elif _last_rp_response:
        return GroqAdvice(**_last_rp_response)
    
    # First response (no previous response)
    _last_rp_response_time = time.time()
    _last_rp_response = current_response
    entry = _add_to_history(current_response)
    await _broadcast_response(entry)
    return GroqAdvice(**current_response)


@router.post("/chat")
async def player_chat_message(message: ChatMessage) -> GroqAdvice:
    """Handle player chat message and send it to LLM for RP response.
    
    Args:
        message: ChatMessage with player's text
        
    Returns:
        LLM's RP response to the player's message
    """
    import logging
    logger = logging.getLogger(__name__)
    
    text = message.text
    logger.info(f"[Chat] Received message: {text}")
    print(f"[AI Assistant API] /api/rp/chat called with: {text}")
    
    if not text or not text.strip():
        logger.warning("[Chat] Message is empty")
        return GroqAdvice(
            response="...",
            confidence=0.0,
            level="INFO",
            threats=[],
            source="chat",
        )
    
    last = _safe_last_log()
    
    # Get recent logs for context
    recent_logs = _recent_logs(limit=5)
    logger.info(f"[Chat] Using {len(recent_logs)} logs as context")
    
    # Try to get LLM response
    if groq_client.is_available():
        logger.info(f"[Chat] Groq client available, generating response...")
        print("[AI Assistant API] Groq client available, generating response...")
        
        llm_response = await groq_client.generate_chat_response_async(text, recent_logs)
        if llm_response:
            logger.info(f"[Chat] LLM response: {llm_response}")
            print(f"[AI Assistant API] LLM response: {llm_response}")
            
            threats = getattr(last, "threats_detected", None) or [] if last else []
            level = _determine_severity_level(last, threats) if last else "INFO"
            result = GroqAdvice(
                response=_format_rp_response(llm_response),
                confidence=0.9,
                level=level,
                threats=threats,
                source="chat",
            )
            entry = _add_to_history(result.model_dump(), player_message=text)
            await _broadcast_response(entry)
            return result
        else:
            logger.warning("[Chat] LLM returned None")
            print("[AI Assistant API] LLM returned None")
    else:
        logger.warning("[Chat] Groq client not available")
        print("[AI Assistant API] Groq client not available")
    
    # Fallback response
    fallback = GroqAdvice(
        response="[RP] Интересное мнение, друже!",
        confidence=0.5,
        level="INFO",
        threats=[],
        source="fallback",
    )
    entry = _add_to_history(fallback.model_dump(), player_message=text)
    await _broadcast_response(entry)
    return fallback


@router.get("/models/available")
async def get_available_llm_models() -> Dict[str, Any]:
    """Get list of available LLM models."""
    models = get_available_models()
    current = llm_config.model_type
    
    model_details = {}
    for model in models:
        model_details[model] = get_model_info(model)
    
    return {
        "current_model": current,
        "available_models": models,
        "model_details": model_details
    }


@router.post("/models/switch")
async def switch_llm_model(model_type: str) -> Dict[str, Any]:
    """Switch to a different LLM model.
    
    Args:
        model_type: Name of the model to switch to ('qwen' or 'llama')
        
    Returns:
        Updated configuration
    """
    global groq_client, llm_config
    
    try:
        updated_config = set_model_type(model_type)
        # Reinitialize groq_client with new config
        groq_client = GroqClient(llm_config=updated_config)
        
        return {
            "status": "success",
            "message": f"Switched to model: {model_type}",
            "current_model": updated_config.model_type,
            "model_info": get_model_info(model_type)
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
            "available_models": get_available_models()
        }


@router.get("/history")
async def get_response_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Get LLM response history (newest first)."""
    return list(reversed(_response_history[-max(1, limit):]))


@router.websocket("/ws")
async def responses_websocket(websocket: WebSocket):
    """WebSocket for real-time LLM response updates."""
    await websocket.accept()
    _response_ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _response_ws_clients:
            _response_ws_clients.remove(websocket)
