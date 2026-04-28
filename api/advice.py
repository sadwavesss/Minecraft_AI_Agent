from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect
from typing import Any, Dict, List, Optional, Set
import asyncio
import json
import logging
import re
from dotenv import load_dotenv
from datetime import datetime, timezone
import time

from api.challenges import get_active_challenge, refresh_challenge_progress
from api.console_utils import make_console_safe
from api.logs import logs_db
from api.settings import current_settings
from api.groq_client import GroqClient
from api.minecraft_catalog import resolve_item_id_from_text
from api.llm_config_manager import get_llm_config, set_model_type, get_available_models, get_model_info
from api.tool_service import execute_tool_call, get_tool_registry
from models.groq_response import GroqAdvice, ChatMessage

load_dotenv()

router = APIRouter(prefix="/api/rp", tags=["roleplay"])
logger = logging.getLogger(__name__)

# Initialize groq_client with LLM config
llm_config = get_llm_config()
groq_client = GroqClient(llm_config=llm_config)

# Critical events that require immediate response (no rate limiting)
CRITICAL_EVENTS = {"death"}
SUPPORTED_ACTION_TYPES = {"give", "summon"}
DEFAULT_COMMAND_COUNT = 1
MAX_COMMAND_COUNT = 64
ITEM_ID_PATTERN = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
ACTION_REQUEST_PATTERNS = (
    "дай",
    "выдай",
    "give me",
    "give ",
    "забери",
    "удали",
    "убери",
    "remove",
    "take ",
    "clear ",
    "призови",
    "спавн",
    "заспавн",
    "summon",
    "получи",
)
CHALLENGE_CLAIM_PATTERNS = (
    "забрать награду",
    "получить награду",
    "выдай награду",
    "claim reward",
)
CHALLENGE_STATUS_PATTERNS = (
    "какой у меня челлендж",
    "что за челлендж",
    "мой челлендж",
    "текущий челлендж",
    "прогресс челленджа",
)
REQUEST_COUNT_PATTERN = re.compile(r"(?<!\w)(\d{1,3})(?!\w)")

# Rate limiting and change detection
_last_rp_response_time = 0
_last_rp_response = None
_min_interval_seconds = 20  # Default 20 seconds between routine RP responses
_processed_log_ids: Set[int] = set()  # Track which logs we've responded to
RP_LLM_TIMEOUT_SECONDS = 6.0

# Response history for the admin panel
_response_history: List[Dict[str, Any]] = []
MAX_RESPONSE_HISTORY = 200
_response_ws_clients: List[WebSocket] = []
_conversation_history: List[Dict[str, str]] = []
MAX_CONVERSATION_HISTORY = 10


def _safe_console_log(message: Any, *, level: str = "info", print_message: bool = True) -> None:
    safe_message = make_console_safe(message)
    getattr(logger, level, logger.info)(safe_message)
    if print_message:
        print(safe_message)


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


def _append_conversation_message(role: str, content: str):
    normalized_role = (role or "").strip().lower()
    normalized_content = (content or "").strip()
    if normalized_role not in {"user", "assistant", "tool", "tool_result"} or not normalized_content:
        return

    _conversation_history.append({"role": normalized_role, "content": normalized_content})
    if len(_conversation_history) > MAX_CONVERSATION_HISTORY:
        del _conversation_history[:-MAX_CONVERSATION_HISTORY]


def _conversation_window(limit: int = MAX_CONVERSATION_HISTORY) -> List[Dict[str, str]]:
    return list(_conversation_history[-max(1, int(limit)) :])


def _response_text_for_conversation(response: GroqAdvice) -> str:
    return (response.response or response.error or "").strip()


async def _store_chat_result(result: GroqAdvice, player_message: str, *, add_user: bool = True) -> GroqAdvice:
    if add_user:
        _append_conversation_message("user", player_message)
    _append_conversation_message("assistant", _response_text_for_conversation(result))
    entry = _add_to_history(result.model_dump(), player_message=player_message)
    await _broadcast_response(entry)
    return result


def _format_tool_call_for_history(tool_name: str, arguments: Any) -> str:
    return f"{tool_name}({json.dumps(arguments or {}, ensure_ascii=False)})"


