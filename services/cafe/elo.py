from collections import defaultdict
from typing import Dict, List, Tuple


def expected_score(r_a: float, r_b: float) -> float:
    return 1 / (1 + 10 ** ((r_b - r_a) / 400))


def log_new_cafe_elo(
    *,
    initial_elo: float = 1500.0,
    comparisons: List[Tuple[str, float]],
    existing_elos: Dict[str, float],
    existing_has_compared: Dict[str, bool],
    k_new: int = 32,
    k_existing_star_only: int = 6,
    k_existing_compared: int = 10,
    max_existing_delta: float = 5.0,
) -> Tuple[float, Dict[str, float]]:
    """Compute new cafe Elo from comparisons; returns (new_elo, updated_existing_elos)."""
    r_new = initial_elo
    delta_new = 0.0
    delta_existing = defaultdict(float)

    for cafe_id, score in comparisons:
        r_old = existing_elos[cafe_id]
        e_new = expected_score(r_new, r_old)
        delta_new += k_new * (score - e_new)
        k_existing = (
            k_existing_compared
            if existing_has_compared.get(cafe_id, False)
            else k_existing_star_only
        )
        delta_existing[cafe_id] += k_existing * ((1 - score) - (1 - e_new))

    for cafe_id in delta_existing:
        delta_existing[cafe_id] = max(
            -max_existing_delta,
            min(max_existing_delta, delta_existing[cafe_id]),
        )

    new_elo = r_new + delta_new
    updated_existing = {
        cid: existing_elos[cid] + delta_existing[cid]
        for cid in delta_existing
    }
    return new_elo, updated_existing


def elo_to_cups(elo: float, elo_min=1300, elo_max=1700, max_cups=5) -> float:
    cups = 1 + (elo - elo_min) / (elo_max - elo_min) * (max_cups - 1)
    return round(cups * 2) / 2
