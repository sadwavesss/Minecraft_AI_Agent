import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from api.minecraft_catalog import normalize_catalog_text, tokenize_catalog_text


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "entity_catalog.json"
QUERY_STOPWORDS = {
    "а",
    "бы",
    "в",
    "вызови",
    "вызывать",
    "для",
    "же",
    "заспавни",
    "заспавнить",
    "и",
    "или",
    "ли",
    "мне",
    "можно",
    "можешь",
    "на",
    "не",
    "ну",
    "пожалуйста",
    "призови",
    "призвать",
    "призыв",
    "просто",
    "сейчас",
    "создай",
    "спавн",
    "спавнить",
    "существо",
    "существ",
    "тут",
    "хочу",
    "я",
    "summon",
    "spawn",
}


def _query_tokens(text: str) -> List[str]:
    tokens = tokenize_catalog_text(text)
    filtered = [token for token in tokens if token not in QUERY_STOPWORDS]
    return filtered or tokens


def _build_variants(entry: Dict[str, Any]) -> List[str]:
    candidates = [
        entry.get("display_name_ru", ""),
        entry.get("display_name_en", ""),
        *(entry.get("aliases_ru") or []),
        *(entry.get("aliases_en") or []),
    ]
    variants: List[str] = []
    seen = set()
    for value in candidates:
        normalized = normalize_catalog_text(value)
        if normalized and normalized not in seen:
            variants.append(normalized)
            seen.add(normalized)
    variants.sort(key=len, reverse=True)
    return variants


@lru_cache(maxsize=1)
def load_entity_catalog() -> List[Dict[str, Any]]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return [{**entry, "variants": _build_variants(entry)} for entry in payload]


def search_entity_catalog(query: str, *, limit: int = 5) -> List[Dict[str, Any]]:
    normalized_query = normalize_catalog_text(query)
    if not normalized_query:
        return []

    query_tokens = set(_query_tokens(normalized_query))
    padded_query = f" {normalized_query} "
    matches: List[Dict[str, Any]] = []

    for entry in load_entity_catalog():
        best_score = 0
        best_variant = ""
        for variant in entry["variants"]:
            variant_tokens = set(tokenize_catalog_text(variant))
            score = 0

            if normalized_query == variant:
                score = 1000 + len(variant)
            elif f" {variant} " in padded_query:
                score = 900 + len(variant)
            elif query_tokens and variant_tokens:
                overlap = query_tokens & variant_tokens
                if not overlap:
                    similarity = SequenceMatcher(None, normalized_query, variant).ratio()
                    if similarity < 0.84:
                        continue
                    score = int(similarity * 100)
                else:
                    score = len(overlap) * 100 + sum(len(token) for token in overlap)
                    if overlap == variant_tokens:
                        score += 40
                    if overlap == query_tokens:
                        score += 20

            if score > best_score:
                best_score = score
                best_variant = variant

        if best_score > 0:
            matches.append(
                {
                    "id": entry["id"],
                    "kind": entry["kind"],
                    "display_name_ru": entry.get("display_name_ru"),
                    "display_name_en": entry.get("display_name_en"),
                    "matched_variant": best_variant,
                    "score": best_score,
                }
            )

    matches.sort(key=lambda item: (-item["score"], item["id"]))
    return matches[: max(1, limit)]


def resolve_entity_id_from_text(text: str) -> Dict[str, Any]:
    raw_query = (text or "").strip().lower()
    explicit_match = re.search(r"(minecraft:[a-z0-9_./-]+)", raw_query)
    if explicit_match:
        return {
            "status": "resolved",
            "query": text,
            "entity_id": explicit_match.group(1),
            "kind": "mob",
            "matched_variant": explicit_match.group(1),
            "matches": [],
        }

    normalized_query = normalize_catalog_text(text)
    if not normalized_query:
        return {"status": "not_found", "query": text, "matches": []}

    matches = search_entity_catalog(text, limit=5)
    if not matches:
        return {"status": "not_found", "query": text, "matches": []}

    best = matches[0]
    if len(matches) > 1 and matches[1]["score"] == best["score"]:
        return {"status": "ambiguous", "query": text, "matches": matches[:3]}

    return {
        "status": "resolved",
        "query": text,
        "entity_id": best["id"],
        "kind": best["kind"],
        "matched_variant": best["matched_variant"],
        "matches": matches[:3],
    }
