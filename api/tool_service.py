import re
from typing import Any, Dict, List

from api.challenges import claim_active_challenge_reward, create_challenge
from api.entity_catalog import resolve_entity_id_from_text
from api.minecraft_catalog import resolve_item_id_from_text


DEFAULT_COMMAND_COUNT = 1
MAX_ITEM_COUNT = 64
MAX_SUMMON_COUNT = 16
RESOURCE_ID_PATTERN = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")


def _normalize_resource_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    normalized = normalized.replace(" ", "_").replace("-", "_")
    if ":" not in normalized:
        normalized = f"minecraft:{normalized}"

    if not RESOURCE_ID_PATTERN.fullmatch(normalized):
        return None
    return normalized


def _normalize_count(count: Any, *, maximum: int) -> int:
    try:
        normalized = int(count)
    except (TypeError, ValueError):
        normalized = DEFAULT_COMMAND_COUNT

    if normalized < 1:
        return DEFAULT_COMMAND_COUNT
    if normalized > maximum:
        return maximum
    return normalized


def _build_give_command(item_id: str, count: int) -> str:
    return f"/give @s {item_id} {count}"


def _build_clear_command(item_id: str, count: int) -> str:
    return f"/clear @s {item_id} {count}"


def _build_summon_command(entity_id: str, count: int) -> str:
    return "\n".join([f"/summon {entity_id} ~ ~ ~" for _ in range(max(1, count))])


def get_tool_registry() -> List[Dict[str, Any]]:
    return [
        {
            "name": "give_item",
            "description": "Give the player a Minecraft item or block after server-side validation.",
            "arguments": {
                "item_query": "string, required, the human wording for the requested item or block",
                "count": "integer, optional, from 1 to 64",
            },
        },
        {
            "name": "remove_item",
            "description": "Remove a Minecraft item or block from the player's inventory after server-side validation.",
            "arguments": {
                "item_query": "string, required, the human wording for the item or block to remove",
                "count": "integer, optional, from 1 to 64",
            },
        },
        {
            "name": "summon_entity",
            "description": "Summon basic Minecraft mobs near the player after server-side validation.",
            "arguments": {
                "entity_query": "string, required, the human wording for the requested mob",
                "count": "integer, optional, from 1 to 16",
            },
        },
        {
            "name": "create_challenge",
            "description": "Create one active Minecraft challenge from chat after validating the goal and reward on the server.",
            "arguments": {
                "goal_type": "string, required, one of: kill, collect",
                "target_query": "string, required, the mob or item mentioned in the goal",
                "goal_count": "integer, optional, how many kills/items are needed",
                "reward_item_query": "string, required, reward item or block",
                "reward_count": "integer, optional, reward amount from 1 to 64",
                "title": "string, optional, short challenge title",
            },
        },
        {
            "name": "claim_challenge_reward",
            "description": "Claim the reward for the currently completed active challenge.",
            "arguments": {
                "challenge_id": "string, optional, active challenge id if the model wants to be explicit",
            },
        },
    ]


