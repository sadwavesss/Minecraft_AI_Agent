from fastapi import APIRouter
from typing import Any, Dict, List, Optional

from api.logs import logs_db
from api.settings import current_settings

router = APIRouter(prefix="/api/advice", tags=["advice"])


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


@router.get("/")
async def get_advice() -> Dict[str, Any]:
    """Return a short actionable advice for the player.

    MVP implementation: rule-based logic from the latest known game state in logs.
    """

    last = _safe_last_log()
    if last is None:
        return {
            "advice": "Пока нет данных из игры. Запусти Minecraft с модом и подожди пару секунд.",
            "confidence": 0.2,
            "level": "INFO",
            "threats": [],
        }

    # MVP events priority (recent)
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
        }

    night = _find_last_event("night", limit=80)
    if night is not None:
        return {
            "advice": "Наступила ночь: держись освещённых мест, ставь факелы или подумай о сне, чтобы избежать лишних боёв.",
            "confidence": 0.65,
            "level": "INFO",
            "threats": getattr(last, "threats_detected", None) or [],
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
        }

    if threat_score >= float(threshold):
        return {
            "advice": "Обнаружена опасность рядом: оцени обстановку, держи дистанцию и подготовься к бою/отступлению.",
            "confidence": 0.75,
            "level": "WARNING",
            "threats": threats or [],
        }

    return {
        "advice": "Ситуация спокойная: продолжай текущую задачу, следи за ресурсами (еда/броня/факелы).",
        "confidence": 0.6,
        "level": "INFO",
        "threats": threats or [],
    }