def _format_tool_result_for_history(tool_result: Dict[str, Any]) -> str:
    return json.dumps(tool_result, ensure_ascii=False)


def _append_tool_context(tool_name: str, arguments: Any, tool_result: Dict[str, Any]):
    _append_conversation_message("tool", _format_tool_call_for_history(tool_name, arguments))
    _append_conversation_message("tool_result", _format_tool_result_for_history(tool_result))


def _build_response_from_tool_result(tool_result: Dict[str, Any], spoken_response: Optional[str], last: Any) -> GroqAdvice:
    response_text = (spoken_response or "").strip() or str(tool_result.get("summary") or "").strip()
    if not tool_result.get("ok"):
        error_message = str(tool_result.get("error") or "Не удалось выполнить tool.").strip()
        return _build_action_error(last, _merge_action_message(response_text, error_message))

    if not response_text:
        response_text = "Готово."

    return _build_chat_result(
        response=response_text,
        last=last,
        source="chat",
        confidence=0.9,
        mode="action" if bool(tool_result.get("execute")) else "chat",
        execute=bool(tool_result.get("execute")),
        action_type=str(tool_result.get("action_type") or "").strip() or None,
        item_id=_normalize_item_id(tool_result.get("item_id")),
        item_count=_normalize_item_count(tool_result.get("item_count")) if tool_result.get("item_count") is not None else None,
        entity_id=_normalize_entity_id(tool_result.get("entity_id")),
        entity_count=_normalize_entity_count(tool_result.get("entity_count")) if tool_result.get("entity_count") is not None else None,
        command=tool_result.get("command") if tool_result.get("execute") else None,
        error=tool_result.get("error"),
    )


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


def _should_use_llm_for_rp(*, is_critical: bool) -> bool:
    # Passive RP polling should stay cheap. Reserve LLM usage for critical or
    # high-value events so routine polling does not burn Groq quota.
    return is_critical and groq_client.is_available()


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