def _execute_give_item(arguments: Dict[str, Any]) -> Dict[str, Any]:
    item_query = arguments.get("item_query")
    if not isinstance(item_query, str) or not item_query.strip():
        return {
            "ok": False,
            "tool_name": "give_item",
            "execute": False,
            "error_type": "validation",
            "error": "Tool `give_item` требует непустой `item_query`.",
        }

    resolution = resolve_item_id_from_text(item_query)
    status = resolution.get("status")
    if status == "ambiguous":
        candidates = [match.get("display_name_ru") or match.get("id") for match in resolution.get("matches", [])[:3]]
        candidate_text = ", ".join([str(candidate) for candidate in candidates if candidate])
        return {
            "ok": False,
            "tool_name": "give_item",
            "execute": False,
            "error_type": "ambiguous",
            "error": f"Запрос неоднозначен. Уточни предмет: {candidate_text}." if candidate_text else "Запрос неоднозначен. Уточни предмет.",
            "matches": resolution.get("matches", []),
            "arguments": {"item_query": item_query},
        }

    if status != "resolved":
        return {
            "ok": False,
            "tool_name": "give_item",
            "execute": False,
            "error_type": "not_found",
            "error": "Не смог определить предмет или блок для выдачи.",
            "arguments": {"item_query": item_query},
        }

    item_id = _normalize_resource_id(resolution.get("item_id"))
    if item_id is None:
        return {
            "ok": False,
            "tool_name": "give_item",
            "execute": False,
            "error_type": "validation",
            "error": "Не смог понять, какой предмет нужно выдать.",
            "arguments": {"item_query": item_query},
        }

    count = _normalize_count(arguments.get("count"), maximum=MAX_ITEM_COUNT)
    resolved_name = resolution.get("display_name_ru") or item_id
    return {
        "ok": True,
        "tool_name": "give_item",
        "execute": True,
        "action_type": "give",
        "item_id": item_id,
        "item_count": count,
        "resolved_name": resolved_name,
        "command": _build_give_command(item_id, count),
        "arguments": {"item_query": item_query, "count": count},
        "summary": f"Выдаю {count} x {resolved_name}.",
    }


def _execute_remove_item(arguments: Dict[str, Any]) -> Dict[str, Any]:
    item_query = arguments.get("item_query")
    if not isinstance(item_query, str) or not item_query.strip():
        return {
            "ok": False,
            "tool_name": "remove_item",
            "execute": False,
            "error_type": "validation",
            "error": "Tool `remove_item` требует непустой `item_query`.",
        }

    resolution = resolve_item_id_from_text(item_query)
    status = resolution.get("status")
    if status == "ambiguous":
        candidates = [match.get("display_name_ru") or match.get("id") for match in resolution.get("matches", [])[:3]]
        candidate_text = ", ".join([str(candidate) for candidate in candidates if candidate])
        return {
            "ok": False,
            "tool_name": "remove_item",
            "execute": False,
            "error_type": "ambiguous",
            "error": f"Запрос неоднозначен. Уточни предмет для удаления: {candidate_text}." if candidate_text else "Запрос неоднозначен. Уточни предмет для удаления.",
            "matches": resolution.get("matches", []),
            "arguments": {"item_query": item_query},
        }

    if status != "resolved":
        return {
            "ok": False,
            "tool_name": "remove_item",
            "execute": False,
            "error_type": "not_found",
            "error": "Не смог определить предмет или блок для удаления.",
            "arguments": {"item_query": item_query},
        }

    item_id = _normalize_resource_id(resolution.get("item_id"))
    if item_id is None:
        return {
            "ok": False,
            "tool_name": "remove_item",
            "execute": False,
            "error_type": "validation",
            "error": "Не смог понять, какой предмет нужно удалить.",
            "arguments": {"item_query": item_query},
        }

    count = _normalize_count(arguments.get("count"), maximum=MAX_ITEM_COUNT)
    resolved_name = resolution.get("display_name_ru") or item_id
    return {
        "ok": True,
        "tool_name": "remove_item",
        "execute": True,
        "action_type": "clear",
        "item_id": item_id,
        "item_count": count,
        "resolved_name": resolved_name,
        "command": _build_clear_command(item_id, count),
        "arguments": {"item_query": item_query, "count": count},
        "summary": f"Забираю {count} x {resolved_name}.",
    }


