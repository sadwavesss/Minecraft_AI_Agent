from fastapi import APIRouter
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv

from api.logs import logs_db
from api.settings import current_settings
from api.groq_client import GroqClient
from models.groq_response import GroqAdvice

load_dotenv()

router = APIRouter(prefix="/api/advice", tags=["advice"])
groq_client = GroqClient()


def _safe_last_log() -> Optional[Any]:
    if not logs_db:
        return None
    return logs_db[-1]


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


def _get_fallback_advice(last: Any) -> Dict[str, Any]:
    """Fallback rule-based advice when Groq is unavailable."""
    # Check recent critical events
    low_health = _find_last_event("low_health", limit=30)
    if low_health is not None:
        ed = getattr(low_health, "event_data", None) or {}
        hp = ed.get("health")
        food = ed.get("food")
        return {
            "advice": f"Низкое здоровье ({hp}). Отступи, закройся блоками и срочно поешь/используй зелья.",
            "confidence": 0.85,
            "level": "WARNING",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    hunger_low = _find_last_event("hunger_low", limit=40)
    if hunger_low is not None:
        ed = getattr(hunger_low, "event_data", None) or {}
        food = ed.get("food")
        return {
            "advice": f"Низкая сытость ({food}). Поешь, чтобы не потерять спринт и регенерацию.",
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
            "advice": "Рядом враждебные мобы" + suffix + ". Держи дистанцию, проверь броню и будь готов отступить.",
            "confidence": 0.8,
            "level": "WARNING",
            "threats": getattr(last, "threats_detected", None) or [],
            "source": "fallback",
        }

    night = _find_last_event("night", limit=80)
    if night is not None:
        return {
            "advice": "Наступила ночь: держись освещённых мест, ставь факелы или подумай о сне, чтобы избежать лишних боёв.",
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
            "advice": "Низкое здоровье: отступи, закройся блоками и срочно поешь/используй зелья.",
            "confidence": 0.8,
            "level": "WARNING",
            "threats": threats or [],
            "source": "fallback",
        }

    if threat_score >= float(threshold):
        return {
            "advice": "Обнаружена опасность рядом: оцени обстановку, держи дистанцию и подготовься к бою/отступлению.",
            "confidence": 0.75,
            "level": "WARNING",
            "threats": threats or [],
            "source": "fallback",
        }

    return {
        "advice": "Ситуация спокойная: продолжай текущую задачу, следи за ресурсами (еда/броня/факелы).",
        "confidence": 0.6,
        "level": "INFO",
        "threats": threats or [],
        "source": "fallback",
    }


@router.get("/")
async def get_advice() -> Dict[str, Any]:
    """Return a short actionable advice for the player.

    Uses Groq LLM with last 5 logs as context. Falls back to simple advice if unavailable.
    """

    last = _safe_last_log()
    if last is None:
        return {
            "advice": "Пока нет данных из игры. Запусти Minecraft с модом и подожди пару секунд.",
            "confidence": 0.2,
            "level": "INFO",
            "threats": [],
            "source": "fallback",
        }

    # Try to get LLM-based advice
    if groq_client.is_available():
        recent_logs = _recent_logs(limit=5)
        llm_advice = groq_client.generate_tip(recent_logs)
        if llm_advice:
            threats = getattr(last, "threats_detected", None) or []
            # Determine severity level based on threats and health
            level = _determine_severity_level(last, threats)
            return {
                "advice": llm_advice,
                "confidence": 0.8,
                "level": level,
                "threats": threats,
                "source": "groq",
            }

    # Fallback to rule-based logic if Groq is unavailable or fails
    return _get_fallback_advice(last)
