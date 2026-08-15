from __future__ import annotations

import logging
import os
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import googlemaps
import requests

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

_PLACE_PATH = re.compile(r"/maps/place/([^/@]+)", re.I)
_SEARCH_PATH = re.compile(r"/maps/search/([^/@]+)", re.I)
_AT_COORDS = re.compile(r"/@(-?\d+\.\d+),(-?\d+\.\d+)")
_BANG_COORDS = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_Q_COORDS = re.compile(r"^(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)$")
_HTTP_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_CHIJ = re.compile(r"(ChIJ[\w-]+)")


def extract_maps_url(text: str) -> str:
    m = _HTTP_URL.search(text or "")
    if not m:
        return ""
    return m.group(0).rstrip(").,;]")


def _short_place_name(name: str) -> str:
    raw = re.sub(r"\s+", " ", (name or "").strip())
    if "," not in raw:
        return raw
    head, tail = raw.split(",", 1)
    if re.search(r"\d", tail):
        return head.strip() or raw
    return raw


def _host_ok(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower().rstrip(".")
    return (
        h == "google.com"
        or h.endswith(".google.com")
        or h == "goo.gl"
        or h.endswith(".goo.gl")
    )


def parse_maps_url(url: str) -> dict:
    """Pull name / lat / lng / place_id from a (usually expanded) Google Maps URL."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    name = ""
    lat: float | None = None
    lng: float | None = None

    bang = _BANG_COORDS.search(url)
    if bang:
        lat, lng = float(bang.group(1)), float(bang.group(2))
    if lat is None:
        at = _AT_COORDS.search(url)
        if at:
            lat, lng = float(at.group(1)), float(at.group(2))

    q_vals = qs.get("q") or qs.get("query") or []
    if q_vals:
        q = q_vals[0]
        qc = _Q_COORDS.match(q.strip())
        if qc:
            lat, lng = float(qc.group(1)), float(qc.group(2))
        elif not name:
            name = q.split("(")[0].strip()

    place = _PLACE_PATH.search(parsed.path)
    if place:
        name = unquote(place.group(1).replace("+", " ")).strip()
    elif not name:
        search = _SEARCH_PATH.search(parsed.path)
        if search:
            name = unquote(search.group(1).replace("+", " ")).strip()

    place_id = ""
    if qs.get("query_place_id"):
        place_id = qs["query_place_id"][0]
    else:
        pid = re.search(r"place_id[=:]([^&\s]+)", url, re.I)
        if pid:
            place_id = unquote(pid.group(1))
    if not place_id:
        chij = _CHIJ.search(url)
        if chij:
            place_id = chij.group(1)

    return {
        "name": _short_place_name(name),
        "latitude": lat,
        "longitude": lng,
        "place_id": place_id,
        "maps_url": url,
    }


def _places_api_key() -> str:
    return (os.environ.get("GOOGLE_PLACES_API_KEY") or "").strip()


def _photo_cdn_url(photo_reference: str) -> str:
    """Resolve Places Photo to a googleusercontent URL. Never return a URL that contains the API key."""
    key = _places_api_key()
    ref = (photo_reference or "").strip()
    if not key or not ref:
        return ""
    api_url = (
        "https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth=400&photo_reference={ref}&key={key}"
    )
    r = requests.get(api_url, allow_redirects=False, timeout=12)
    loc = r.headers.get("Location") or ""
    if loc.startswith("http") and "key=" not in loc.lower():
        return loc
    if r.status_code == 200 and (r.headers.get("Content-Type") or "").lower().startswith("image/"):
        return ""
    return ""


def _geom_lat_lng(obj: dict | None) -> tuple[float | None, float | None]:
    loc = ((obj or {}).get("geometry") or {}).get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None, None
    return float(lat), float(lng)


def resolve_place_and_photo(
    name: str,
    lat: float | None,
    lng: float | None,
    place_id: str,
) -> tuple[str, str, float | None, float | None, str]:
    """Look up a Google place, live photo CDN URL, coordinates, and venue name."""
    key = _places_api_key()
    pid = (place_id or "").strip()
    out_lat, out_lng = lat, lng
    out_name = _short_place_name(name)
    if not key:
        logger.warning("GOOGLE_PLACES_API_KEY is not set; skip watchlist place photo")
        return pid, "", out_lat, out_lng, out_name
    try:
        client = googlemaps.Client(key=key)
        photos: list = []

        def apply_result(result: dict) -> None:
            nonlocal pid, photos, out_lat, out_lng, out_name
            if not result:
                return
            pid = result.get("place_id") or pid
            if result.get("photos"):
                photos = result["photos"]
            glat, glng = _geom_lat_lng(result)
            if glat is not None:
                out_lat, out_lng = glat, glng
            place_name = (result.get("name") or "").strip()
            if place_name:
                out_name = _short_place_name(place_name)

        if pid.startswith("ChIJ"):
            det = client.place(pid, fields=["photo", "place_id", "geometry", "name"])
            apply_result(det.get("result") or {})

        if not pid and name:
            kwargs: dict = {
                "input": name,
                "input_type": "textquery",
                "fields": ["place_id", "photos", "name", "geometry"],
            }
            if lat is not None and lng is not None:
                kwargs["location_bias"] = f"point:{lat},{lng}"
            found = client.find_place(**kwargs)
            for cand in found.get("candidates") or []:
                apply_result(cand)
                if pid:
                    break

        if pid and (not photos or out_lat is None or not out_name):
            det = client.place(pid, fields=["photo", "place_id", "geometry", "name"])
            apply_result(det.get("result") or {})

        if not photos and lat is not None and lng is not None:
            nearby_kwargs: dict = {"location": (lat, lng), "radius": 150, "type": "cafe"}
            if name:
                nearby_kwargs["keyword"] = name
            nearby = client.places_nearby(**nearby_kwargs)
            for result in nearby.get("results") or []:
                apply_result(result)
                if photos:
                    break

        if not photos:
            logger.info("Places returned no photos name=%r pid=%r", name, pid)
            return pid, "", out_lat, out_lng, out_name
        return pid, _photo_cdn_url(photos[0].get("photo_reference") or ""), out_lat, out_lng, out_name
    except Exception:
        logger.exception("Places photo lookup failed")
        return pid, "", out_lat, out_lng, out_name


def attach_watchlist_photo(item: dict) -> dict:
    """Add a live Places thumb, coordinates, and venue name for the API response."""
    pid, photo_url, lat, lng, place_name = resolve_place_and_photo(
        item.get("name") or "",
        item.get("latitude"),
        item.get("longitude"),
        item.get("placeId") or "",
    )
    if pid and pid != (item.get("placeId") or ""):
        item["placeId"] = pid
    if lat is not None:
        item["latitude"] = lat
    if lng is not None:
        item["longitude"] = lng
    if place_name:
        item["name"] = place_name
    item["photoUrl"] = photo_url
    return item


def resolve_google_maps_url(url: str) -> tuple[str, str]:
    """Follow redirects; stay on Google hosts. Returns (final_url, html)."""
    current = url.strip()
    session = requests.Session()
    session.headers["User-Agent"] = _BROWSER_UA
    last_html = ""
    for _ in range(8):
        parsed = urlparse(current)
        if parsed.scheme not in ("http", "https") or not _host_ok(parsed.hostname):
            raise ValueError("Not a Google Maps link")
        r = session.get(current, allow_redirects=False, timeout=12)
        loc = r.headers.get("Location")
        if loc and r.status_code in (301, 302, 303, 307, 308):
            current = urljoin(current, loc)
            continue
        last_html = r.text or ""
        if "maps/place/" not in current:
            found = re.search(
                r"https://www\.google\.com/maps/place/[^\"'\s<>]+",
                last_html,
            )
            if found:
                return found.group(0), last_html
        return r.url or current, last_html
    raise ValueError("Too many redirects")


def preview_maps_link(raw: str) -> dict:
    """Resolve a shared Maps link (including maps.app.goo.gl) to name, coordinates, and photo."""
    url = extract_maps_url(raw) or (raw or "").strip()
    if not url:
        raise ValueError("No URL in that share")
    hint_name = (raw or "").replace(url, "").strip()
    final, _html = resolve_google_maps_url(url)
    parsed = parse_maps_url(final)
    if not parsed["name"] and hint_name:
        parsed["name"] = re.sub(r"\s+", " ", hint_name).strip()
    if not parsed["name"]:
        parsed["name"] = "Saved place"
    parsed["maps_url"] = final if "google.com/maps" in final else url
    pid, photo_url, plat, plng, place_name = resolve_place_and_photo(
        parsed["name"],
        parsed["latitude"],
        parsed["longitude"],
        parsed.get("place_id") or "",
    )
    if pid:
        parsed["place_id"] = pid
    if place_name:
        parsed["name"] = place_name
    if parsed.get("latitude") is None and plat is not None:
        parsed["latitude"] = plat
    if parsed.get("longitude") is None and plng is not None:
        parsed["longitude"] = plng
    parsed["photo_url"] = photo_url
    logger.info(
        "maps preview name=%r lat=%s lng=%s photo=%s",
        parsed["name"],
        parsed["latitude"],
        parsed["longitude"],
        bool(parsed["photo_url"]),
    )
    return parsed


def watchlist_key(parsed: dict) -> str:
    place_id = (parsed.get("place_id") or "").strip()
    if place_id:
        return f"watchlist:gmaps:{place_id}"
    lat, lng = parsed.get("latitude"), parsed.get("longitude")
    if lat is not None and lng is not None:
        return f"watchlist:gmaps:{float(lat):.5f},{float(lng):.5f}"
    name = re.sub(r"\s+", "-", (parsed.get("name") or "place").lower())[:48]
    return f"watchlist:gmaps:{name}"


def watchlist_item_from_preview(parsed: dict) -> dict:
    return {
        "key": watchlist_key(parsed),
        "kind": "watchlist",
        "name": parsed.get("name") or "Saved place",
        "latitude": parsed.get("latitude"),
        "longitude": parsed.get("longitude"),
        "mapsUrl": parsed.get("maps_url") or "",
        "placeId": parsed.get("place_id") or "",
        "source": "gmaps",
    }
