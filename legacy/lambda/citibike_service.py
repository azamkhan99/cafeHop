import json
import boto3
from utils import get_closest_citibike_station

"""
AWS Lambda function that given an image is uploaded to s3 bucket, it will find the closest Citibike station using the s3 object's metadata
(latitude and longitude) and update the object's metadata with the closest station information. 
Then updates cafes.json file in the same s3 bucket with the closest station information for the cafe we just updated.
"""

def lambda_handler(event, context):
    s3 = boto3.client('s3')

    # Get the bucket name and object key from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    # Get the object's metadata
    response = s3.head_object(Bucket=bucket_name, Key=object_key)
    metadata = response['Metadata']

    latitude = float(metadata['latitude'])
    longitude = float(metadata['longitude'])

    # Find the closest Citibike station
    closest_station = get_closest_citibike_station(latitude, longitude)

    # Update the object's metadata with the closest station information
    new_metadata = metadata.copy()
    new_metadata['closest_citibike_station_name'] = closest_station['name']
    new_metadata['closest_citibike_station_mins_walk'] = str(closest_station['mins_walk'])

    s3.copy_object(
        Bucket=bucket_name,
        CopySource={'Bucket': bucket_name, 'Key': object_key},
        Key=object_key,
        Metadata=new_metadata,
        MetadataDirective='REPLACE'
    )

    # Update cafes.json file in the same bucket
    cafes_object_key = 'cafes.json'
    cafes_response = s3.get_object(Bucket=bucket_name, Key=cafes_object_key)
    cafes_data = json.loads(cafes_response['Body'].read().decode('utf-8'))

    # Assuming the cafe can be identified by the object key (e.g., image filename)
    cafe_id = object_key.split('.')[0]  # Example: if object_key is 'cafe1.jpg', cafe_id is 'cafe1'

    for cafe in cafes_data:
        if cafe['id'] == cafe_id:
            cafe['closest_citibike_station_name'] = closest_station['name']
            cafe['closest_station_mins_walk'] = str(closest_station['mins_walk'])
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
        'body': json.dumps('Citibike station information updated successfully!')
    }