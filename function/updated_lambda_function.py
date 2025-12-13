import json
import boto3
import os
import uuid
import io
from PIL import Image, ExifTags
from io import BytesIO

s3 = boto3.client("s3")
BUCKET = "azamcafelistphotos"

def dms_to_decimal(dms, ref):
    """
    Convert GPS coordinates in DMS format to decimal degrees.

    Parameters:
        dms (tuple): (degrees, minutes, seconds) from Pillow GPSInfo
        ref (str): 'N', 'S', 'E', or 'W'

    Returns:
        float: decimal degrees
    """
    degrees, minutes, seconds = dms
    decimal = degrees + minutes / 60 + seconds / 3600

    # South and West are negative
    if ref in ["S", "W"]:
        decimal *= -1

    return decimal

def convert_to_jpg(image):
    """Convert an image to JPG format while keeping metadata."""
    img_byte_arr = io.BytesIO()
    if image.format != "JPEG":
        img = image.convert("RGB")
        img.save(img_byte_arr, format="JPEG", exif=image.info.get("exif"))
    else:
        image.save(img_byte_arr, format="JPEG", exif=image.info.get("exif"))
    return img_byte_arr.getvalue()

def get_image_lat_long(img):
    """
    Get the latitude and longitude of an image using its EXIF data.
    """
    # Handle both bytes and BytesIO objects
    if isinstance(img, bytes):
        img = Image.open(BytesIO(img))
    else:
        img = Image.open(img)
    exif = {ExifTags.TAGS.get(k, k): v for k, v in (img._getexif() or {}).items()}

    gpsinfo = {}
    if "GPSInfo" not in exif:
        return None

    for key in exif["GPSInfo"].keys():
        decode = ExifTags.GPSTAGS.get(key, key)
        gpsinfo[decode] = exif["GPSInfo"][key]

    latitude = gpsinfo.get("GPSLatitude")
    longitude = gpsinfo.get("GPSLongitude")
    lat_ref = gpsinfo.get("GPSLatitudeRef")
    lon_ref = gpsinfo.get("GPSLongitudeRef")

    if not latitude or not longitude:
        return None

    lat = dms_to_decimal(latitude, lat_ref)
    lon = dms_to_decimal(longitude, lon_ref)

    return (float(lat), float(lon))

# def rename_convert_upload(image):
#     filename = st.text_input("Enter a filename:", placeholder="Location_X_STARS")
#     filename = f"{filename}.jpg"
#     if st.button("Upload"):
#         jpg_image = convert_to_jpg(image)
#         latitude, longitude = get_image_lat_long(jpg_image)
#         image_gps = {
#             "latitude": str(latitude),
#             "longitude": str(longitude),
#         }
#         s3_url = upload_to_s3(jpg_image, filename, image_gps)
#         st.toast(f"Image uploaded successfully!")
#         st.session_state.rename_convert_upload = s3_url
#         st.rerun()

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