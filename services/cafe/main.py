import logging
import os
import sys

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from db import (
    cafe_to_item,
    delete_item,
    get_item,
    item_to_cafe_dict,
    put_item,
    scan,
    update_item,
)
from elo import elo_to_cups
from enrichment import location_enrichment
from models import (
    Cafe,
    CafeListResponse,
    FromUploadRequest,
    FromUploadResponse,
    InitialEloRequest,
    InitialEloResponse,
    RandomCafeListResponse,
    RandomCafeOut,
)
from ranking import compute_initial_elo, get_random_cafes_for_comparison, normalize_comparisons

logger = logging.getLogger(__name__)


def _configure_logging_for_lambda() -> None:
    """CloudWatch only shows app lines if the root logger level and handlers emit INFO."""
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)
    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root.addHandler(h)


_configure_logging_for_lambda()

app = FastAPI(title="Cafe service", version="1.0.0")
# In Lambda, CORS is configured on API Gateway HTTP API; adding CORSMiddleware here too
# duplicates Access-Control-Allow-Origin and breaks browser fetch from local dev pages.
if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


@app.get("/", include_in_schema=False)
def root():
    """HTML and static assets are served by the `web` container (port 3000 in docker-compose)."""
    return {
        "service": "cafehop-cafe-api",
        "openapi": "/docs",
        "example_ui": "http://127.0.0.1:3000/add.html",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/cafes", response_model=CafeListResponse)
def get_cafes(
    neighborhood: str | None = Query(default=None, description="Filter by neighborhood"),
    limit: int = Query(default=100, ge=1, le=500, description="Limit"),
    offset: int = Query(default=0, ge=0, description="Offset"),
):
    """Return cafes from DynamoDB with optional neighborhood filter and pagination."""
    try:
        items = scan(neighborhood=neighborhood, limit=limit, offset=offset)
        cafes = [Cafe(**item_to_cafe_dict(it)) for it in items]
        return CafeListResponse(cafes=cafes)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Register upload (under /v1 so it never matches GET /cafes/{cafe_id}).
BUCKET_URL = os.environ.get("BUCKET_URL", "").rstrip("/")
if not BUCKET_URL and os.environ.get("BUCKET_NAME"):
    _region = os.environ.get("AWS_REGION", "us-east-1")
    BUCKET_URL = f"https://{os.environ['BUCKET_NAME']}.s3.{_region}.amazonaws.com"


@app.options("/v1/cafes/from-upload")
def from_upload_preflight():
    return Response(status_code=204)


@app.post("/v1/cafes/from-upload", response_model=FromUploadResponse)
def from_upload(req: FromUploadRequest):
    """
    Register a newly uploaded cafe in DynamoDB.
    Fills neighborhood, subway, citibike, Google Maps, and initial Elo from lat/lon and comparisons.
    """
    key = (req.s3Key or "").strip() or f"{(req.cafeName or '').replace('/', '_')}.jpg"
    logger.info(
        "v1/cafes/from-upload start key=%r cafeName=%r lat=%r lon=%r comparisons=%d",
        key,
        (req.cafeName or "").strip(),
        req.latitude,
        req.longitude,
        len(req.comparisons or []),
    )
    name = (req.cafeName or "").strip() or key
    lat = req.latitude
    lon = req.longitude
    notes = (req.notes or "").strip()

    # Image URL
    image_url = f"{BUCKET_URL}/{key}" if BUCKET_URL else ""

    neighborhood = ""
    subway_station = ""
    subway_distance_m = 0.0
    subway_routes: list[str] = []
    google_maps_link = ""
    google_maps_place_type = ""
    citibike_name = ""
    citibike_distance_m = 0.0
    citibike_walk_mins = 0

    if lat is not None and lon is not None:
        safe_name = name.replace("/", "_").replace("\\", "_")
        e = location_enrichment(float(lat), float(lon), safe_name)
        neighborhood = e.neighborhood
        subway_station = e.subway_station
        subway_distance_m = e.subway_distance_m
        subway_routes = list(e.subway_routes)
        google_maps_link = e.google_maps_link
        google_maps_place_type = e.google_maps_place_type
        citibike_name = e.citibike_name
        citibike_distance_m = e.citibike_distance_m
        citibike_walk_mins = e.citibike_walk_mins

    initial_elo = compute_initial_elo(normalize_comparisons(req.comparisons))
    elo_star = elo_to_cups(initial_elo)

    item = {
        "key": key,
        "name": name,
        "imageUrl": image_url,
        "latitude": float(lat) if lat is not None else 0.0,
        "longitude": float(lon) if lon is not None else 0.0,
        "neighborhood": neighborhood,
        "subwayStation": subway_station,
        "subwayDistanceM": subway_distance_m,
        "subwayRoutes": subway_routes,
        "eloRating": initial_elo,
        "eloStarRating": elo_star,
        "notes": notes,
        "google_maps_link": google_maps_link,
        "google_maps_place_type": google_maps_place_type,
        "closest_citibike_station_name": citibike_name,
        "closest_citibike_station_distance_m": citibike_distance_m,
        "closest_citibike_station_walk_minutes": citibike_walk_mins,
        "shareCardPngUrl": "",
    }
    try:
        put_item(item)
        logger.info("v1/cafes/from-upload ok key=%r name=%r", key, name)
        return FromUploadResponse(key=key, message="Cafe registered in DynamoDB")
    except Exception as e:
        logger.exception("v1/cafes/from-upload failed key=%r", key)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/cafes/{cafe_id}", response_model=Cafe)
def get_cafe(cafe_id: str):
    """Return one cafe by key."""
    item = get_item(cafe_id)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Cafe not found"})
    return Cafe(**item_to_cafe_dict(item))


@app.post("/cafes", response_model=Cafe)
def create_cafe(cafe: Cafe):
    """Create a new cafe in DynamoDB (e.g. after image upload)."""
    try:
        put_item(cafe_to_item(cafe.model_dump()))
        return cafe
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/cafes/{cafe_id}", response_model=Cafe)
def update_cafe(cafe_id: str, cafe: Cafe):
    """Update cafe metadata in DynamoDB."""
    item = get_item(cafe_id)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Cafe not found"})
    updates = cafe_to_item(cafe.model_dump())
    updates.pop("key", None)
    updated = update_item(cafe_id, updates)
    if not updated:
        return JSONResponse(status_code=500, content={"error": "Update failed"})
    return Cafe(**item_to_cafe_dict(updated))


@app.delete("/cafes/{cafe_id}", response_model=Cafe)
def delete_cafe(cafe_id: str):
    """Delete a cafe from DynamoDB."""
    deleted = delete_item(cafe_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": "Cafe not found"})
    return Cafe(**item_to_cafe_dict(deleted))


# --- Health (for load balancer / readiness) ---
@app.get("/health")
def health():
    return {"status": "ok"}


# --- Ranking (logic in ranking.py) ---
@app.get("/ranking/cafes", response_model=RandomCafeListResponse)
def ranking_cafes(limit: int = Query(5, ge=1, le=50)):
    """Random cafes for add.html comparison UI."""
    cafes = get_random_cafes_for_comparison(limit)
    return RandomCafeListResponse(cafes=[RandomCafeOut(**c) for c in cafes])


@app.post("/ranking/initial-elo", response_model=InitialEloResponse)
def ranking_initial_elo(req: InitialEloRequest):
    """Compute initial Elo for a new cafe from comparison UI results."""
    try:
        comparisons = normalize_comparisons(req.comparisons)
        initial = compute_initial_elo(comparisons)
        return InitialEloResponse(initial_elo=initial, elo_star_rating=elo_to_cups(initial))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def lambda_handler(event, context):
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
    return handler(event, context)
