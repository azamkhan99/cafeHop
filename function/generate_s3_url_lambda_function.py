import json
import boto3
import os

# Import utils for computing neighborhood and subway station
try:
    from utils import get_neighborhood, get_closest_subway_station
except ImportError:
    # Fallback if utils not available
    get_neighborhood = None
    get_closest_subway_station = None

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]

# CORS headers for GitHub Pages
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://azamkhan99.github.io",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "POST, OPTIONS"
}

def lambda_handler(event, context):
    # Handle preflight OPTIONS request
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": ""
        }

    try:
        body = json.loads(event.get("body", "{}"))
        content_type = body.get("contentType", "image/jpeg")
        cafe_name = body.get("cafeName", "").strip()
        rating = body.get("rating")
        notes = body.get("notes", "").strip()
        latitude = body.get("latitude")
        longitude = body.get("longitude")
        
        # Compute neighborhood and subway station from coordinates if available
        neighborhood = ""
        closest_subway_station = ""
        closest_subway_lines = ""
        
        if latitude is not None and longitude is not None:
            try:
                # Compute neighborhood
                if get_neighborhood:
                    computed_neighborhood = get_neighborhood(float(latitude), float(longitude))
                    if computed_neighborhood:
                        neighborhood = computed_neighborhood
                
                # Compute closest subway station
                if get_closest_subway_station:
                    subway_data = get_closest_subway_station(float(latitude), float(longitude))
                    if subway_data:
                        closest_subway_station = subway_data.get('station', '')
                        lines = subway_data.get('lines', [])
                        if lines:
                            closest_subway_lines = ','.join(lines)
            except Exception as e:
                # Log error but don't fail the request
                print(f"Error computing metadata: {e}")
        
        # Allow override from request body if provided
        if body.get("neighborhood", "").strip():
            neighborhood = body.get("neighborhood", "").strip()
        if body.get("closestSubwayStation", "").strip():
            closest_subway_station = body.get("closestSubwayStation", "").strip()
        if body.get("closestSubwayLines", "").strip():
            closest_subway_lines = body.get("closestSubwayLines", "").strip()

        if not cafe_name:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Cafe name is required"})
            }

        # Sanitize cafe name
        safe_cafe_name = cafe_name.replace("/", "_").replace("\\", "_")

        # Generate filename
        rating_value = None
        if rating is not None and rating != "":
            try:
                rating_value = float(rating)
                if rating_value > 0:
                    rating_str = str(int(rating_value)) if rating_value == int(rating_value) else str(rating_value)
                    key = f"{safe_cafe_name}_{rating_str}_STARS.jpg"
                else:
                    key = f"{safe_cafe_name}_unvisited.jpg"
            except (ValueError, TypeError):
                key = f"{safe_cafe_name}_unvisited.jpg"
        else:
            key = f"{safe_cafe_name}_unvisited.jpg"

        # Generate presigned URL with metadata
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ContentType": content_type,
                "Metadata": {
                    "cafe-name": cafe_name,
                    "notes": notes or "",
                    "rating": str(rating_value) if rating_value else "",
                    "latitude": str(latitude) if latitude is not None else "",
                    "longitude": str(longitude) if longitude is not None else "",
                    "neighborhood": neighborhood or "",
                    "closest_subway_station": closest_subway_station or "",
                    "closest_subway_lines": closest_subway_lines or ""
                }
            },
            ExpiresIn=60
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"uploadUrl": url, "s3Key": key})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }