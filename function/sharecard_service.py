import re
from jinja2 import Environment, FileSystemLoader
import cairosvg
from datetime import date
import base64
from pathlib import Path
import io
import requests
from PIL import Image
import json
import boto3

def font_file_to_data_uri(ttf_path: str) -> str:
    b = Path(ttf_path).read_bytes()
    b64 = base64.b64encode(b).decode("utf-8")
    return f"data:font/ttf;base64,{b64}"

def image_url_to_data_uri(url: str) -> str:
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    # Convert whatever it is (jpeg/webp/etc.) into PNG
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    b64 = base64.b64encode(out.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def shorten_intersection(text):
    # Split on &
    m = re.match(r'^\s*([^&]+?)\s*&\s*(.+?)\s*$', text)
    if not m:
        return text  # fail-safe

    s1, s2 = m.group(1), m.group(2)

    # Normalize directions
    dir_map = {
        r'\bEast\b': 'E',
        r'\bWest\b': 'W',
        r'\bNorth\b': 'N',
        r'\bSouth\b': 'S'
    }
    for pat, repl in dir_map.items():
        s1 = re.sub(pat, repl, s1, flags=re.IGNORECASE)
        s2 = re.sub(pat, repl, s2, flags=re.IGNORECASE)

    # Remove street-type suffixes
    suffixes = r'\b(St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Pl|Place|Ln|Lane|Dr|Drive)\b'
    s1 = re.sub(suffixes, '', s1, flags=re.IGNORECASE)
    s2 = re.sub(suffixes, '', s2, flags=re.IGNORECASE)

    # Cleanup extra spaces
    s1 = re.sub(r'\s+', ' ', s1).strip()
    s2 = re.sub(r'\s+', ' ', s2).strip()

    return f"{s1} & {s2}"



def generate_receipt_card(data,s3_image_url, template, width, height):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template)

    image_href = image_url_to_data_uri(s3_image_url)
    citibike_station = data['closest_citibike_station_name']
    shortened_citibike_station = shorten_intersection(citibike_station).replace("&", "&amp;")
    

    gmaps_place_id = data['google_maps_link'].split("place_id:")[-1]
    shortened_gmaps_link = f"https://maps.google.com/?q=place_id:{gmaps_place_id}"

    svg = template.render(
        name=data['cafe-name'],
        neighborhood=data["neighborhood"],
        rating=data["elo_star_rating"],
        subway_lines=data["closest_subway_lines"].split(","),
        citibike_station = shortened_citibike_station,
        cafe_photo_href=image_href,
        date=date.today().strftime("%B %d, %Y"),
        gmaps_link = shortened_gmaps_link
    )

    try:
        print("PHOTO HREF PREVIEW:", image_href[:80])
        png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                                    output_width=width, output_height=height, unsafe=True)
    except Exception as e:
        print("Error during SVG to PNG conversion:")
        raise

    return png_bytes

"""
lambda should run when a new file is uploaded to S3 bucket.
The key of the file should be the cafe key in cafes.json.
Use the metadata of the file to generate the share card, store the share card in the same S3 bucket with key "receipt_cards/{cafe_key}.png" and update cafes.json with the share card url
cafes.json is a list of dicts which has a key field as well as the data fields
"""

def lambda_handler(event, context):
    s3 = boto3.client('s3')

    # Get the bucket name and object key from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    # Get the object's metadata
    response = s3.head_object(Bucket=bucket_name, Key=object_key)
    metadata = response['Metadata']

    cafe_key = object_key.split('.')[0]  # assuming the key is the filename without extension
    s3_image_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
    # Generate the share card
    share_card_png = generate_receipt_card(metadata,s3_image_url, "receipt_card.svg", 1080, 1350)

    # Store the share card in S3
    share_card_key = f"receipt_cards/{cafe_key}.png"
    s3.put_object(
        Bucket=bucket_name,
        Key=share_card_key,
        Body=share_card_png,
        ContentType='image/png'
    )

    share_card_url = f"https://{bucket_name}.s3.amazonaws.com/{share_card_key}"

    # Update cafes.json file in the same bucket
    cafes_object_key = 'cafes.json'
    cafes_response = s3.get_object(Bucket=bucket_name, Key=cafes_object_key)
    cafes_data = json.loads(cafes_response['Body'].read().decode('utf-8'))

    for cafe in cafes_data:
        if cafe['key'] == cafe_key:
            cafe['shareCardPngUrl'] = share_card_url
            break

    # Write the updated cafes data back to cafes.json
    s3.put_object(
        Bucket=bucket_name,
        Key=cafes_object_key,
        Body=json.dumps(cafes_data),
        ContentType='application/json'
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Share card generated and cafes.json updated successfully!')
    }
