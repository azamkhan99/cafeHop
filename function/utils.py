import os
import csv
from datetime import datetime
import requests
import http.client
import json
from PIL import Image, ExifTags
from io import BytesIO
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import math
import pickle

import time

geolocator = Nominatim(user_agent="azam_cafehop")

# Earth radius in meters
EARTH_RADIUS_M = 6371000

# Cache for GTFS data
_gtfs_cache = None

# Try to import numpy for efficient computation (optional)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def get_neighborhood(lat, lon):
    """Get neighborhood name from coordinates"""
    if not lat or not lon:
        return None
    try:
        location = geolocator.reverse(f"{lat}, {lon}", exactly_one=True)
        if location:
            address = location.raw.get('address', {})
            # Try to get neighborhood, or fall back to other location names
            neighborhood = (address.get('neighbourhood') or 
                          address.get('suburb') or 
                          address.get('city_district') or
                          address.get('quarter'))
            if neighborhood and isinstance(neighborhood, str) and neighborhood.startswith("Manhattan Community Board"):
                neighborhood = translate_manhattan_community_board(neighborhood)
            return neighborhood
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error for {lat}, {lon}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error for {lat}, {lon}: {e}")
        return None

def translate_manhattan_community_board(board_str):
    """
    Translate Manhattan Community Board names to approximate neighborhood names.

    Args:
        board_str (str): e.g., 'Manhattan Community Board 5'

    Returns:
        str or None: Human-readable neighborhood name, or None if not a CB or unknown.
    """
    cb_to_neighborhood = {
        'Manhattan Community Board 1': 'Financial District, Tribeca, Battery Park City',
        'Manhattan Community Board 2': 'Greenwich Village, SoHo, NoHo',
        'Manhattan Community Board 3': 'Lower East Side, Chinatown, East Village',
        'Manhattan Community Board 4': 'Chelsea, Hell\'s Kitchen (Clinton)',
        'Manhattan Community Board 5': 'Midtown, Flatiron, Times Square',
        'Manhattan Community Board 6': 'Murray Hill, Kips Bay, Gramercy',
        'Manhattan Community Board 7': 'Upper West Side',
        'Manhattan Community Board 8': 'Upper East Side, Yorkville',
        'Manhattan Community Board 9': 'Morningside Heights, Manhattanville',
        'Manhattan Community Board 10': 'Harlem',
        'Manhattan Community Board 11': 'East Harlem',
        'Manhattan Community Board 12': 'Washington Heights, Inwood'
    }
    if isinstance(board_str, str) and board_str in cb_to_neighborhood:
        match = cb_to_neighborhood[board_str].split(",")[0]
        return match
    return None

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


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth using Haversine formula.
    
    Parameters:
        lat1, lon1: Latitude and longitude of first point in decimal degrees
        lat2, lon2: Latitude and longitude of second point in decimal degrees
    
    Returns:
        float: Distance in meters
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_M * c


def _load_gtfs_data(pickle_path=None):
    """
    Load GTFS data from precomputed pickle file. Uses cached data if available.
    
    Parameters:
        pickle_path: Path to gtfs_precomputed.pkl file. If None, tries to find it relative to this file.
    
    Returns:
        dict: Dictionary containing precomputed GTFS data
    """
    global _gtfs_cache
    
    if _gtfs_cache is not None:
        return _gtfs_cache
    
    # Try to find pickle file
    if pickle_path is None:
        # Try relative to utils.py location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        pickle_path = os.path.join(os.path.dirname(current_dir), 'gtfs_precomputed.pkl')
    
    if not os.path.exists(pickle_path):
        # If pickle file isn't available, return None
        return None
    
    try:
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
        
        # Cache the loaded data
        _gtfs_cache = data
        return _gtfs_cache
    except Exception as e:
        print(f"Error loading GTFS pickle file: {e}")
        return None


