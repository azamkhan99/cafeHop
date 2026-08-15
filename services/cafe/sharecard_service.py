from __future__ import annotations

import base64
import io
import logging
import os
import re
from datetime import date
from pathlib import Path

import boto3
import cairosvg
from jinja2 import Environment, FileSystemLoader
from PIL import Image

logger = logging.getLogger(__name__)

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL")
_s3_kwargs: dict = {"region_name": _REGION}
if _ENDPOINT:
    _s3_kwargs["endpoint_url"] = _ENDPOINT


def _s3_client():
    return boto3.client("s3", **_s3_kwargs)


def _templates_dir() -> Path:
    env_dir = os.environ.get("SHARECARD_TEMPLATES_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    beside = Path(__file__).resolve().parent / "templates"
    if beside.is_dir():
        return beside
    return Path(__file__).resolve().parents[2] / "assets" / "templates"


def _public_bucket_url(bucket_name: str) -> str:
    configured = os.environ.get("BUCKET_URL", "").rstrip("/")
    if configured:
        return configured
    return f"https://{bucket_name}.s3.{_REGION}.amazonaws.com"


def _image_bytes_to_data_uri(raw: bytes) -> str:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    b64 = base64.b64encode(out.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def shorten_intersection(text: str) -> str:
    m = re.match(r"^\s*([^&]+?)\s*&\s*(.+?)\s*$", text)
    if not m:
        return text

    s1, s2 = m.group(1), m.group(2)
    dir_map = {
        r"\bEast\b": "E",
        r"\bWest\b": "W",
        r"\bNorth\b": "N",
        r"\bSouth\b": "S",
    }
    for pat, repl in dir_map.items():
        s1 = re.sub(pat, repl, s1, flags=re.IGNORECASE)
        s2 = re.sub(pat, repl, s2, flags=re.IGNORECASE)

    suffixes = r"\b(St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Pl|Place|Ln|Lane|Dr|Drive)\b"
    s1 = re.sub(suffixes, "", s1, flags=re.IGNORECASE)
    s2 = re.sub(suffixes, "", s2, flags=re.IGNORECASE)
    s1 = re.sub(r"\s+", " ", s1).strip()
    s2 = re.sub(r"\s+", " ", s2).strip()
    return f"{s1} & {s2}"


def _shorten_gmaps_link(link: str) -> str:
    if "place_id:" in link:
        place_id = link.split("place_id:")[-1]
        return f"https://maps.google.com/?q=place_id:{place_id}"
    return link


def _subway_lines(data: dict) -> list[str]:
    routes = data.get("subwayRoutes") or data.get("subway_routes") or []
    if isinstance(routes, str):
        return [p.strip() for p in routes.split(",") if p.strip()]
    if isinstance(routes, list):
        return [str(x).strip() for x in routes if str(x).strip()]
    raw = data.get("closest_subway_lines") or ""
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def generate_receipt_card(
    data: dict,
    cafe_photo_bytes: bytes,
    template: str = "receipt_card.svg",
    width: int = 1080,
    height: int = 1350,
) -> bytes:
    tdir = _templates_dir()
    env = Environment(loader=FileSystemLoader(str(tdir)))
    tmpl = env.get_template(template)

    citibike_station = str(data.get("closest_citibike_station_name") or "")
    shortened_citibike = shorten_intersection(citibike_station).replace("&", "&amp;")
    rating = data.get("eloStarRating", data.get("elo_star_rating", 0)) or 0

    svg = tmpl.render(
        name=data.get("name") or data.get("cafe-name") or "",
        neighborhood=data.get("neighborhood") or "",
        rating=rating,
        subway_lines=_subway_lines(data),
        citibike_station=shortened_citibike,
        cafe_photo_href=_image_bytes_to_data_uri(cafe_photo_bytes),
        date=date.today().strftime("%B %d, %Y"),
        gmaps_link=_shorten_gmaps_link(str(data.get("google_maps_link") or "")),
        font_receipt_title="",
        font_receipt_mono="",
    )
    return cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        output_width=width,
        output_height=height,
        unsafe=True,
    )


def generate_and_store_share_card(item: dict) -> str:
    """Render receipt PNG, upload to S3, return public URL. Empty string if S3 is not configured."""
    bucket = os.environ.get("BUCKET_NAME", "").strip()
    object_key = (item.get("key") or "").strip()
    if not bucket or not object_key:
        logger.warning("share card skipped: missing BUCKET_NAME or cafe key")
        return ""

    s3 = _s3_client()
    obj = s3.get_object(Bucket=bucket, Key=object_key)
    png_bytes = generate_receipt_card(item, obj["Body"].read())

    stem = Path(object_key).stem
    share_card_key = f"receipt_cards/{stem}.png"
    s3.put_object(
        Bucket=bucket,
        Key=share_card_key,
        Body=png_bytes,
        ContentType="image/png",
        CacheControl="max-age=31536000",
    )
    url = f"{_public_bucket_url(bucket)}/{share_card_key}"
    logger.info("share card stored key=%r url=%r", share_card_key, url)
    return url
