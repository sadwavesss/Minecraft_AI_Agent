from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from api.catalog_labels import get_entity_display_name_ru, get_item_display_name_ru
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.player_state import get_player_state


router = APIRouter(prefix="/api/challenges", tags=["challenges"])

CHALLENGE_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "challenge_state.json"
MAX_HISTORY = 100

_challenge_state: Dict[str, Any] = {
    "active": None,
    "history": [],
    "updated_at": None,
}


class ChallengeCreateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    goal_type: Literal["kill", "collect"]
    goal_target_id: str
    goal_count: int = Field(default=1, ge=1)
    reward_item_id: str
    reward_count: int = Field(default=1, ge=1, le=64)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> Dict[str, Any]:
    return {"active": None, "history": [], "updated_at": None}


def _normalize_resource_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None
    if ":" not in normalized:
        normalized = f"minecraft:{normalized.replace(' ', '_').replace('-', '_')}"
    return normalized


def _normalize_count(value: Any, *, maximum: int = 64) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 1
    if count < 1:
        return 1
    return min(count, maximum)


def _trim_history() -> None:
    history = _challenge_state["history"]
    if len(history) > MAX_HISTORY:
        del history[:-MAX_HISTORY]


def save_challenge_state() -> None:
    CHALLENGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHALLENGE_STATE_PATH.write_text(json.dumps(_challenge_state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_challenge_state() -> None:
    global _challenge_state
    if not CHALLENGE_STATE_PATH.exists():
        _challenge_state = _default_state()
        return

    try:
        payload = json.loads(CHALLENGE_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _challenge_state = _default_state()
        return

    if not isinstance(payload, dict):
        _challenge_state = _default_state()
        return

    _challenge_state = {
        "active": payload.get("active") if isinstance(payload.get("active"), dict) else None,
        "history": payload.get("history") if isinstance(payload.get("history"), list) else [],
        "updated_at": payload.get("updated_at"),
    }


def reset_challenge_state(*, persist: bool = False) -> None:
    global _challenge_state
    _challenge_state = _default_state()
    if persist:
        save_challenge_state()


def _get_progress_count(challenge: Dict[str, Any], player_state: Dict[str, Any]) -> int:
    goal_type = str(challenge.get("goal_type") or "").strip().lower()
    target_id = str(challenge.get("goal_target_id") or "").strip()
    if not target_id:
        return 0

    if goal_type == "kill":
        raw_count = (player_state.get("kill_counts") or {}).get(target_id, 0)
    elif goal_type == "collect":
        raw_count = ((player_state.get("inventory") or {}).get("counts") or {}).get(target_id, 0)
    else:
        raw_count = 0

    try:
        return max(0, int(raw_count))
    except (TypeError, ValueError):
        return 0


def refresh_challenge_progress(player_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    active = _challenge_state.get("active")
    if not isinstance(active, dict):
        return get_challenge_state()

    player_state = player_state or get_player_state()
    progress_count = _get_progress_count(active, player_state)
    goal_count = _normalize_count(active.get("goal_count"))
    changed = False

    if progress_count != int(active.get("progress_count") or 0):
        active["progress_count"] = progress_count
        changed = True

    if active.get("status") == "active" and progress_count >= goal_count:
        active["status"] = "completed"
        active["completed_at"] = _now_iso()
        changed = True

    if changed:
        active["updated_at"] = _now_iso()
        _challenge_state["updated_at"] = active["updated_at"]
        save_challenge_state()

    return get_challenge_state()


def get_challenge_state() -> Dict[str, Any]:
    snapshot = deepcopy(_challenge_state)
    active = snapshot.get("active")
    if isinstance(active, dict):
        _enrich_challenge_names(active)
    history = snapshot.get("history") or []
    for challenge in history:
        if isinstance(challenge, dict):
            _enrich_challenge_names(challenge)
    return snapshot


def get_active_challenge() -> Optional[Dict[str, Any]]:
    active = get_challenge_state().get("active")
    return active if isinstance(active, dict) else None


def _enrich_challenge_names(challenge: Dict[str, Any]) -> None:
    goal_type = str(challenge.get("goal_type") or "").strip().lower()
    goal_target_id = str(challenge.get("goal_target_id") or "").strip()
    reward_item_id = str(challenge.get("reward_item_id") or "").strip()
    if goal_type == "kill":
        challenge["goal_target_name"] = get_entity_display_name_ru(goal_target_id) or goal_target_id or None
    else:
        challenge["goal_target_name"] = get_item_display_name_ru(goal_target_id) or goal_target_id or None
    challenge["reward_item_name"] = get_item_display_name_ru(reward_item_id) or reward_item_id or None


def get_challenge_prompt_context() -> str:
    state = refresh_challenge_progress()
    active = state.get("active")
    if not isinstance(active, dict):
        return "No active challenge."

    goal_type = active.get("goal_type")
    target_id = active.get("goal_target_name") or active.get("goal_target_id")
    progress_count = int(active.get("progress_count") or 0)
    goal_count = int(active.get("goal_count") or 1)
    reward_item_id = active.get("reward_item_name") or active.get("reward_item_id")
    reward_count = int(active.get("reward_count") or 1)
    status = active.get("status") or "active"

    lines = [
        "Active challenge:",
        f"- title: {active.get('title') or 'Untitled challenge'}",
        f"- status: {status}",
        f"- goal: {goal_type} {target_id} x{goal_count}",
        f"- progress: {progress_count}/{goal_count}",
        f"- reward: {reward_item_id} x{reward_count}",
    ]
    if active.get("description"):
        lines.append(f"- description: {active['description']}")
    return "\n".join(lines)


def create_challenge(
    *,
    goal_type: str,
    goal_target_id: str,
    goal_count: Any,
    reward_item_id: str,
    reward_count: Any,
    title: Optional[str] = None,
    description: Optional[str] = None,
    source: str = "chat",
) -> Dict[str, Any]:
    active = _challenge_state.get("active")
    if isinstance(active, dict):
        refresh_challenge_progress()
        active = _challenge_state.get("active")
        if isinstance(active, dict):
            return {
                "ok": False,
                "error_type": "active_exists",
                "error": "У тебя уже есть активный челлендж. Сначала заверши или отмени его.",
                "challenge": deepcopy(active),
            }

    normalized_goal_type = str(goal_type or "").strip().lower()
    if normalized_goal_type not in {"kill", "collect"}:
        return {"ok": False, "error_type": "validation", "error": "Поддерживаются только цели `kill` и `collect`."}

    normalized_target_id = _normalize_resource_id(goal_target_id)
    normalized_reward_item_id = _normalize_resource_id(reward_item_id)
    if not normalized_target_id or not normalized_reward_item_id:
        return {"ok": False, "error_type": "validation", "error": "Не удалось нормализовать цель или награду челленджа."}

    normalized_goal_count = _normalize_count(goal_count, maximum=9999)
    normalized_reward_count = _normalize_count(reward_count, maximum=64)

    challenge_id = f"challenge-{uuid4().hex[:10]}"
    created_at = _now_iso()
    challenge = {
        "id": challenge_id,
        "title": title or ("Охота" if normalized_goal_type == "kill" else "Сбор ресурсов"),
        "description": description
        or (
            f"Убей {normalized_goal_count} x {normalized_target_id} и получи {normalized_reward_count} x {normalized_reward_item_id}."
            if normalized_goal_type == "kill"
            else f"Собери {normalized_goal_count} x {normalized_target_id} и получи {normalized_reward_count} x {normalized_reward_item_id}."
        ),
        "status": "active",
        "goal_type": normalized_goal_type,
        "goal_target_id": normalized_target_id,
        "goal_count": normalized_goal_count,
        "progress_count": 0,
        "reward_type": "give_item",
        "reward_item_id": normalized_reward_item_id,
        "reward_count": normalized_reward_count,
        "source": source,
        "created_at": created_at,
        "completed_at": None,
        "claimed_at": None,
        "updated_at": created_at,
    }

    _challenge_state["active"] = challenge
    _challenge_state["updated_at"] = created_at
    refresh_challenge_progress()
    save_challenge_state()

    return {
        "ok": True,
        "challenge": deepcopy(_challenge_state["active"]),
        "summary": f"Зафиксировал челлендж: {challenge['description']}",
    }


def cancel_active_challenge(challenge_id: str) -> Dict[str, Any]:
    active = _challenge_state.get("active")
    if not isinstance(active, dict):
        return {"ok": False, "error_type": "not_found", "error": "Активного челленджа сейчас нет."}

    if challenge_id != str(active.get("id")):
        return {"ok": False, "error_type": "not_found", "error": "Не нашёл такой активный челлендж."}

    archived = deepcopy(active)
    archived["status"] = "cancelled"
    archived["updated_at"] = _now_iso()
    _challenge_state["history"].append(archived)
    _trim_history()
    _challenge_state["active"] = None
    _challenge_state["updated_at"] = archived["updated_at"]
    save_challenge_state()
    return {"ok": True, "challenge": archived, "summary": "Челлендж отменён."}


def claim_active_challenge_reward(challenge_id: Optional[str] = None) -> Dict[str, Any]:
    refresh_challenge_progress()
    active = _challenge_state.get("active")
    if not isinstance(active, dict):
        return {
            "ok": False,
            "tool_name": "claim_challenge_reward",
            "execute": False,
            "error_type": "not_found",
            "error": "Сейчас нет активного челленджа для получения награды.",
        }

    if challenge_id and challenge_id != str(active.get("id")):
        return {
            "ok": False,
            "tool_name": "claim_challenge_reward",
            "execute": False,
            "error_type": "not_found",
            "error": "Не нашёл такой челлендж для получения награды.",
        }

    if active.get("status") != "completed":
        progress_count = int(active.get("progress_count") or 0)
        goal_count = int(active.get("goal_count") or 1)
        return {
            "ok": False,
            "tool_name": "claim_challenge_reward",
            "execute": False,
            "error_type": "not_ready",
            "error": f"Челлендж ещё не выполнен: {progress_count}/{goal_count}.",
            "challenge": deepcopy(active),
        }

    from api.tool_service import execute_tool_call

    reward_result = execute_tool_call(
        "give_item",
        {"item_query": active.get("reward_item_id"), "count": active.get("reward_count")},
    )
    if not reward_result.get("ok"):
        return {
            **reward_result,
            "tool_name": "claim_challenge_reward",
            "challenge": deepcopy(active),
        }

    claimed = deepcopy(active)
    claimed["status"] = "claimed"
    claimed["claimed_at"] = _now_iso()
    claimed["updated_at"] = claimed["claimed_at"]
    _challenge_state["history"].append(claimed)
    _trim_history()
    _challenge_state["active"] = None
    _challenge_state["updated_at"] = claimed["claimed_at"]
    save_challenge_state()

    reward_result["tool_name"] = "claim_challenge_reward"
    reward_result["challenge_id"] = claimed["id"]
    reward_result["challenge"] = claimed
    reward_result["summary"] = (
        f"Челлендж выполнен. Выдаю награду: {claimed['reward_count']} x {claimed['reward_item_id']}."
    )
    return reward_result


@router.get("/")
async def get_challenges_endpoint():
    return refresh_challenge_progress()


@router.get("/active")
async def get_active_challenge_endpoint():
    return {"active": refresh_challenge_progress().get("active")}


@router.get("/completed")
async def get_completed_challenges_endpoint():
    state = refresh_challenge_progress()
    history = [
        challenge
        for challenge in state.get("history", [])
        if str(challenge.get("status") or "") in {"claimed", "cancelled", "completed"}
    ]
    return {"history": history}


@router.post("/")
async def create_challenge_endpoint(payload: ChallengeCreateRequest):
    result = create_challenge(
        goal_type=payload.goal_type,
        goal_target_id=payload.goal_target_id,
        goal_count=payload.goal_count,
        reward_item_id=payload.reward_item_id,
        reward_count=payload.reward_count,
        title=payload.title,
        description=payload.description,
        source="api",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Не удалось создать челлендж.")
    return result


@router.post("/{challenge_id}/claim")
async def claim_challenge_endpoint(challenge_id: str):
    result = claim_active_challenge_reward(challenge_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Не удалось забрать награду.")
    return result


@router.post("/{challenge_id}/cancel")
async def cancel_challenge_endpoint(challenge_id: str):
    result = cancel_active_challenge(challenge_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Не удалось отменить челлендж.")
    return result


load_challenge_state()