def get_closest_subway_station(lat, lon, pickle_path=None):
    """
    Find the closest NYC subway station to given coordinates using precomputed GTFS data.
    
    Parameters:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        pickle_path: Path to gtfs_precomputed.pkl file (optional)
    
    Returns:
        dict: {
            'station': str,  # Station name
            'distance_m': float,  # Distance in meters
            'lines': list  # List of route names (e.g., ['1', '2', '3'])
        } or None if GTFS data not available
    """
    if not lat or not lon:
        return None
    
    gtfs_data = _load_gtfs_data(pickle_path)
    if gtfs_data is None:
        return None
    
    # Extract data from pickle
    station_coords = gtfs_data['station_coords']  # numpy array in radians
    stop_names = gtfs_data['stop_names']  # numpy array or list
    stop_ids = gtfs_data['stop_ids']  # numpy array or list
    stop_to_routes = gtfs_data['stop_to_routes']  # dict
    route_id_to_name = gtfs_data['route_id_to_name']  # dict
    parent_stations = gtfs_data['parent_stations']  # numpy array or list
    
    # Convert to lists if numpy arrays (for compatibility)
    if HAS_NUMPY and isinstance(stop_names, np.ndarray):
        stop_names = stop_names.tolist()
    if HAS_NUMPY and isinstance(stop_ids, np.ndarray):
        stop_ids = stop_ids.tolist()
    if HAS_NUMPY and isinstance(parent_stations, np.ndarray):
        parent_stations = parent_stations.tolist()
    
    # Use numpy for efficient distance calculation if available
    if HAS_NUMPY and isinstance(station_coords, np.ndarray):
        # Convert input to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        
        # Calculate distances using numpy (vectorized)
        dlat = station_coords[:, 0] - lat_rad
        dlon = station_coords[:, 1] - lon_rad
        a = np.sin(dlat / 2)**2 + np.cos(lat_rad) * np.cos(station_coords[:, 0]) * np.sin(dlon / 2)**2
        distances = 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))
        
        # Find closest stop
        closest_idx = np.argmin(distances)
        distance_m = float(distances[closest_idx])
    else:
        # Fallback to Python loop if numpy not available
        min_distance = float('inf')
        closest_idx = None
        
        # Convert station_coords from radians to degrees for haversine_distance
        # (station_coords are stored in radians, but haversine_distance expects degrees)
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        
        for idx, coord in enumerate(station_coords):
            stop_lat_rad = coord[0]  # already in radians
            stop_lon_rad = coord[1]  # already in radians
            
            # Calculate haversine distance directly in radians
            dlat = stop_lat_rad - lat_rad
            dlon = stop_lon_rad - lon_rad
            a = math.sin(dlat / 2)**2 + math.cos(lat_rad) * math.cos(stop_lat_rad) * math.sin(dlon / 2)**2
            distance = 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
            
            if distance < min_distance:
                min_distance = distance
                closest_idx = idx
        
        if closest_idx is None:
            return None
        
        distance_m = min_distance
    
    # Get stop info
    closest_stop_id = stop_ids[closest_idx]
    parent_id = parent_stations[closest_idx] if parent_stations[closest_idx] else closest_stop_id
    
    # Get all stops for this parent station
    station_stop_ids = []
    for idx, sid in enumerate(stop_ids):
        pid = parent_stations[idx] if parent_stations[idx] else sid
        if pid == parent_id:
            station_stop_ids.append(sid)
    
    if parent_id not in station_stop_ids:
        station_stop_ids.append(parent_id)
    
    # Aggregate all routes for this station
    all_route_ids = set()
    for sid in station_stop_ids:
        if sid in stop_to_routes:
            routes = stop_to_routes[sid]
            if isinstance(routes, set):
                all_route_ids.update(routes)
            else:
                all_route_ids.update(routes)
    
    # Convert route_ids to route names
    lines = sorted([route_id_to_name.get(rid, rid) for rid in all_route_ids if rid in route_id_to_name])
    
    # Get station name (use parent station name if available)
    if parent_id in stop_ids:
        parent_idx = stop_ids.index(parent_id)
        station_name = stop_names[parent_idx]
    else:
        station_name = stop_names[closest_idx]
    
    return {
        'station': station_name,
        'distance_m': str(round(distance_m, 1)) + 'm',
        'lines': ','.join([line.lower() for line in lines])
    }
