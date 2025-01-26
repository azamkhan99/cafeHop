import os
import json
import requests

# import pandas as pd
from utils import (
    get_place_id,
    get_photo_reference,
    download_most_recent_nyc_coffee_csv,
    get_photo_url,
)

# import dropbox
import boto3
import base64
import io
from dotenv import load_dotenv


def lambda_handler(event, context):
    load_dotenv()
    """AWS Lambda function to retrieve Place ID and photo reference."""
    bucket_name = "azamcafelistphotos"
    region = "us-east-1"
    client = boto3.client("s3", region_name=region)
    resource = boto3.resource("s3", region_name=region)
    # Extract place name from the event
    print("HERE")
    # Get API key from environment variables
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"statusCode": 500, "body": json.dumps({"error": "API key not found."})}

    # try:
    # Retrieve Place ID
    # cafes_df = download_most_recent_nyc_coffee_csv(dbx)
    # # print(cafes_df.head())
    # for place_name, note in cafes_df[["Title", "Note"]].values:
    #     place_id = get_place_id(api_key, place_name)
    #     # Retrieve photo reference
    #     photo_reference = get_photo_reference(api_key, place_id)

    #     photo_url = get_photo_url(api_key, photo_reference)

    #     photo_response = requests.get(photo_url)

    #     decoded_image = base64.b64encode(photo_response.content).decode("utf-8")
    #     image_file = io.BytesIO(base64.b64decode(decoded_image))

    #     if not pd.isna(note):
    #         file_name = f"{place_name}_{note}.jpg"
    #     else:
    #         file_name = f"{place_name}_unvisited.jpg"
    #     print(f"Uploading photo for: {place_name}")
    dropbox_access_token = os.environ.get("DROPBOX_ACCESS_TOKEN")
    cafes = download_most_recent_nyc_coffee_csv(dropbox_access_token)

    for row in cafes:
        place_name = row["Title"]
        note = row.get("Note")  # Use .get() to safely handle missing keys

        place_id = get_place_id(api_key, place_name)
        # Retrieve photo reference
        photo_reference = get_photo_reference(api_key, place_id)

        photo_url = get_photo_url(api_key, photo_reference)

        photo_response = requests.get(photo_url)

        decoded_image = base64.b64encode(photo_response.content).decode("utf-8")
        image_file = io.BytesIO(base64.b64decode(decoded_image))

        # Check if `note` is not empty or None
        if note and note.strip():  # Ensure note is not empty or whitespace
            file_name = f"{place_name}_{note}.jpg"
        else:
            file_name = f"{place_name}_unvisited.jpg"
        print(f"Uploading photo for: {place_name}")
        # upload photo to S3
        # client.upload_fileobj(
        #     image_file,
        #     bucket_name,
        #     f"{file_name}",
        # )
        # resource.Object(bucket_name, f"{file_name}").wait_until_exists()

    return {
        "statusCode": 200,
        "body": json.dumps({"place_id": place_id, "photo_reference": photo_reference}),
    }
    # except Exception as e:
    #     return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    event = {"place_name": "Starbucks"}
    lambda_handler(event, None)