def _execute_summon_entity(arguments: Dict[str, Any]) -> Dict[str, Any]:
    entity_query = arguments.get("entity_query")
    if not isinstance(entity_query, str) or not entity_query.strip():
        return {
            "ok": False,
            "tool_name": "summon_entity",
            "execute": False,
            "error_type": "validation",
            "error": "Tool `summon_entity` требует непустой `entity_query`.",
        }

    requested_count = _normalize_count(arguments.get("count"), maximum=MAX_SUMMON_COUNT)

    resolution = resolve_entity_id_from_text(entity_query)
    status = resolution.get("status")
    if status == "ambiguous":
        candidates = [match.get("display_name_ru") or match.get("id") for match in resolution.get("matches", [])[:3]]
        candidate_text = ", ".join([str(candidate) for candidate in candidates if candidate])
        return {
            "ok": False,
            "tool_name": "summon_entity",
            "execute": False,
            "error_type": "ambiguous",
            "error": f"Запрос неоднозначен. Уточни существо: {candidate_text}." if candidate_text else "Запрос неоднозначен. Уточни существо.",
            "matches": resolution.get("matches", []),
            "arguments": {"entity_query": entity_query},
        }

    if status != "resolved":
        return {
            "ok": False,
            "tool_name": "summon_entity",
            "execute": False,
            "error_type": "not_found",
            "error": "Не смог определить, какое существо нужно призвать.",
            "arguments": {"entity_query": entity_query},
        }

    entity_id = _normalize_resource_id(resolution.get("entity_id"))
    if entity_id is None:
        return {
            "ok": False,
            "tool_name": "summon_entity",
            "execute": False,
            "error_type": "validation",
            "error": "Не смог понять, какое существо нужно призвать.",
            "arguments": {"entity_query": entity_query},
        }

    resolved_name = resolution.get("display_name_ru") or entity_id
    return {
        "ok": True,
        "tool_name": "summon_entity",
        "execute": True,
        "action_type": "summon",
        "entity_id": entity_id,
        "entity_count": requested_count,
        "resolved_name": resolved_name,
        "command": _build_summon_command(entity_id, requested_count),
        "arguments": {"entity_query": entity_query, "count": requested_count},
        "summary": f"Призываю {requested_count} x {resolved_name}.",
    }


