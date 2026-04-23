import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "minecraft_catalog.json"
TOKEN_PATTERN = re.compile(r"\w+")
QUERY_STOPWORDS = {
    "а",
    "бы",
    "в",
    "выдай",
    "дай",
    "для",
    "же",
    "и",
    "или",
    "ли",
    "мне",
    "можно",
    "мог",
    "могу",
    "могла",
    "могли",
    "мы",
    "на",
    "не",
    "ну",
    "нужен",
    "нужна",
    "нужно",
    "нужны",
    "от",
    "очень",
    "пожалуйста",
    "получи",
    "получить",
    "просто",
    "сейчас",
    "спавн",
    "хочу",
    "хотел",
    "хотела",
    "хотелось",
    "что",
    "я",
    "you",
    "give",
    "get",
    "me",
    "please",
    "want",
    "need",
}
DEFAULT_QUERY_RESOLUTIONS = {
    "меч": "minecraft:diamond_sword",
}


def _normalize_token(token: str) -> str:
    normalized = (token or "").strip()
    if not normalized:
        return ""

    if normalized.startswith("бутыл"):
        return "бутылочка"
    if normalized.startswith("пузыр"):
        return "пузырек"
    if normalized.startswith("склян"):
        return "колба"
    if normalized.startswith("наковаль"):
        return "наковальня"
    return normalized


def normalize_catalog_text(text: str) -> str:
    normalized = (text or "").lower().replace("ё", "е")
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = re.sub(r"[^\w\s:]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize_catalog_text(text: str) -> List[str]:
    tokens = TOKEN_PATTERN.findall(normalize_catalog_text(text))
    return [_normalize_token(token) for token in tokens if _normalize_token(token)]


def _query_tokens(text: str) -> List[str]:
    tokens = tokenize_catalog_text(text)
    filtered = [token for token in tokens if token not in QUERY_STOPWORDS]
    return filtered or tokens


def _fuzzy_token_score(query_tokens: set[str], variant_tokens: set[str]) -> int:
    if not query_tokens or not variant_tokens:
        return 0

    score = 0
    for query_token in query_tokens:
        if query_token in variant_tokens:
            continue

        best_similarity = max(
            (SequenceMatcher(None, query_token, variant_token).ratio() for variant_token in variant_tokens),
            default=0.0,
        )
        if best_similarity >= 0.92:
            score += 60
        elif best_similarity >= 0.84:
            score += 30

    return score


@lru_cache(maxsize=1)
def load_catalog() -> List[Dict[str, Any]]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog: List[Dict[str, Any]] = []
    for index, entry in enumerate(payload):
        variants = _build_variants(entry)
        catalog.append({**entry, "variants": variants, "catalog_index": index})
    return catalog


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


def search_catalog(query: str, *, limit: int = 5) -> List[Dict[str, Any]]:
    normalized_query = normalize_catalog_text(query)
    if not normalized_query:
        return []

    query_tokens = set(_query_tokens(normalized_query))
    padded_query = f" {normalized_query} "
    matches_by_id: Dict[str, Dict[str, Any]] = {}

    for entry in load_catalog():
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
                fuzzy_bonus = _fuzzy_token_score(query_tokens, variant_tokens)
                if not overlap and not fuzzy_bonus:
                    continue
                score = len(overlap) * 100 + sum(len(token) for token in overlap)
                if overlap == variant_tokens:
                    score += 50
                if overlap == query_tokens:
                    score += 25
                score += fuzzy_bonus
                if len(normalized_query) >= 6:
                    similarity = SequenceMatcher(None, normalized_query, variant).ratio()
                    if similarity >= 0.88:
                        score += int(similarity * 40)

            if score > best_score:
                best_score = score
                best_variant = variant

        if best_score > 0:
            candidate = {
                "id": entry["id"],
                "kind": entry["kind"],
                "display_name_ru": entry.get("display_name_ru"),
                "display_name_en": entry.get("display_name_en"),
                "matched_variant": best_variant,
                "score": best_score,
                "catalog_index": entry["catalog_index"],
            }
            existing = matches_by_id.get(entry["id"])
            if existing is None or best_score > existing["score"]:
                matches_by_id[entry["id"]] = candidate

    matches = list(matches_by_id.values())
    matches.sort(key=lambda item: (-item["score"], item["catalog_index"], item["id"]))
    return matches[: max(1, limit)]


def resolve_item_id_from_text(text: str) -> Dict[str, Any]:
    raw_query = (text or "").strip().lower()
    explicit_match = re.search(r"(minecraft:[a-z0-9_./-]+)", raw_query)
    if explicit_match:
        return {
            "status": "resolved",
            "query": text,
            "item_id": explicit_match.group(1),
            "kind": "unknown",
            "matched_variant": explicit_match.group(1),
            "matches": [],
        }

    normalized_query = normalize_catalog_text(text)
    if not normalized_query:
        return {"status": "not_found", "query": text, "matches": []}

    matches = search_catalog(text, limit=5)
    if not matches:
        return {"status": "not_found", "query": text, "matches": []}

    preferred_query = " ".join(_query_tokens(normalized_query))
    preferred_item_id = DEFAULT_QUERY_RESOLUTIONS.get(preferred_query) or DEFAULT_QUERY_RESOLUTIONS.get(normalized_query)
    if preferred_item_id:
        preferred_match = next((match for match in matches if match["id"] == preferred_item_id), None)
        if preferred_match is not None:
            return {
                "status": "resolved",
                "query": text,
                "item_id": preferred_match["id"],
                "kind": preferred_match["kind"],
                "matched_variant": preferred_match["matched_variant"],
                "matches": matches[:3],
            }

    best = matches[0]
    if len(matches) > 1 and matches[1]["score"] == best["score"]:
        return {"status": "ambiguous", "query": text, "matches": matches[:3]}

    return {
        "status": "resolved",
        "query": text,
        "item_id": best["id"],
        "kind": best["kind"],
        "matched_variant": best["matched_variant"],
        "matches": matches[:3],
    }
