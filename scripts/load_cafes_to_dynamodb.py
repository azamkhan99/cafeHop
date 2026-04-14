#!/usr/bin/env python3
"""
One-time load: fetch cafes.json from S3 and write all cafes into the DynamoDB table.
Requires: boto3, table already created (terraform apply).
  pip install boto3
  AWS credentials configured (env or ~/.aws/credentials).
Usage:
  TABLE_NAME=cafehop-cafes BUCKET=azamcafelistphotos KEY=cafes.json python scripts/load_cafes_to_dynamodb.py
  Or with terraform output: TABLE_NAME=$(cd terraform && terraform output -raw cafes_table_name) BUCKET=azamcafelistphotos KEY=cafes.json python scripts/load_cafes_to_dynamodb.py
"""
import json
import os
import sys
from decimal import Decimal

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "cafehop-cafes")
BUCKET = os.environ.get("BUCKET", "azamcafelistphotos")
KEY = os.environ.get("KEY", "cafes.json")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def decimalize(obj):
    """Convert floats to Decimal for DynamoDB; leave other types intact."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: decimalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimalize(v) for v in obj]
    return obj


def main():
    s3 = boto3.client("s3", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    print(f"Fetching s3://{BUCKET}/{KEY} ...")
    resp = s3.get_object(Bucket=BUCKET, Key=KEY)
    data = json.load(resp["Body"])
    cafes = data.get("cafes", [])
    if not cafes:
        print("No 'cafes' array in JSON.")
        sys.exit(1)

    print(f"Loading {len(cafes)} cafes into {TABLE_NAME} ...")
    batch_size = 25
    for i in range(0, len(cafes), batch_size):
        batch = cafes[i : i + batch_size]
        with table.batch_writer() as writer:
            for cafe in batch:
                item = decimalize(cafe)
                writer.put_item(Item=item)
        print(f"  Wrote {min(i + batch_size, len(cafes))}/{len(cafes)}")
    print("Done.")


if __name__ == "__main__":
    main()
