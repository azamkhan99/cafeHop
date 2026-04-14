"""
Comparison sampling and initial Elo from DynamoDB-backed cafes.
Used by GET /ranking/cafes, POST /ranking/initial-elo, and POST /v1/cafes/from-upload.
"""
from __future__ import annotations

import logging
import random
import re

from db import scan_all
from elo import log_new_cafe_elo

logger = logging.getLogger(__name__)

IMAGE_KEY_PATTERN = re.compile(r"\.(jpg|jpeg|png|gif)$", re.I)


def _name_from_key(key: str) -> str:
    if not key:
        return "Unknown Cafe"
    base = key.split("/")[-1]
    base = IMAGE_KEY_PATTERN.sub("", base).replace("_", " ").strip()
    return base or "Unknown Cafe"


def _random_cafes_with_elo(num_cafes: int = 5) -> list[tuple[str, float]]:
    try:
        items = scan_all(
            projection_expression="#k, #e",
            expression_attribute_names={"#k": "key", "#e": "eloRating"},
        )
        candidates = []
        for it in items:
            key = it.get("key")
            elo = it.get("eloRating") or it.get("elo_rating")
            if isinstance(key, str) and key and elo is not None:
                try:
                    candidates.append((key, float(elo)))
                except (TypeError, ValueError):
                    pass
        if not candidates:
            return []
        return random.sample(candidates, min(num_cafes, len(candidates)))
    except Exception as e:
        logger.warning("Random cafes with Elo: %s", e)
        return []


def compute_initial_elo(comparisons: list[tuple[str, float]] | None) -> float:
    default_elo = 1500.0
    reference = _random_cafes_with_elo(5)
    if not reference:
        return default_elo
    cafe_ids = [k for k, _ in reference]
    existing_elos = {k: elo for k, elo in reference}
    existing_has_compared = {k: False for k in cafe_ids}
    if comparisons:
        valid = [(k, float(s)) for k, s in comparisons if k in existing_elos]
        comparisons_to_use = valid if valid else [(k, 0.5) for k in cafe_ids]
    else:
        comparisons_to_use = [(k, 0.5) for k in cafe_ids]
    try:
        new_elo, _ = log_new_cafe_elo(
            initial_elo=default_elo,
            comparisons=comparisons_to_use,
            existing_elos=existing_elos,
            existing_has_compared=existing_has_compared,
        )
        return float(new_elo)
    except Exception as e:
        logger.warning("Elo computation: %s", e)
    avg = sum(existing_elos.values()) / len(existing_elos)
    return avg - 50.0


def get_random_cafes_for_comparison(limit: int) -> list[dict]:
    try:
        items = scan_all(
            projection_expression="#k, #n, neighborhood",
            expression_attribute_names={"#k": "key", "#n": "name"},
        )
        valid = [
            it
            for it in items
            if isinstance(it.get("key"), str)
            and it["key"]
            and not it["key"].startswith("mapThumbnails/")
            and IMAGE_KEY_PATTERN.search(it["key"])
        ]
        if not valid:
            return []
        sample = random.sample(valid, min(limit, len(valid)))
        out = []
        for it in sample:
            key = it.get("key", "")
            name = it.get("name")
            name = (str(name).strip() if name else _name_from_key(key)) or "Unknown Cafe"
            neighborhood = it.get("neighborhood")
            neighborhood = str(neighborhood).strip() or None if neighborhood else None
            out.append({"key": key, "name": name, "neighborhood": neighborhood})
        return out
    except Exception as e:
        logger.warning("Random cafes for comparison: %s", e)
        return []


def normalize_comparisons(raw: list[list] | None) -> list[tuple[str, float]] | None:
    if not raw:
        return None
    out = []
    for c in raw:
        try:
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                out.append((str(c[0]), float(c[1])))
        except (TypeError, ValueError):
            continue
    return out if out else None
