"""Pydantic request/response models for the cafe HTTP API."""
from __future__ import annotations

from pydantic import BaseModel


class Cafe(BaseModel):
    name: str
    image_url: str
    s3_key: str
    latitude: float
    longitude: float
    neighborhood: str
    subway_station: str
    subway_distance_m: float
    subway_routes: list[str]
    elo_rating: float
    elo_star_rating: float
    notes: str
    google_maps_link: str
    google_maps_place_type: str
    closest_citibike_station_name: str
    closest_citibike_station_distance_m: float
    closest_citibike_station_walk_minutes: int
    share_card_png_url: str


class CafeListResponse(BaseModel):
    cafes: list[Cafe]


class RandomCafeOut(BaseModel):
    key: str
    name: str = "Unknown Cafe"
    neighborhood: str | None = None


class RandomCafeListResponse(BaseModel):
    cafes: list[RandomCafeOut]


class InitialEloRequest(BaseModel):
    comparisons: list[list] | None = None


class InitialEloResponse(BaseModel):
    initial_elo: float
    elo_star_rating: float


class FromUploadRequest(BaseModel):
    """Payload for POST /v1/cafes/from-upload (geolocate + citibike + Elo → DynamoDB)."""

    s3Key: str
    cafeName: str
    latitude: float | None = None
    longitude: float | None = None
    notes: str = ""
    comparisons: list[list] | None = None


class FromUploadResponse(BaseModel):
    key: str
    message: str = "Cafe registered in DynamoDB"
