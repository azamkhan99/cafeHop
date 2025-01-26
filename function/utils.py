import os
import csv
from datetime import datetime
import requests
import http.client
import json


def get_place_id(api_key, place_name):
    """Fetch the Place ID for a given place name."""
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "key": api_key,
        "input": place_name,
        "inputtype": "textquery",
        "fields": "place_id",
    }
    response = requests.get(url, params=params)
    response_data = response.json()

    if response.status_code == 200 and response_data.get("candidates"):
        return response_data["candidates"][0]["place_id"]
    else:
        raise Exception("Failed to fetch Place ID. Check the place name or API key.")


def get_photo_reference(api_key, place_id):
    """Fetch the photo reference for a given Place ID."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "key": api_key,
        "place_id": place_id,
        "fields": "photos",
    }
    response = requests.get(url, params=params)
    response_data = response.json()

    if (
        response.status_code == 200
        and response_data.get("result")
        and response_data["result"].get("photos")
    ):
        return response_data["result"]["photos"][0]["photo_reference"]
    else:
        raise Exception(
            "Failed to fetch photo reference. Check the Place ID or API key."
        )


def get_photo_url(api_key, photo_reference):
    """Generate the photo URL using the photo reference."""
    return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={api_key}"


def download_most_recent_nyc_coffee_csv(access_key):
    """
    Download the NYC Coffee.csv from the most recent takeout directory.

    Parameters:
    -----------
    dbx : dropbox.Dropbox
        An authenticated Dropbox client

    Returns:
    --------
    list of dict
        The contents of the NYC Coffee.csv file as a list of dictionaries
    """
    conn = http.client.HTTPSConnection("api.dropboxapi.com")
    payload = json.dumps(
        {
            "include_deleted": False,
            "include_has_explicit_shared_members": False,
            "include_media_info": False,
            "include_mounted_folders": True,
            "include_non_downloadable_files": True,
            "path": "/Apps/Google Download Your Data/",
            "recursive": False,
        }
    )
    headers = {
        "Authorization": f"Bearer {access_key}",
        "Content-Type": "application/json",
    }
    conn.request("POST", "/2/files/list_folder", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    data_dict = json.loads(data)

    # List the takeout directories
    takeout_dirs = [
        entry["path_display"]
        for entry in data_dict["entries"]
        if entry["name"].startswith("takeout-")
    ]

    # Find the most recent takeout directory
    if not takeout_dirs:
        raise ValueError("No takeout directories found")

    most_recent_takeout = max(
        takeout_dirs,
        key=lambda x: datetime.strptime(x.split("takeout-")[1].split("T")[0], "%Y%m%d"),
    )

    # Construct the full path to NYC Coffee.csv
    file_path = os.path.join(most_recent_takeout, "Takeout/Saved/NYC Coffee.csv")
    print(file_path)
    # Download the file
    try:
        conn = http.client.HTTPSConnection("content.dropboxapi.com")
        payload = ""
        headers = {
            "Authorization": f"Bearer {access_key}",
            # "Dropbox-API-Arg": f'{"path":"/Apps/Google Download Your Data/takeout-20250125T205304Z-001/Takeout/Saved/NYC Coffee.csv"}',
            "Dropbox-API-Arg": f'{{"path":"{file_path}"}}',
        }
        conn.request("POST", "/2/files/download", payload, headers)
        res = conn.getresponse()
        data = res.read()
        print(data.decode("utf-8"))
        # Save the file locally
        reader = csv.DictReader(data.decode("utf-8").splitlines())
        return [row for row in reader]

    except Exception as e:
        print(f"Error downloading file: {e}")
        raise
