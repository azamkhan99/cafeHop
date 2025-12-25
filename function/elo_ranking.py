from collections import defaultdict
from typing import Dict, List, Tuple
import math

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
    """
    Parameters
    ----------
    initial_elo : float
        Starting Elo for the new cafe (default 1500).
    comparisons : list of (cafe_id, score)
        score ∈ {1, 0.5, 0} where 1 = new cafe preferred.
    existing_elos : dict
        Current Elo ratings for existing cafes.
    existing_has_compared : dict
        Whether an existing cafe has previously participated in any Elo comparison.
    """

    # 1️⃣ Initialize new cafe rating
    r_new = initial_elo

    delta_new = 0.0
    delta_existing = defaultdict(float)

    # 2️⃣ Batch Elo updates
    for cafe_id, score in comparisons:
        r_old = existing_elos[cafe_id]

        e_new = expected_score(r_new, r_old)

        # Update new cafe
        delta_new += k_new * (score - e_new)

        # Choose K for existing cafe
        k_existing = (
            k_existing_compared
            if existing_has_compared.get(cafe_id, False)
            else k_existing_star_only
        )

        delta_existing[cafe_id] += (
            k_existing * ((1 - score) - (1 - e_new))
        )

    # 3️⃣ Safety cap for existing cafes
    for cafe_id in delta_existing:
        delta_existing[cafe_id] = max(
            -max_existing_delta,
            min(max_existing_delta, delta_existing[cafe_id])
        )

    # 4️⃣ Apply updates
    new_elo = r_new + delta_new

    updated_existing = {
        cafe_id: existing_elos[cafe_id] + delta
        for cafe_id, delta in delta_existing.items()
    }

    return new_elo, updated_existing

def elo_to_cups(elo: float, elo_min=1300, elo_max=1700, max_cups=5):
    cups = 1 + (elo - elo_min) / (elo_max - elo_min) * (max_cups - 1)
    return round(cups * 2) / 2  # round to nearest 0.5