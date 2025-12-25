import json
import boto3
import os
import random
from io import BytesIO
from PIL import Image, ImageOps

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

def update_cafes_json(cafe_data):
    """
    Update the cafes.json file in S3 with new cafe data.
    Reads existing JSON, adds/updates the cafe entry, and writes back.
    
    Args:
        cafe_data: dict with cafe information (key, name, imageUrl, etc.)
    
    Returns:
        bool: True if successful, False otherwise
    """
    CAFES_JSON_KEY = "cafes.json"
    
    try:
        # Try to read existing JSON file
        try:
            response = s3.get_object(Bucket=BUCKET, Key=CAFES_JSON_KEY)
            existing_data = json.loads(response['Body'].read().decode('utf-8'))
            cafes = existing_data.get('cafes', [])
        except s3.exceptions.NoSuchKey:
            # File doesn't exist yet, start with empty list
            cafes = []
        
        # Remove existing entry with same key if it exists (for updates)
        cafes = [c for c in cafes if c.get('key') != cafe_data.get('key')]
        
        # Add new cafe entry
        cafes.append(cafe_data)
        
        # Sort by ELO star rating (highest first), then by name
        # This matches the default client-side sort for better initial load performance
        def sort_key(cafe):
            elo_star = cafe.get('eloStarRating')
            if elo_star is None:
                elo_star = -float('inf')
            else:
                try:
                    elo_star = float(elo_star)
                except (ValueError, TypeError):
                    elo_star = -float('inf')
            name = cafe.get('name', '')
            # Return tuple for multi-level sort: (-rating for desc, name for asc)
            return (-elo_star, name)
        
        cafes.sort(key=sort_key)
        
        # Write back to S3
        from datetime import datetime
        updated_data = {
            'cafes': cafes,
            'lastUpdated': datetime.utcnow().isoformat() + 'Z'
        }
        
        s3.put_object(
            Bucket=BUCKET,
            Key=CAFES_JSON_KEY,
            Body=json.dumps(updated_data, indent=2),
            ContentType='application/json',
            CacheControl='max-age=300'  # Cache for 5 minutes
        )
        
        print(f"Successfully updated cafes.json with cafe: {cafe_data.get('key')}")
        return True
        
    except Exception as e:
        print(f"Error updating cafes.json: {e}")
        return False