def _looks_like_action_request(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(token in lowered for token in ACTION_REQUEST_PATTERNS)


def _normalize_request_text(text: str) -> str:
    normalized = (text or "").lower().replace("ё", "е")
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = re.sub(r"[^\w\s:]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _extract_requested_count(text: str) -> int:
    match = REQUEST_COUNT_PATTERN.search(text or "")
    if not match:
        return DEFAULT_COMMAND_COUNT
    return _normalize_item_count(match.group(1))


def _extract_requested_item_id(text: str) -> Optional[str]:
    resolution = resolve_item_id_from_text(text)
    if resolution.get("status") != "resolved":
        return None
    return _normalize_item_id(resolution.get("item_id"))


def _resolve_direct_action_request(text: str, *, force_lookup: bool = False) -> Dict[str, Any]:
    if not force_lookup and not _looks_like_action_request(text):
        return {"status": "not_action"}

    resolution = resolve_item_id_from_text(text)
    status = resolution.get("status")
    if status == "resolved":
        return resolution
    if status == "ambiguous":
        candidates = [match.get("display_name_ru") or match.get("id") for match in resolution.get("matches", [])[:3]]
        candidate_text = ", ".join([str(candidate) for candidate in candidates if candidate])
        return {
            "status": "ambiguous",
            "message": f"Запрос неоднозначен. Уточни предмет: {candidate_text}." if candidate_text else "Запрос неоднозначен. Уточни, какой именно предмет или блок нужен.",
            "matches": resolution.get("matches", []),
        }
    return {"status": "not_found"}


def _build_direct_action_payload(text: str) -> Optional[Dict[str, Any]]:
    resolution = _resolve_direct_action_request(text)
    if resolution.get("status") != "resolved":
        return None

    item_id = _normalize_item_id(resolution.get("item_id"))
    if item_id is None:
        return None

    count = _extract_requested_count(text)
    matched_name = resolution.get("display_name_ru") or item_id
    return {
        "mode": "action",
        "spoken_response": f"Выдаю {count} x {matched_name}.",
        "action_type": "give",
        "item_id": item_id,
        "count": count,
        "execute": True,
        "error": None,
    }


def _looks_like_summon_request(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(token in lowered for token in ("призови", "заспавн", "спавн", "summon", "spawn"))


def _looks_like_remove_request(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(token in lowered for token in ("забери", "удали", "убери", "remove", "take ", "clear "))


def _looks_like_claim_challenge_request(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(token in lowered for token in CHALLENGE_CLAIM_PATTERNS)


def _looks_like_challenge_status_request(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(token in lowered for token in CHALLENGE_STATUS_PATTERNS)


def _build_challenge_status_response(last: Any) -> GroqAdvice:
    refresh_challenge_progress()
    active = get_active_challenge()
    if not active:
        return _build_chat_result(
            response="Сейчас активного челленджа нет.",
            last=last,
            source="chat",
            confidence=0.9,
            mode="chat",
        )

    progress_count = int(active.get("progress_count") or 0)
    goal_count = int(active.get("goal_count") or 1)
    reward_item_id = str(active.get("reward_item_id") or "").strip()
    reward_count = int(active.get("reward_count") or 1)
    status = str(active.get("status") or "active")
    title = str(active.get("title") or "Челлендж").strip()
    goal_type = str(active.get("goal_type") or "").strip()
    goal_target_id = str(active.get("goal_target_id") or "").strip()

    if status == "completed":
        response = (
            f"{title}: цель уже выполнена. "
            f"Условие было {goal_type} {goal_target_id} x{goal_count}. "
            f"Можешь забрать награду: {reward_item_id} x{reward_count}."
        )
    else:
        response = (
            f"{title}: {goal_type} {goal_target_id} x{goal_count}. "
            f"Прогресс {progress_count}/{goal_count}. "
            f"Награда: {reward_item_id} x{reward_count}."
        )

    return _build_chat_result(
        response=response,
        last=last,
        source="chat",
        confidence=0.9,
        mode="chat",
    )


def _normalize_item_id(item_id: Any) -> Optional[str]:
    if not isinstance(item_id, str):
        return None

    normalized = item_id.strip().lower()
    if not normalized:
        return None

    normalized = normalized.replace(" ", "_").replace("-", "_")
    if ":" not in normalized:
        normalized = f"minecraft:{normalized}"

    if not ITEM_ID_PATTERN.fullmatch(normalized):
        return None

    return normalized


def _normalize_entity_id(entity_id: Any) -> Optional[str]:
    return _normalize_item_id(entity_id)


def _normalize_item_count(count: Any) -> int:
    try:
        normalized = int(count)
    except (TypeError, ValueError):
        normalized = DEFAULT_COMMAND_COUNT

    if normalized < 1:
        return DEFAULT_COMMAND_COUNT
    if normalized > MAX_COMMAND_COUNT:
        return MAX_COMMAND_COUNT
    return normalized


def _normalize_entity_count(count: Any) -> int:
    try:
        normalized = int(count)
    except (TypeError, ValueError):
        normalized = DEFAULT_COMMAND_COUNT

    if normalized < 1:
        return DEFAULT_COMMAND_COUNT
    if normalized > 16:
        return 16
    return normalized


def _build_give_command(item_id: str, count: int) -> str:
    return f"/give @s {item_id} {count}"


def _build_chat_result(
    *,
    response: str,
    last: Any,
    source: str = "chat",
    confidence: float = 0.9,
    mode: str = "chat",
    execute: bool = False,
    action_type: Optional[str] = None,
    item_id: Optional[str] = None,
    item_count: Optional[int] = None,
    entity_id: Optional[str] = None,
    entity_count: Optional[int] = None,
    command: Optional[str] = None,
    error: Optional[str] = None,
    fallback: bool = False,
) -> GroqAdvice:
    threats = getattr(last, "threats_detected", None) or [] if last else []
    level = _determine_severity_level(last, threats) if last else "INFO"
    return GroqAdvice(
        response=_format_rp_response(response),
        confidence=confidence,
        level=level,
        threats=threats,
        source=source,
        fallback=fallback,
        mode=mode,
        execute=execute,
        action_type=action_type,
        item_id=item_id,
        item_count=item_count,
        entity_id=entity_id,
        entity_count=entity_count,
        command=command,
        error=error,
    )


def _build_action_error(last: Any, message: str, *, source: str = "chat", fallback: bool = False) -> GroqAdvice:
    return _build_chat_result(
        response=message,
        last=last,
        source=source,
        confidence=0.5 if fallback else 0.75,
        mode="action",
        execute=False,
        error=message,
        fallback=fallback,
    )


def _merge_action_message(spoken_response: Optional[str], error_message: str) -> str:
    response = (spoken_response or "").strip()
    if not response:
        return error_message
    return f"{response} {error_message}".strip()


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def _build_chat_action_response(action_payload: Dict[str, Any], last: Any) -> Optional[GroqAdvice]:
    mode = str(action_payload.get("mode") or "chat").strip().lower()
    spoken_response = str(action_payload.get("spoken_response") or "").strip()

    tool_name = str(action_payload.get("tool_name") or "").strip().lower()
    if not tool_name:
        legacy_action_type = str(action_payload.get("action_type") or "").strip().lower()
        if legacy_action_type == "give":
            tool_name = "give_item"
        elif legacy_action_type == "summon":
            tool_name = "summon_entity"
        elif legacy_action_type == "clear":
            tool_name = "remove_item"

    if not tool_name and mode not in {"tool", "action"}:
        if not spoken_response:
            return None
        return _build_chat_result(
            response=spoken_response,
            last=last,
            source="chat",
            confidence=0.9,
            mode="chat",
            execute=False,
        )

    if tool_name not in {"give_item", "remove_item", "summon_entity", "create_challenge", "claim_challenge_reward"}:
        return _build_action_error(last, _merge_action_message(spoken_response, "Я пока умею вызывать только tools `give_item`, `remove_item`, `summon_entity`, `create_challenge` и `claim_challenge_reward`."))

    arguments = action_payload.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}

    tool_arguments = dict(arguments)
    if tool_name in {"give_item", "remove_item"}:
        item_query = tool_arguments.get("item_query")
        if item_query is None:
            item_query = action_payload.get("item_query")
        if item_query is None and action_payload.get("item_id") is not None:
            item_query = action_payload.get("item_id")
        if not item_query:
            error_message = "Не смог понять, какой предмет нужно выдать." if tool_name == "give_item" else "Не смог понять, какой предмет нужно забрать."
            return _build_action_error(last, _merge_action_message(spoken_response, error_message))
        tool_arguments["item_query"] = item_query
        tool_arguments["count"] = tool_arguments.get("count", action_payload.get("count"))
    elif tool_name == "summon_entity":
        entity_query = tool_arguments.get("entity_query")
        if entity_query is None:
            entity_query = action_payload.get("entity_query")
        if entity_query is None and action_payload.get("entity_id") is not None:
            entity_query = action_payload.get("entity_id")
        if not entity_query:
            return _build_action_error(last, _merge_action_message(spoken_response, "Не смог понять, какое существо нужно призвать."))
        tool_arguments["entity_query"] = entity_query
        tool_arguments["count"] = tool_arguments.get("count", action_payload.get("count"))
    elif tool_name == "create_challenge":
        goal_type = tool_arguments.get("goal_type", action_payload.get("goal_type"))
        target_query = tool_arguments.get("target_query", action_payload.get("target_query"))
        reward_item_query = tool_arguments.get("reward_item_query", action_payload.get("reward_item_query"))
        tool_arguments["goal_type"] = goal_type
        tool_arguments["target_query"] = target_query
        tool_arguments["reward_item_query"] = reward_item_query
        tool_arguments["goal_count"] = tool_arguments.get("goal_count", action_payload.get("goal_count"))
        tool_arguments["reward_count"] = tool_arguments.get("reward_count", action_payload.get("reward_count"))
        tool_arguments["title"] = tool_arguments.get("title", action_payload.get("title"))
        if not goal_type or not target_query or not reward_item_query:
            return _build_action_error(last, _merge_action_message(spoken_response, "Не смог понять условие или награду челленджа."))
    else:
        if tool_arguments.get("challenge_id") is None and action_payload.get("challenge_id") is not None:
            tool_arguments["challenge_id"] = action_payload.get("challenge_id")

    tool_result = execute_tool_call(tool_name, tool_arguments)
    if not tool_result.get("ok"):
        return _build_action_error(last, _merge_action_message(spoken_response, str(tool_result.get("error") or "Не удалось выполнить tool.")))

    response_text = spoken_response or str(tool_result.get("summary") or "").strip() or "Готово."
    should_execute = _coerce_bool(
        action_payload.get("should_execute"),
        default=_coerce_bool(action_payload.get("execute"), default=True),
    )

    if not should_execute:
        return _build_chat_result(
            response=response_text,
            last=last,
            source="chat",
            confidence=0.9,
            mode="action",
            execute=False,
            action_type=str(tool_result.get("action_type") or ""),
            item_id=_normalize_item_id(tool_result.get("item_id")),
            item_count=_normalize_item_count(tool_result.get("item_count")) if tool_result.get("item_count") is not None else None,
            entity_id=_normalize_entity_id(tool_result.get("entity_id")),
            entity_count=_normalize_entity_count(tool_result.get("entity_count")) if tool_result.get("entity_count") is not None else None,
        )

    return _build_response_from_tool_result(tool_result, response_text, last)


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

    # Routine passive polling should read cached/stateful responses cheaply.
    # Only critical events are allowed to invoke the LLM on this endpoint.
    if _should_use_llm_for_rp(is_critical=is_critical):
        recent_logs = _recent_logs(limit=5)
        try:
            llm_response = await asyncio.wait_for(
                groq_client.generate_tip_async(recent_logs),
                timeout=RP_LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[RP] %s tip generation exceeded %.1fs; returning cached or fallback response",
                groq_client.get_source_name(),
                RP_LLM_TIMEOUT_SECONDS,
            )
            if _last_rp_response:
                return GroqAdvice(**_last_rp_response)
            llm_response = None
        if llm_response:
            threats = getattr(last, "threats_detected", None) or []
            # Determine severity level based on threats and health
            level = _determine_severity_level(last, threats)
            current_response = {
                "response": _format_rp_response(llm_response),
                "confidence": 0.8,
                "level": level,
                "threats": threats,
                "source": groq_client.get_source_name(),
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
    text = message.text
    _safe_console_log(f"[Chat] Received message: {text}", print_message=False)
    _safe_console_log(f"[AI Assistant API] /api/rp/chat called with: {text}")
    
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
    conversation_history = _conversation_window()
    available_tools = get_tool_registry()
    logger.info(f"[Chat] Using {len(recent_logs)} logs as context")

    # Interactive chat uses a lightweight tool-service loop:
    # assistant decision -> optional tool call -> final assistant response.
    if groq_client.is_available():
        _safe_console_log(f"[Chat] {groq_client.provider} client available, generating response...", print_message=False)
        _safe_console_log(f"[AI Assistant API] {groq_client.provider} client available, generating response...")

        decision_payload = await groq_client.generate_tool_decision_async(
            text,
            recent_logs,
            conversation_history,
            available_tools,
        )
        if decision_payload:
            tool_call = decision_payload.get("tool_call")
            assistant_response = str(decision_payload.get("assistant_response") or "").strip()

            if isinstance(tool_call, dict) and tool_call.get("name"):
                tool_name = str(tool_call.get("name") or "").strip()
                tool_arguments = tool_call.get("arguments") or {}
                tool_result = execute_tool_call(tool_name, tool_arguments)

                _append_conversation_message("user", text)
                _append_tool_context(tool_name, tool_arguments, tool_result)

                final_response_text = await groq_client.generate_tool_followup_async(
                    text,
                    recent_logs,
                    _conversation_window(),
                    tool_result,
                )
                final_response = _build_response_from_tool_result(tool_result, final_response_text, last)
                _safe_console_log(f"[Chat] Tool loop response: {final_response.model_dump()}", print_message=False)
                _safe_console_log(f"[AI Assistant API] Tool loop response: {final_response.model_dump()}")
                return await _store_chat_result(final_response, text, add_user=False)

            if assistant_response:
                result = _build_chat_result(
                    response=assistant_response,
                    last=last,
                    source="chat",
                    confidence=0.9,
                    mode="chat",
                )
                _safe_console_log(f"[Chat] Assistant response without tool: {result.model_dump()}", print_message=False)
                _safe_console_log(f"[AI Assistant API] Assistant response without tool: {result.model_dump()}")
                return await _store_chat_result(result, text)

        logger.warning("[Chat] Tool decision payload was empty or invalid")
        print("[AI Assistant API] Tool decision payload was empty or invalid")
    else:
        _safe_console_log(f"[Chat] {groq_client.provider} client not available", level="warning", print_message=False)
        _safe_console_log(f"[AI Assistant API] {groq_client.provider} client not available")

    if _looks_like_summon_request(text):
        direct_summon_result = execute_tool_call(
            "summon_entity",
            {"entity_query": text, "count": _extract_requested_count(text)},
        )
        direct_summon_response = _build_response_from_tool_result(
            direct_summon_result,
            None if direct_summon_result.get("ok") else "",
            last,
        )
        _safe_console_log(f"[Chat] Direct summon response: {direct_summon_response.model_dump()}", print_message=False)
        _safe_console_log(f"[AI Assistant API] Direct summon response: {direct_summon_response.model_dump()}")
        return await _store_chat_result(direct_summon_response, text)

    if _looks_like_remove_request(text):
        direct_remove_result = execute_tool_call(
            "remove_item",
            {"item_query": text, "count": _extract_requested_count(text)},
        )
        direct_remove_response = _build_response_from_tool_result(
            direct_remove_result,
            None if direct_remove_result.get("ok") else "",
            last,
        )
        _safe_console_log(f"[Chat] Direct remove response: {direct_remove_response.model_dump()}", print_message=False)
        _safe_console_log(f"[AI Assistant API] Direct remove response: {direct_remove_response.model_dump()}")
        return await _store_chat_result(direct_remove_response, text)

    if _looks_like_claim_challenge_request(text):
        direct_claim_result = execute_tool_call("claim_challenge_reward", {})
        direct_claim_response = _build_response_from_tool_result(
            direct_claim_result,
            None if direct_claim_result.get("ok") else "",
            last,
        )
        _safe_console_log(f"[Chat] Direct challenge claim response: {direct_claim_response.model_dump()}", print_message=False)
        _safe_console_log(f"[AI Assistant API] Direct challenge claim response: {direct_claim_response.model_dump()}")
        return await _store_chat_result(direct_claim_response, text)

    if _looks_like_challenge_status_request(text):
        challenge_status_response = _build_challenge_status_response(last)
        _safe_console_log(f"[Chat] Challenge status response: {challenge_status_response.model_dump()}", print_message=False)
        _safe_console_log(f"[AI Assistant API] Challenge status response: {challenge_status_response.model_dump()}")
        return await _store_chat_result(challenge_status_response, text)

    direct_action_resolution = _resolve_direct_action_request(text)
    if direct_action_resolution.get("status") == "ambiguous":
        direct_action_error = _build_action_error(last, direct_action_resolution["message"])
        return await _store_chat_result(direct_action_error, text)

    direct_action_payload = _build_direct_action_payload(text)
    if direct_action_payload:
        direct_action_response = _build_chat_action_response(direct_action_payload, last)
        if direct_action_response:
            _safe_console_log(f"[Chat] Direct action response: {direct_action_response.model_dump()}", print_message=False)
            _safe_console_log(f"[AI Assistant API] Direct action response: {direct_action_response.model_dump()}")
            return await _store_chat_result(direct_action_response, text)

    if groq_client.is_available():
        fallback_chat = await groq_client.generate_chat_response_async(text, recent_logs, conversation_history)
        if fallback_chat:
            fallback_chat_response = _build_chat_result(
                response=fallback_chat,
                last=last,
                source="chat",
                confidence=0.75,
                mode="chat",
            )
            _safe_console_log(f"[Chat] Fallback chat response: {fallback_chat_response.model_dump()}", print_message=False)
            _safe_console_log(f"[AI Assistant API] Fallback chat response: {fallback_chat_response.model_dump()}")
            return await _store_chat_result(fallback_chat_response, text)

    if _looks_like_action_request(text):
        fallback_action = _build_action_error(
            last,
            "Не могу выполнить выдачу предмета: LLM недоступна или не смогла разобрать запрос.",
            source="fallback",
            fallback=True,
        )
        return await _store_chat_result(fallback_action, text)

    # Fallback response
    fallback = _build_chat_result(
        response="[RP] Интересное мнение, друже!",
        last=last,
        source="fallback",
        confidence=0.5,
        mode="chat",
        fallback=True,
    )
    return await _store_chat_result(fallback, text)


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
