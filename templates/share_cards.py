# %%
import json

# %%
with open('/Users/ahmedkhan/Desktop/cafeHop/station_information.json', 'r') as f:
    data = json.load(f)

# %%
data['data']['stations']

# %%
rel_data = []
for station in data['data']['stations']:
    rel_data.append({
        'station_id': station['station_id'],
        'name': station['name'],
        'lat': station['lat'],
        'lon': station['lon']
    })

# %%
json.dump(rel_data, open('/Users/ahmedkhan/Desktop/cafeHop/station_information_rel.json', 'w'), indent=4)

# %%
import math
import numpy

# %%
# function to calculate distance between a lat/long and closest station using numpy (vectorized)
EARTH_RADIUS_M = 6371000  # in meters
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

def get_closest_citibike_station(lat, lon, json_path=None):

    if json_path is None:
        json_path = '/Users/ahmedkhan/Desktop/cafeHop/station_information_rel.json'
    
    stations = json.load(open(json_path, 'r'))
    
    station_lats = numpy.array([station['lat'] for station in stations])
    station_lons = numpy.array([station['lon'] for station in stations])
    
    # Vectorized calculation of distances
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    station_lats_rad = numpy.radians(station_lats)
    station_lons_rad = numpy.radians(station_lons)
    
    dlat = station_lats_rad - lat_rad
    dlon = station_lons_rad - lon_rad
    
    a = numpy.sin(dlat / 2)**2 + numpy.cos(lat_rad) * numpy.cos(station_lats_rad) * numpy.sin(dlon / 2)**2
    c = 2 * numpy.arcsin(numpy.sqrt(a))
    
    distances = EARTH_RADIUS_M * c
    
    closest_index = numpy.argmin(distances)
    closest_station = stations[closest_index]

    closest_station_distance = distances[closest_index]
    walking_speed_m_per_min = 80  # average walking speed in meters per minute
    mins_walk = closest_station_distance / walking_speed_m_per_min
    
    return {
        'station_id': closest_station['station_id'],
        'name': closest_station['name'],
        'lat': closest_station['lat'],
        'lon': closest_station['lon'],
        'distance_m': float(distances[closest_index]),
        'mins_walk': int(numpy.ceil(mins_walk))
    }



# %%
get_closest_station(40.748817, -73.985428)

# %%
!pip install cairosvg jinja2

# %%
from jinja2 import Environment, FileSystemLoader
import cairosvg
from datetime import date


def generate_receipt_card(data, template, width, height):
    env = Environment(loader=FileSystemLoader("/Users/ahmedkhan/Desktop/cafeHop/templates"))
    template = env.get_template(template)

    image_href = image_url_to_data_uri(data["image_url"])

    # stars = get_stars(data["rating"])

    svg = template.render(
        name=data["name"],
        neighborhood=data["neighborhood"],
        rating=data["rating"],
        subway=data["subway"],
        walk_minutes=data["walk_minutes"],
        cafe_photo_href=image_href,
        date=date.today().strftime("%B %d, %Y"),
        gmaps_link = data['gmaps_link']
    )

    try:
        print("PHOTO HREF PREVIEW:", image_href[:80])
        png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                                    output_width=width, output_height=height, unsafe=True)
    except Exception as e:
        with open("/Users/ahmedkhan/Desktop/cafeHop/_debug_rendered.svg", "w", encoding="utf-8") as f:
            f.write(svg)
        raise


    return png_bytes


# %%
import base64
from pathlib import Path

def font_file_to_data_uri(ttf_path: str) -> str:
    b = Path(ttf_path).read_bytes()
    b64 = base64.b64encode(b).decode("utf-8")
    return f"data:font/ttf;base64,{b64}"


# %%
import base64
import io
import requests
from PIL import Image  # pip install pillow

def image_url_to_data_uri(url: str) -> str:
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    # Convert whatever it is (jpeg/webp/etc.) into PNG
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    b64 = base64.b64encode(out.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

# %%
watchhouse = {
    'name': 'WatchHouse',
    'rating': 3.5,
    'neighborhood': 'Midtown',
    'subway': 'E',
    'location_type': 'cafe',
    'walk_minutes': '3',
    'gmaps_link': 'https://www.google.com/maps/place/?q=place_id:ChIJJZFonGRZwokRUlJQynzhi1c',
    'image_url': 'https://lh3.googleusercontent.com/p/AF1QipNjMyT2wj864CnEOa_Xk6arX-inkgrLRjBstE3G=w203-h270-k-no',
}

# %%
# read png bytes as png
with open('/Users/ahmedkhan/Desktop/cafeHop/watchhouse_receipt.png', 'wb') as f:
    f.write(generate_receipt_card(watchhouse, 'receipt_card2.svg'))

# %%
# read png bytes as png
with open('/Users/ahmedkhan/Desktop/cafeHop/watchhouse_receipt_story.png', 'wb') as f:
    f.write(generate_receipt_card(watchhouse, 'receipt_card_story.svg', 1080, 1920))


