import json
import boto3

s3 = boto3.client("s3")
BUCKET = "azamcafelistphotos"

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
                    "longitude": str(longitude) if longitude is not None else ""
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
