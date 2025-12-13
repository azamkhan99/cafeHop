import json
import boto3

s3 = boto3.client("s3")
BUCKET = "azamcafelistphotos"

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        content_type = body.get("contentType", "image/jpeg")
        cafe_name = body.get("cafeName", "").strip()
        rating = body.get("rating")
        notes = body.get("notes", "").strip()

        # Validate cafe name is provided
        if not cafe_name:
            return {
                "statusCode": 400,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*"
                },
                "body": json.dumps({
                    "error": "Cafe name is required"
                })
            }

        # Generate filename based on rating
        # Sanitize cafe name (remove special characters that might cause issues)
        safe_cafe_name = cafe_name.replace("/", "_").replace("\\", "_")
        
        # Check if rating is provided and valid
        rating_value = None
        if rating is not None and rating != "":
            try:
                rating_value = float(rating)
                if rating_value > 0:
                    # Format rating to integer if it's a whole number, otherwise keep decimal
                    rating_str = str(int(rating_value)) if rating_value == int(rating_value) else str(rating_value)
                    key = f"{safe_cafe_name}_{rating_str}_STARS.jpg"
                else:
                    key = f"{safe_cafe_name}_unvisited.jpg"
            except (ValueError, TypeError):
                key = f"{safe_cafe_name}_unvisited.jpg"
        else:
            key = f"{safe_cafe_name}_unvisited.jpg"

        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ContentType": content_type,
                "Metadata": {
                    "cafe-name": cafe_name,
                    "notes": notes or "",
                    "rating": str(rating_value) if rating_value else ""
                }
            },
            ExpiresIn=60
        )

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            },
            "body": json.dumps({
                "uploadUrl": url,
                "s3Key": key
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            },
            "body": json.dumps({
                "error": str(e)
            })
        }