"""
Image service: S3 presigned PUT and map thumbnail after upload.
- POST /presigned-url: return presigned PUT URL + s3Key; optional S3 metadata from payload.
- POST /process: create mapThumbnails/{key} from the uploaded object.
"""
from __future__ import annotations

import logging
import os
import sys

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from processing import generate_map_thumbnail

logger = logging.getLogger(__name__)


def _configure_logging_for_lambda() -> None:
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

BUCKET = os.environ.get("BUCKET_NAME", "")
_REGION = os.environ.get("AWS_REGION", "us-east-1")
_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL")
_s3_kwargs: dict = {"region_name": _REGION}
if _ENDPOINT:
    _s3_kwargs["endpoint_url"] = _ENDPOINT
s3 = boto3.client("s3", **_s3_kwargs) if BUCKET else None
# Presigned URLs must use a host the *browser* can reach. Inside Docker, AWS_ENDPOINT_URL
# is often http://localstack:4566; set S3_PUBLIC_ENDPOINT_URL to http://127.0.0.1:4566
# so SigV4 matches the PUT from the user's machine (signing is local; no TCP to this host).
_presign_endpoint = os.environ.get("S3_PUBLIC_ENDPOINT_URL", "").strip() or _ENDPOINT
_presign_kwargs: dict = {"region_name": _REGION}
if _presign_endpoint:
    _presign_kwargs["endpoint_url"] = _presign_endpoint
s3_presign = boto3.client("s3", **_presign_kwargs) if BUCKET else None

app = FastAPI(title="Image service")
if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "cafehop-image-api",
        "openapi": "/docs",
        "example_ui": "http://127.0.0.1:3000/add.html",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


class PresignedUrlRequest(BaseModel):
    """Matches add.html uploadData (extra fields ignored for S3 metadata if empty)."""
    cafeName: str = Field(..., min_length=1, description="Cafe name (required)")
    contentType: str = Field(default="image/jpeg", description="MIME type for upload")
    notes: str | None = Field(default=None, description="Optional notes")
    latitude: float | None = Field(default=None, description="Optional latitude")
    longitude: float | None = Field(default=None, description="Optional longitude")
    neighborhood: str | None = Field(default=None, description="Optional neighborhood override")
    closestSubwayStation: str | None = Field(default=None, description="Optional closest subway station")
    closestSubwayLines: str | None = Field(default=None, description="Optional subway lines (comma-separated)")
    googleMapsLink: str | None = Field(default=None, description="Optional Google Maps link")
    googleMapsPlaceType: str | None = Field(default=None, description="Optional place type")
    comparisons: list[list] | None = Field(
        default=None,
        description="Ignored for presign; used by cafe /v1/cafes/from-upload after upload",
    )


class PresignedUrlResponse(BaseModel):
    uploadUrl: str
    s3Key: str


class ProcessRequest(BaseModel):
    s3Key: str = Field(..., min_length=1, description="S3 object key of the uploaded image")


class ProcessResponse(BaseModel):
    message: str = "Thumbnail created"


def _metadata_from_payload(body: PresignedUrlRequest) -> dict[str, str]:
    def str_val(v) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        return s if s else ""

    return {
        "cafe-name": body.cafeName.strip(),
        "notes": str_val(body.notes),
        "x-amz-meta-notes": str_val(body.notes),
        "latitude": str_val(body.latitude),
        "longitude": str_val(body.longitude),
        "x-amz-meta-neighborhood": str_val(body.neighborhood),
        "closest_subway_station": str_val(body.closestSubwayStation),
        "closest_subway_lines": str_val(body.closestSubwayLines),
        "google_maps_link": str_val(body.googleMapsLink),
        "google_maps_place_type": str_val(body.googleMapsPlaceType),
    }


@app.options("/presigned-url")
@app.options("/process")
async def _cors_preflight():
    return Response(status_code=204)


@app.post("/presigned-url", response_model=PresignedUrlResponse)
async def presigned_url(body: PresignedUrlRequest):
    return await _handle_presign(body)


@app.post("/process", response_model=ProcessResponse)
async def process(body: ProcessRequest):
    return await _handle_process(body)


async def _handle_process(body: ProcessRequest):
    key = body.s3Key
    logger.info("POST /process start key=%r", key)
    if not s3 or not BUCKET:
        return JSONResponse(
            status_code=503,
            content={"error": "S3 not configured"},
            headers={"Access-Control-Allow-Origin": "*"},
        )
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        raw = obj["Body"].read()
        try:
            thumb_bytes = generate_map_thumbnail(raw)
        except ValueError as e:
            head = raw[:24].hex() if raw else ""
            logger.warning(
                "POST /process thumbnail key=%r bytes=%s head_hex=%s err=%s",
                key,
                len(raw),
                head,
                e,
            )
            return JSONResponse(
                status_code=422,
                content={"error": str(e)},
                headers={"Access-Control-Allow-Origin": "*"},
            )
        map_key = f"mapThumbnails/{key}"
        s3.put_object(
            Bucket=BUCKET,
            Key=map_key,
            Body=thumb_bytes,
            ContentType="image/jpeg",
            CacheControl="max-age=31536000",
        )
        logger.info("POST /process ok key=%r map_key=%r thumb_bytes=%s", key, map_key, len(thumb_bytes))
        return ProcessResponse(message="Thumbnail created")
    except Exception as e:
        from botocore.exceptions import ClientError

        if isinstance(e, ClientError) and e.response.get("Error", {}).get("Code") == "NoSuchKey":
            return JSONResponse(
                status_code=404,
                content={"error": "Object not found"},
                headers={"Access-Control-Allow-Origin": "*"},
            )
        err = str(e)
        if "NoSuchKey" in err:
            return JSONResponse(
                status_code=404,
                content={"error": "Object not found"},
                headers={"Access-Control-Allow-Origin": "*"},
            )
        logger.exception("POST /process failed for key=%s", key)
        return JSONResponse(
            status_code=500,
            content={"error": err},
            headers={"Access-Control-Allow-Origin": "*"},
        )


async def _handle_presign(body: PresignedUrlRequest):
    if not s3_presign or not BUCKET:
        return JSONResponse(
            status_code=503,
            content={"error": "S3 not configured"},
            headers={"Access-Control-Allow-Origin": "*"},
        )

    cafe_name = body.cafeName.strip()
    safe_name = cafe_name.replace("/", "_").replace("\\", "_")
    key = f"{safe_name}.jpg"
    content_type = body.contentType or "image/jpeg"
    metadata = _metadata_from_payload(body)

    url = s3_presign.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": BUCKET,
            "Key": key,
            "ContentType": content_type,
            "Metadata": metadata,
        },
        ExpiresIn=60,
    )
    return PresignedUrlResponse(uploadUrl=url, s3Key=key)


def lambda_handler(event, context):
    from mangum import Mangum

    handler = Mangum(app, lifespan="off")
    return handler(event, context)
