from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "cafehop-cafes")
REGION = os.environ.get("AWS_REGION", "us-east-1")
_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL")

_ddb_kwargs: dict = {"region_name": REGION}
if _ENDPOINT:
    _ddb_kwargs["endpoint_url"] = _ENDPOINT

_resource = boto3.resource("dynamodb", **_ddb_kwargs)
table = _resource.Table(TABLE_NAME)


def _serialize(obj: Any) -> Any:
    """Convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def _deserialize(obj: Any) -> Any:
    """Convert Decimal to float for JSON/Pydantic."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _deserialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deserialize(v) for v in obj]
    return obj


def get_item(cafe_id: str) -> dict | None:
    """Get one cafe by key. Returns None if not found."""
    try:
        resp = table.get_item(Key={"key": cafe_id})
        item = resp.get("Item")
        return _deserialize(item) if item else None
    except Exception as e:
        print(f"db get_item error: {e}")
        return None


def put_item(item: dict) -> None:
    """Insert or overwrite one cafe. Item must include 'key'."""
    table.put_item(Item=_serialize(item))


def scan_all(
    projection_expression: str | None = None,
    expression_attribute_names: dict | None = None,
) -> list[dict]:
    """Scan full table with optional projection; returns deserialized items."""
    kwargs = {}
    if projection_expression:
        kwargs["ProjectionExpression"] = projection_expression
    if expression_attribute_names:
        kwargs["ExpressionAttributeNames"] = expression_attribute_names
    items = []
    resp = table.scan(**kwargs)
    items.extend(resp.get("Items", []))
    while resp.get("LastEvaluatedKey"):
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
        items.extend(resp.get("Items", []))
    return [_deserialize(it) for it in items]


def scan(
    neighborhood: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Scan table with optional neighborhood filter; apply limit/offset."""
    kwargs = {}
    if neighborhood is not None and neighborhood.strip():
        from boto3.dynamodb.conditions import Attr

        kwargs["FilterExpression"] = Attr("neighborhood").eq(neighborhood)
    items = []
    resp = table.scan(**kwargs)
    items.extend(resp.get("Items", []))
    while resp.get("LastEvaluatedKey") and len(items) < offset + limit:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
        items.extend(resp.get("Items", []))
    items = [_deserialize(it) for it in items]
    return items[offset : offset + limit]


def update_item(cafe_id: str, updates: dict) -> dict | None:
    """
    Update attributes for one cafe. updates is a flat dict of attr -> value.
    Returns the updated item (ALL_NEW) or None on error.
    """
    if not updates:
        return get_item(cafe_id)
    expr_parts = []
    names = {}
    values = {}
    for i, (k, v) in enumerate(updates.items()):
        alias = f"#a{i}"
        val_alias = f":v{i}"
        names[alias] = k
        values[val_alias] = _serialize(v) if isinstance(v, (int, float)) else v
        expr_parts.append(f"set {alias} = {val_alias}")
    try:
        resp = table.update_item(
            Key={"key": cafe_id},
            UpdateExpression=" ".join(expr_parts),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        attrs = resp.get("Attributes")
        return _deserialize(attrs) if attrs else None
    except Exception as e:
        print(f"db update_item error: {e}")
        return None


def delete_item(cafe_id: str) -> dict | None:
    """Delete one cafe. Returns the deleted item (ALL_OLD) or None."""
    try:
        resp = table.delete_item(Key={"key": cafe_id}, ReturnValues="ALL_OLD")
        item = resp.get("Attributes")
        return _deserialize(item) if item else None
    except Exception as e:
        print(f"db delete_item error: {e}")
        return None


# Map DynamoDB/cafes.json keys (mixed camelCase/snake_case) to Cafe API model (snake_case)
def item_to_cafe_dict(item: dict) -> dict:
    """Convert a raw DynamoDB item to a dict suitable for Cafe(**kwargs)."""
    if not item:
        return {}
    return {
        "name": item.get("name", ""),
        "image_url": item.get("imageUrl") or item.get("image_url", ""),
        "s3_key": item.get("key") or item.get("s3_key", ""),
        "latitude": float(item["latitude"]) if item.get("latitude") is not None else 0.0,
        "longitude": float(item["longitude"]) if item.get("longitude") is not None else 0.0,
        "neighborhood": item.get("neighborhood", ""),
        "subway_station": item.get("subwayStation") or item.get("subway_station", ""),
        "subway_distance_m": float(item["subwayDistanceM"]) if item.get("subwayDistanceM") is not None else float(item.get("subway_distance_m", 0)) if item.get("subway_distance_m") is not None else 0.0,
        "subway_routes": item.get("subwayRoutes") or item.get("subway_routes") or [],
        "elo_rating": float(item["eloRating"]) if item.get("eloRating") is not None else float(item.get("elo_rating", 1500)),
        "elo_star_rating": float(item["eloStarRating"]) if item.get("eloStarRating") is not None else float(item.get("elo_star_rating", 0)),
        "notes": item.get("notes") or "",
        "google_maps_link": item.get("google_maps_link", ""),
        "google_maps_place_type": item.get("google_maps_place_type", ""),
        "closest_citibike_station_name": item.get("closest_citibike_station_name", ""),
        "closest_citibike_station_distance_m": float(item["closest_citibike_station_distance_m"]) if item.get("closest_citibike_station_distance_m") is not None else 0.0,
        "closest_citibike_station_walk_minutes": int(item["closest_citibike_station_walk_minutes"]) if item.get("closest_citibike_station_walk_minutes") is not None else 0,
        "share_card_png_url": item.get("shareCardPngUrl") or item.get("share_card_png_url", ""),
    }


def cafe_to_item(cafe_dict: dict) -> dict:
    """Convert Cafe.model_dump() (snake_case) to DynamoDB item (cafes.json shape)."""
    key = cafe_dict.get("s3_key") or cafe_dict.get("key", "")
    return {
        "key": key,
        "name": cafe_dict.get("name", ""),
        "imageUrl": cafe_dict.get("image_url", ""),
        "latitude": cafe_dict.get("latitude", 0),
        "longitude": cafe_dict.get("longitude", 0),
        "neighborhood": cafe_dict.get("neighborhood", ""),
        "subwayStation": cafe_dict.get("subway_station", ""),
        "subwayDistanceM": cafe_dict.get("subway_distance_m", 0),
        "subwayRoutes": cafe_dict.get("subway_routes", []),
        "eloRating": cafe_dict.get("elo_rating", 1500),
        "eloStarRating": cafe_dict.get("elo_star_rating", 0),
        "notes": cafe_dict.get("notes", ""),
        "google_maps_link": cafe_dict.get("google_maps_link", ""),
        "google_maps_place_type": cafe_dict.get("google_maps_place_type", ""),
        "closest_citibike_station_name": cafe_dict.get("closest_citibike_station_name", ""),
        "closest_citibike_station_distance_m": cafe_dict.get("closest_citibike_station_distance_m", 0),
        "closest_citibike_station_walk_minutes": cafe_dict.get("closest_citibike_station_walk_minutes", 0),
        "shareCardPngUrl": cafe_dict.get("share_card_png_url", ""),
    }
