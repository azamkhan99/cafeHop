import json
import math
import os
from typing import Optional

import numpy as np

EARTH_RADIUS_M = 6371000
WALKING_SPEED_M_PER_MIN = 80

_stations_cache = None


def _stations_path():
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "station_information_rel.json",
    )
    return os.environ.get("CITIBIKE_STATIONS_JSON_PATH", default)


def _load_stations(json_path=None):
    global _stations_cache
    if _stations_cache is not None:
        return _stations_cache
    path = json_path or _stations_path()
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        _stations_cache = json.load(f)
    return _stations_cache


def get_closest_citibike_station(lat: float, lon: float, json_path: Optional[str] = None) -> Optional[dict]:
    """Closest station; returns dict with name, distance_m, mins_walk. None if data unavailable."""
    stations = _load_stations(json_path)
    if not stations:
        return None

    station_lats = np.array([s["lat"] for s in stations])
    station_lons = np.array([s["lon"] for s in stations])
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    station_lats_rad = np.radians(station_lats)
    station_lons_rad = np.radians(station_lons)
    dlat = station_lats_rad - lat_rad
    dlon = station_lons_rad - lon_rad
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat_rad) * np.cos(station_lats_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))
    distances = EARTH_RADIUS_M * c
    closest_idx = int(np.argmin(distances))
    closest = stations[closest_idx]
    distance_m = float(distances[closest_idx])
    mins_walk = int(np.ceil(distance_m / WALKING_SPEED_M_PER_MIN))
    return {
        "station_id": closest["station_id"],
        "name": closest["name"],
        "lat": closest["lat"],
        "lon": closest["lon"],
        "distance_m": distance_m,
        "mins_walk": mins_walk,
    }
