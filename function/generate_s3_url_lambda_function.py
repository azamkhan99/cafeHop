import json
import boto3
import os
import random

# Import utils for computing neighborhood and subway station
try:
    from utils import get_neighborhood, get_closest_subway_station
except ImportError:
    # Fallback if utils not available
    get_neighborhood = None
    get_closest_subway_station = None

# Import elo ranking function
try:
    from elo_ranking import log_new_cafe_elo, elo_to_cups
except ImportError:
    log_new_cafe_elo = None

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET_NAME"]

# CORS headers for GitHub Pages and local development
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",  # Allow all origins for development, can restrict to specific domain in production
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "POST, OPTIONS"
}

def get_random_cafes_with_elo(num_cafes=5):
    """
    Fetch random cafes from S3 and return their keys and Elo ratings.
    
    Returns:
        list: List of tuples (cafe_key, elo_rating) where elo_rating is float or None
    """
    try:
        # List all objects in the bucket
        paginator = s3.get_paginator('list_objects_v2')
        all_keys = []
        
        for page in paginator.paginate(Bucket=BUCKET):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Only include image files
                    if key.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        all_keys.append(key)
        
        if not all_keys:
            return []
        
        # Select random cafes (up to num_cafes, or all if fewer exist)
        num_to_select = min(num_cafes, len(all_keys))
        random_keys = random.sample(all_keys, num_to_select)
        
        # Get Elo ratings from metadata
        cafes_with_elo = []
        for key in random_keys:
            try:
                # Get object metadata
                response = s3.head_object(Bucket=BUCKET, Key=key)
                metadata = response.get('Metadata', {})
                
                # Try to get Elo rating from metadata
                # S3 metadata keys are lowercase and may have x-amz-meta- prefix
                # Check multiple variations since S3 normalizes keys
                elo_str = (
                    metadata.get('x-amz-meta-elo-rating') or
                    metadata.get('x-amz-meta-elo_rating') or
                    metadata.get('elo_rating') or
                    metadata.get('elo-rating') or
                    None
                )
                
                elo_rating = None
                if elo_str:
                    try:
                        elo_rating = float(elo_str)
                    except (ValueError, TypeError):
                        pass
                
                cafes_with_elo.append((key, elo_rating))
            except Exception as e:
                # If we can't get metadata for a cafe, skip it
                print(f"Error getting metadata for {key}: {e}")
                continue
        
        return cafes_with_elo
    except Exception as e:
        print(f"Error fetching random cafes: {e}")
        return []

def compute_initial_elo_rating(comparisons=None):
    """
    Compute initial Elo rating for a new cafe by comparing against existing cafes.
    
    Parameters:
        comparisons: List of tuples (cafe_key, score) where score is 1.0 (new cafe wins),
                     0.0 (existing cafe wins), or 0.5 (tie). If None, uses neutral comparisons.
    
    Returns:
        float: Initial Elo rating for the new cafe
    """
    DEFAULT_ELO = 1500.0
    
    # Get 5 random cafes with their Elo ratings
    random_cafes = get_random_cafes_with_elo(5)
    
    if not random_cafes:
        # No existing cafes, use default
        return DEFAULT_ELO
    
    # Filter cafes that have Elo ratings
    cafes_with_elo = [(key, elo) for key, elo in random_cafes if elo is not None]
    
    if not cafes_with_elo:
        # No cafes with Elo ratings, use default
        return DEFAULT_ELO
    
    # If we have the log_new_cafe_elo function, use it
    if log_new_cafe_elo:
        try:
            # Prepare data for log_new_cafe_elo
            # Use cafe keys as IDs
            cafe_ids = [key for key, _ in cafes_with_elo]
            existing_elos = {key: elo for key, elo in cafes_with_elo}
            existing_has_compared = {key: False for key in cafe_ids}
            
            # Use provided comparisons, or default to neutral (0.5 score)
            if comparisons is not None:
                # Filter comparisons to only include cafes we have Elo ratings for
                valid_comparisons = [(key, score) for key, score in comparisons if key in existing_elos]
                if valid_comparisons:
                    comparisons_to_use = valid_comparisons
                else:
                    # If no valid comparisons, use neutral
                    comparisons_to_use = [(key, 0.5) for key in cafe_ids]
            else:
                # Use neutral comparisons (0.5 score) to compute initial Elo
                comparisons_to_use = [(key, 0.5) for key in cafe_ids]
            
            new_elo, _ = log_new_cafe_elo(
                initial_elo=DEFAULT_ELO,
                comparisons=comparisons_to_use,
                existing_elos=existing_elos,
                existing_has_compared=existing_has_compared
            )
            
            return new_elo
        except Exception as e:
            print(f"Error computing Elo with log_new_cafe_elo: {e}")
            # Fall through to simple average
    
    # Fallback: use average of existing Elo ratings
    elo_values = [elo for _, elo in cafes_with_elo]
    average_elo = sum(elo_values) / len(elo_values)
    
    # Start slightly below average to be conservative
    return average_elo - 50.0

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
                    key = f"{safe_cafe_name}.jpg"
                else:
                    key = f"{safe_cafe_name}_unvisited.jpg"
            except (ValueError, TypeError):
                key = f"{safe_cafe_name}_unvisited.jpg"
        else:
            key = f"{safe_cafe_name}_unvisited.jpg"

        # Get comparison results from request body if provided
        comparisons = body.get("comparisons")  # List of [cafe_key, score] tuples
        if comparisons:
            # Convert to list of tuples
            try:
                comparisons = [(item[0], float(item[1])) for item in comparisons]
            except (ValueError, TypeError, IndexError):
                print(f"Invalid comparisons format: {comparisons}")
                comparisons = None
        
        # Compute initial Elo rating for the new cafe
        try:
            initial_elo = compute_initial_elo_rating(comparisons=comparisons)
            if initial_elo:
                # Convert to cups
                elo_star_rating = elo_to_cups(initial_elo)
                print(f"Initial Elo STAR rating: {elo_star_rating}")
        except Exception as e:
            print(f"Error computing Elo rating: {e}")
            # Use default if computation fails
            initial_elo = 1500.0
            elo_star_rating = elo_to_cups(initial_elo)

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
                    "x-amz-meta-neighborhood": neighborhood or "",
                    "closest_subway_station": closest_subway_station or "",
                    "closest_subway_lines": closest_subway_lines or "",
                    "elo_rating": str(initial_elo),
                    "elo_star_rating": str(elo_star_rating)
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