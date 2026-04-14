from __future__ import annotations

import logging
from dataclasses import dataclass

from citibike_stations import get_closest_citibike_station
from geocoding import build_google_maps_link_nearby, get_closest_subway_station, get_neighborhood

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocationEnrichment:
    neighborhood: str = ""
    subway_station: str = ""
    subway_distance_m: float = 0.0
    subway_routes: tuple[str, ...] = ()
    google_maps_link: str = ""
    google_maps_place_type: str = ""
    citibike_name: str = ""
    citibike_distance_m: float = 0.0
    citibike_walk_mins: int = 0


def location_enrichment(lat: float, lon: float, safe_cafe_name: str) -> LocationEnrichment:
    neighborhood = ""
    subway_station = ""
    subway_distance_m = 0.0
    subway_routes: list[str] = []
    google_maps_link = ""
    google_maps_place_type = ""
    citibike_name = ""
    citibike_distance_m = 0.0
    citibike_walk_mins = 0

    try:
        n = get_neighborhood(lat, lon)
        if n:
            neighborhood = n
        sub = get_closest_subway_station(lat, lon)
        if sub:
            subway_station = sub.get("station", "")
            lines = sub.get("lines", [])
            if lines:
                subway_routes = [str(x) for x in lines]
            dm = sub.get("distance_m")
            if dm is not None:
                subway_distance_m = float(dm)
        link, ptype = build_google_maps_link_nearby(safe_cafe_name, lat, lon)
        if link:
            google_maps_link = link
        if ptype:
            google_maps_place_type = ptype
    except Exception as e:
        logger.warning("Geocoding enrichment failed: %s", e)

    try:
        station = get_closest_citibike_station(lat, lon)
        if station:
            citibike_name = station.get("name", "")
            citibike_distance_m = float(station.get("distance_m", 0))
            citibike_walk_mins = int(station.get("mins_walk", 0))
    except Exception as e:
        logger.warning("Citibike enrichment failed: %s", e)

    return LocationEnrichment(
        neighborhood=neighborhood,
        subway_station=subway_station,
        subway_distance_m=subway_distance_m,
        subway_routes=tuple(subway_routes),
        google_maps_link=google_maps_link,
        google_maps_place_type=google_maps_place_type,
        citibike_name=citibike_name,
        citibike_distance_m=citibike_distance_m,
        citibike_walk_mins=citibike_walk_mins,
    )
