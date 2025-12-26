from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import math
import pickle
import os
import json
import googlemaps
gmaps_api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
nominatim_api_key = os.environ.get('NOMINATIM_API_KEY')
geolocator = Nominatim(user_agent=nominatim_api_key)

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


def _load_gtfs_data(json_path=None):
    """
    Load GTFS data from precomputed JSON file. Uses cached data if available.
    
    Parameters:
        json_path: Path to gtfs_precomputed.json file. If None, tries to find it relative to this file.
    
    Returns:
        dict: Dictionary containing precomputed GTFS data
    """
    global _gtfs_cache
    
    if _gtfs_cache is not None:
        return _gtfs_cache
    
    # Try to find JSON file
    if json_path is None:
        # Try in the same directory as utils.py (function/ directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'gtfs_precomputed.json')
        
        # Fallback: try parent directory (for local development)
        if not os.path.exists(json_path):
            json_path = os.path.join(os.path.dirname(current_dir), 'gtfs_precomputed.json')
    
    if not os.path.exists(json_path):
        # If JSON file isn't available, return None
        print(f"GTFS JSON file not found at: {json_path}")
        return None
    
    try:
        # Check file size
        file_size = os.path.getsize(json_path)
        if file_size == 0:
            print(f"GTFS JSON file is empty: {json_path}")
            return None
        
        # Load JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert lists back to numpy arrays if numpy is available (for efficient computation)
        if HAS_NUMPY:
            # Convert station_coords back to numpy array (it's stored as list of [lat, lon] in radians)
            if 'station_coords' in data and isinstance(data['station_coords'], list):
                data['station_coords'] = np.array(data['station_coords'])
            # Convert other arrays if needed
            if 'stop_names' in data and isinstance(data['stop_names'], list):
                data['stop_names'] = np.array(data['stop_names'])
            if 'stop_ids' in data and isinstance(data['stop_ids'], list):
                data['stop_ids'] = np.array(data['stop_ids'])
            if 'parent_stations' in data and isinstance(data['parent_stations'], list):
                data['parent_stations'] = np.array(data['parent_stations'])
        
        # Convert route lists back to sets for stop_to_routes
        if 'stop_to_routes' in data:
            stop_to_routes = {}
            for stop_id, routes in data['stop_to_routes'].items():
                stop_to_routes[stop_id] = set(routes) if isinstance(routes, list) else routes
            data['stop_to_routes'] = stop_to_routes
        
        # Verify it has the expected structure
        required_keys = ['station_coords', 'stop_names', 'stop_ids', 'stop_to_routes', 
                       'route_id_to_name', 'parent_stations']
        if not isinstance(data, dict) or not all(key in data for key in required_keys):
            print(f"GTFS JSON file doesn't have expected structure: {json_path}")
            return None
        
        # Cache the loaded data
        _gtfs_cache = data
        print(f"Successfully loaded GTFS data from: {json_path}")
        return _gtfs_cache
    except json.JSONDecodeError as e:
        print(f"JSON decode error (file may be corrupted): {e}")
        print(f"File path: {json_path}, File size: {os.path.getsize(json_path) if os.path.exists(json_path) else 'N/A'} bytes")
        return None
    except Exception as e:
        print(f"Error loading GTFS JSON file: {type(e).__name__}: {e}")
        print(f"File path: {json_path}")
        import traceback
        traceback.print_exc()
        return None



def get_closest_subway_station(lat, lon, json_path=None):
    """
    Find the closest NYC subway station to given coordinates using precomputed GTFS data.
    
    Parameters:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        json_path: Path to gtfs_precomputed.json file (optional)
    
    Returns:
        dict: {
            'station': str,  # Station name
            'distance_m': float,  # Distance in meters
            'lines': list  # List of route names (e.g., ['1', '2', '3'])
        } or None if GTFS data not available
    """
    if not lat or not lon:
        return None
    
    gtfs_data = _load_gtfs_data(json_path)
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
        'lines': ','.join([line.lower() for line in lines if 'X' not in line])
    }





def build_google_maps_link_nearby(cafe_name, lat, lon, radius=350):
    
    if not gmaps_api_key:
        raise ValueError("Google Maps API key is not set")
    gmaps = googlemaps.Client(key=gmaps_api_key)
    # Query Google Places
    geocode_result = gmaps.places_nearby(
        keyword=cafe_name, 
        location=(lat, lon), 
        radius=radius,  # use a slightly larger radius to make sure the place is included
    )
    
    relevant_types = ['cafe', 'bakery', 'food']
    relevant_results = [
        result for result in geocode_result['results']
        if any(t in relevant_types for t in result.get('types', []))
    ]
    closest_place = relevant_results[0]
    place_id = closest_place['place_id']
    place_types = closest_place['types']
    if 'bakery' in place_types:
        place_type = 'bakery'
    else:
        place_type = 'cafe'
    maps_link = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    
    return maps_link, place_type