def handle_update_cafes(event, context):
    """
    Handle request to update cafes.json after an upload completes.
    Client calls this after successfully uploading to S3.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        key = body.get("s3Key")
        
        if not key:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "s3Key is required"})
            }
        
        # Get the uploaded object's metadata and LastModified
        try:
            response = s3.head_object(Bucket=BUCKET, Key=key)
            metadata = response.get('Metadata', {})
            last_modified = response.get('LastModified', '').isoformat() if response.get('LastModified') else ''
        except Exception as e:
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": f"Object not found: {e}"})
            }
        
        # Parse cafe name from key (remove extension)
        cafe_name = key.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('.gif', '')
        
        # Extract metadata
        # S3 stores metadata with x-amz-meta- prefix, but when you set it with x-amz-meta- prefix,
        # it might be stored as x-amz-meta-x-amz-meta-... so check both variations
        neighborhood = metadata.get('x-amz-meta-x-amz-meta-neighborhood', '') or metadata.get('x-amz-meta-neighborhood', '') or metadata.get('neighborhood', '')
        subway_lines = metadata.get('x-amz-meta-x-amz-meta-closest_subway_lines', '') or metadata.get('x-amz-meta-closest_subway_lines', '') or metadata.get('closest_subway_lines', '')
        latitude = metadata.get('x-amz-meta-x-amz-meta-latitude', '') or metadata.get('x-amz-meta-latitude', '') or metadata.get('latitude', '')
        longitude = metadata.get('x-amz-meta-x-amz-meta-longitude', '') or metadata.get('x-amz-meta-longitude', '') or metadata.get('longitude', '')
        elo_star_rating = metadata.get('x-amz-meta-x-amz-meta-elo_star_rating', '') or metadata.get('x-amz-meta-elo_star_rating', '') or metadata.get('elo_star_rating', '')
        notes = metadata.get('x-amz-meta-x-amz-meta-notes', '') or metadata.get('x-amz-meta-notes', '') or metadata.get('notes', '')
        
        # Parse subway routes
        subway_routes = []
        if subway_lines:
            subway_routes = [r.strip().lower() for r in subway_lines.split(',') if r.strip()]
        
        # Generate map thumbnail only (gallery uses the 800px uploaded image)
        map_thumbnail_url = None
        try:
            # Download the uploaded image (already resized to 800px on client)
            image_obj = s3.get_object(Bucket=BUCKET, Key=key)
            image_data = image_obj['Body'].read()
            
            # Open image
            img = Image.open(BytesIO(image_data))
            
            # Apply EXIF orientation - primarily handle orientation 6 (90° CCW, most common)
            # Use exif_transpose first (handles all cases), with fallback for orientation 6
            try:
                # Try exif_transpose first (handles all EXIF orientations correctly)
                img = ImageOps.exif_transpose(img)
            except Exception:
                # If exif_transpose fails, manually check for orientation 6 (90° CCW)
                try:
                    exif = img.getexif()
                    if exif is not None:
                        orientation = exif.get(274)  # EXIF tag 274 is Orientation
                        if orientation == 6:
                            # Rotate 90° counter-clockwise (most common for phone photos)
                            img = img.rotate(-90, expand=True)
                except Exception:
                    # If EXIF reading fails, continue with image as-is
                    pass
            
            # Convert to RGB if necessary (handles PNG with transparency, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Generate map thumbnail (150px max width for 70px display)
            max_width_map = 150
            if img.width > max_width_map:
                ratio = max_width_map / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width_map, new_height), Image.Resampling.LANCZOS)
            
            map_thumbnail_buffer = BytesIO()
            img.save(map_thumbnail_buffer, format='JPEG', quality=75, optimize=True)  # Lower quality for smaller file
            map_thumbnail_buffer.seek(0)
            
            # Store map thumbnail in mapThumbnails/ folder
            map_thumbnail_key = f"mapThumbnails/{key}"
            s3.put_object(
                Bucket=BUCKET,
                Key=map_thumbnail_key,
                Body=map_thumbnail_buffer.getvalue(),
                ContentType='image/jpeg',
                CacheControl='max-age=31536000'  # Cache for 1 year
            )
            map_thumbnail_url = f"https://{BUCKET}.s3.us-east-1.amazonaws.com/{map_thumbnail_key}"
            print(f"Generated map thumbnail: {map_thumbnail_key}")
        except Exception as e:
            print(f"Error generating map thumbnail: {e}")
            # Continue without map thumbnail - use full image URL as fallback
            map_thumbnail_url = f"https://{BUCKET}.s3.us-east-1.amazonaws.com/{key}"
        
        # Build cafe data
        # The uploaded image (800px) is used as the "full" image for gallery
        # Only generate map thumbnail (150px) for map popups
        image_url = f"https://{BUCKET}.s3.us-east-1.amazonaws.com/{key}"
        cafe_data = {
            'key': key,
            'name': cafe_name,
            'imageUrl': image_url,  # 800px image uploaded from client
            'thumbnailUrl': image_url,  # Same as imageUrl since it's already optimized
            'mapThumbnailUrl': map_thumbnail_url or image_url,  # Fallback to full image if map thumbnail failed
            'lastModified': last_modified,
            'neighborhood': neighborhood if neighborhood else None,
            'subwayRoutes': subway_routes if subway_routes else None,
            'latitude': float(latitude) if latitude else None,
            'longitude': float(longitude) if longitude else None,
            'eloStarRating': float(elo_star_rating) if elo_star_rating else None,
            'notes': notes if notes else None
        }
        
        # Update cafes.json
        success = update_cafes_json(cafe_data)
        
        if success:
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({"message": "Cafes.json updated successfully"})
            }
        else:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Failed to update cafes.json"})
            }
            
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
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

    # Check if this is a request to update cafes.json (after upload)
    # Check both path and routeKey for API Gateway v2
    path = event.get("requestContext", {}).get("http", {}).get("path", "") or event.get("rawPath", "")
    route_key = event.get("requestContext", {}).get("routeKey", "")
    
    # Parse body to check for action
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception as e:
        print(f"Error parsing body: {e}")
        body = {}
    
    if "/update-cafes" in path or "update-cafes" in route_key or body.get("action") == "update-cafes":
        return handle_update_cafes(event, context)

    try:
        content_type = body.get("contentType", "image/jpeg")
        cafe_name = body.get("cafeName", "").strip()
        notes = body.get("notes", "").strip()
        latitude = body.get("latitude")
        longitude = body.get("longitude")
        
        # Compute neighborhood and subway station from coordinates if available
        neighborhood = ""
        closest_subway_station = ""
        closest_subway_lines = ""
        closest_subway_distance = ""
        
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
                        distance_m = subway_data.get('distance_m')
                        if distance_m is not None:
                            closest_subway_distance = str(distance_m)
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

        # Generate filename (all cafes are visited, no need for _unvisited suffix)
        key = f"{safe_cafe_name}.jpg"

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
                    "latitude": str(latitude) if latitude is not None else "",
                    "longitude": str(longitude) if longitude is not None else "",
                    "x-amz-meta-neighborhood": neighborhood or "",
                    "closest_subway_station": closest_subway_station or "",
                    "closest_subway_station_distance_m": closest_subway_distance or "",
                    "closest_subway_lines": closest_subway_lines or "",
                    "elo_rating": str(initial_elo),
                    "elo_star_rating": str(elo_star_rating),
                    "x-amz-meta-notes": notes or ""
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