from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Optional

from api.entity_catalog import load_entity_catalog
from api.minecraft_catalog import load_catalog


@lru_cache(maxsize=1)
def _item_display_names() -> Dict[str, str]:
    names: Dict[str, str] = {}
    for entry in load_catalog():
        item_id = str(entry.get("id") or "").strip()
        display_name = str(entry.get("display_name_ru") or "").strip()
        if item_id and display_name and item_id not in names:
            names[item_id] = display_name
    return names


@lru_cache(maxsize=1)
def _entity_display_names() -> Dict[str, str]:
    names: Dict[str, str] = {}
    for entry in load_entity_catalog():
        entity_id = str(entry.get("id") or "").strip()
        display_name = str(entry.get("display_name_ru") or "").strip()
        if entity_id and display_name and entity_id not in names:
            names[entity_id] = display_name
    return names


def get_item_display_name_ru(item_id: Any) -> Optional[str]:
    normalized = str(item_id or "").strip()
    if not normalized:
        return None
    return _item_display_names().get(normalized)


def get_entity_display_name_ru(entity_id: Any) -> Optional[str]:
    normalized = str(entity_id or "").strip()
    if not normalized:
        return None
    return _entity_display_names().get(normalized)


def get_resource_display_name_ru(resource_id: Any) -> Optional[str]:
    normalized = str(resource_id or "").strip()
    if not normalized:
        return None
    return get_item_display_name_ru(normalized) or get_entity_display_name_ru(normalized)


RESOURCE_ID_PATTERN = re.compile(r"\bminecraft:[a-z0-9_./-]+\b")


def replace_resource_ids_with_labels(text: Any) -> str:
    source_text = str(text or "")
    if not source_text:
        return ""

    def _replace(match: re.Match[str]) -> str:
        resource_id = match.group(0)
        return get_resource_display_name_ru(resource_id) or resource_id

    return RESOURCE_ID_PATTERN.sub(_replace, source_text)