def _execute_create_challenge(arguments: Dict[str, Any]) -> Dict[str, Any]:
    goal_type = str(arguments.get("goal_type") or "").strip().lower()
    target_query = arguments.get("target_query")
    reward_item_query = arguments.get("reward_item_query")
    title = arguments.get("title")

    if goal_type not in {"kill", "collect"}:
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": "validation",
            "error": "Tool `create_challenge` требует `goal_type` = `kill` или `collect`.",
        }

    if not isinstance(target_query, str) or not target_query.strip():
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": "validation",
            "error": "Tool `create_challenge` требует непустой `target_query`.",
        }

    if not isinstance(reward_item_query, str) or not reward_item_query.strip():
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": "validation",
            "error": "Tool `create_challenge` требует непустой `reward_item_query`.",
        }

    goal_count = _normalize_count(arguments.get("goal_count"), maximum=9999)
    reward_count = _normalize_count(arguments.get("reward_count"), maximum=MAX_ITEM_COUNT)

    if goal_type == "kill":
        target_resolution = resolve_entity_id_from_text(target_query)
        if target_resolution.get("status") == "ambiguous":
            candidates = [match.get("display_name_ru") or match.get("id") for match in target_resolution.get("matches", [])[:3]]
            return {
                "ok": False,
                "tool_name": "create_challenge",
                "execute": False,
                "error_type": "ambiguous",
                "error": f"Неясно, кого нужно убить. Уточни цель: {', '.join([str(candidate) for candidate in candidates if candidate])}.",
                "matches": target_resolution.get("matches", []),
            }
        if target_resolution.get("status") != "resolved":
            return {
                "ok": False,
                "tool_name": "create_challenge",
                "execute": False,
                "error_type": "not_found",
                "error": "Не смог определить существо для челленджа.",
            }
        goal_target_id = _normalize_resource_id(target_resolution.get("entity_id"))
        goal_target_name = target_resolution.get("display_name_ru") or goal_target_id
    else:
        target_resolution = resolve_item_id_from_text(target_query)
        if target_resolution.get("status") == "ambiguous":
            candidates = [match.get("display_name_ru") or match.get("id") for match in target_resolution.get("matches", [])[:3]]
            return {
                "ok": False,
                "tool_name": "create_challenge",
                "execute": False,
                "error_type": "ambiguous",
                "error": f"Неясно, какой предмет нужен для челленджа. Уточни цель: {', '.join([str(candidate) for candidate in candidates if candidate])}.",
                "matches": target_resolution.get("matches", []),
            }
        if target_resolution.get("status") != "resolved":
            return {
                "ok": False,
                "tool_name": "create_challenge",
                "execute": False,
                "error_type": "not_found",
                "error": "Не смог определить предмет для цели челленджа.",
            }
        goal_target_id = _normalize_resource_id(target_resolution.get("item_id"))
        goal_target_name = target_resolution.get("display_name_ru") or goal_target_id

    reward_resolution = resolve_item_id_from_text(reward_item_query)
    if reward_resolution.get("status") == "ambiguous":
        candidates = [match.get("display_name_ru") or match.get("id") for match in reward_resolution.get("matches", [])[:3]]
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": "ambiguous",
            "error": f"Неясно, какая награда нужна. Уточни предмет: {', '.join([str(candidate) for candidate in candidates if candidate])}.",
            "matches": reward_resolution.get("matches", []),
        }
    if reward_resolution.get("status") != "resolved":
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": "not_found",
            "error": "Не смог определить награду для челленджа.",
        }

    reward_item_id = _normalize_resource_id(reward_resolution.get("item_id"))
    reward_name = reward_resolution.get("display_name_ru") or reward_item_id
    if goal_target_id is None or reward_item_id is None:
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": "validation",
            "error": "Не удалось нормализовать цель или награду челленджа.",
        }

    challenge_result = create_challenge(
        goal_type=goal_type,
        goal_target_id=goal_target_id,
        goal_count=goal_count,
        reward_item_id=reward_item_id,
        reward_count=reward_count,
        title=str(title).strip() if isinstance(title, str) and title.strip() else None,
        description=(
            f"Условие: {goal_type} {goal_count} x {goal_target_name}. Награда: {reward_count} x {reward_name}."
        ),
        source="chat",
    )
    if not challenge_result.get("ok"):
        return {
            "ok": False,
            "tool_name": "create_challenge",
            "execute": False,
            "error_type": challenge_result.get("error_type") or "challenge_error",
            "error": challenge_result.get("error") or "Не удалось создать челлендж.",
            "challenge": challenge_result.get("challenge"),
        }

    challenge = challenge_result.get("challenge") or {}
    return {
        "ok": True,
        "tool_name": "create_challenge",
        "execute": False,
        "action_type": "challenge_created",
        "challenge_id": challenge.get("id"),
        "challenge": challenge,
        "summary": challenge_result.get("summary")
        or f"Зафиксировал челлендж: {goal_type} {goal_count} x {goal_target_name} за {reward_count} x {reward_name}.",
    }


def _execute_claim_challenge_reward(arguments: Dict[str, Any]) -> Dict[str, Any]:
    challenge_id = arguments.get("challenge_id")
    if challenge_id is not None and not isinstance(challenge_id, str):
        challenge_id = str(challenge_id)
    return claim_active_challenge_reward(challenge_id)


def execute_tool_call(tool_name: str, arguments: Any) -> Dict[str, Any]:
    normalized_name = str(tool_name or "").strip().lower()
    if not isinstance(arguments, dict):
        arguments = {}

    if normalized_name == "give_item":
        return _execute_give_item(arguments)
    if normalized_name == "remove_item":
        return _execute_remove_item(arguments)
    if normalized_name == "summon_entity":
        return _execute_summon_entity(arguments)
    if normalized_name == "create_challenge":
        return _execute_create_challenge(arguments)
    if normalized_name == "claim_challenge_reward":
        return _execute_claim_challenge_reward(arguments)

    return {
        "ok": False,
        "tool_name": normalized_name or "unknown",
        "execute": False,
        "error_type": "unsupported_tool",
        "error": "Разрешены только tools `give_item`, `remove_item`, `summon_entity`, `create_challenge` и `claim_challenge_reward`.",
    }
