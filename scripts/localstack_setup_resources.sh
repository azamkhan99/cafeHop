#!/usr/bin/env bash
# Create S3 bucket + DynamoDB table in LocalStack (idempotent).
# Used by docker compose (init-aws). Can also run on the host after LocalStack is up.
# Optional: set -a && source localstack/.env && set +a (see localstack.env.example).
set -euo pipefail
ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

BUCKET="${BUCKET_NAME:-cafehop-local-photos}"
TABLE="${TABLE_NAME:-cafehop-cafes}"

AWS=(aws --endpoint-url="$ENDPOINT")

echo "Using endpoint $ENDPOINT bucket=$BUCKET table=$TABLE"

if ! "${AWS[@]}" s3 ls "s3://$BUCKET" 2>/dev/null; then
  "${AWS[@]}" s3 mb "s3://$BUCKET"
  echo "Created bucket s3://$BUCKET"
else
  echo "Bucket s3://$BUCKET already exists"
fi

# Browser uploads use presigned PUT from add.html; S3 must allow the page origin.
"${AWS[@]}" s3api put-bucket-cors --bucket "$BUCKET" --cors-configuration '{
  "CORSRules": [{
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"]
  }]
}'

# index.html / map.html fetch bucket/cafes.json; avoid 404 + broken gallery until first publish.
if ! "${AWS[@]}" s3api head-object --bucket "$BUCKET" --key cafes.json &>/dev/null; then
  printf '%s\n' '{"cafes":[]}' | "${AWS[@]}" s3 cp - "s3://${BUCKET}/cafes.json" --content-type application/json
  echo "Seeded s3://${BUCKET}/cafes.json (empty list)"
fi

if "${AWS[@]}" dynamodb describe-table --table-name "$TABLE" &>/dev/null; then
  echo "DynamoDB table $TABLE already exists"
else
  # Minimal table for local dev (hash key only; scans work without production GSI).
  "${AWS[@]}" dynamodb create-table \
    --table-name "$TABLE" \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=key,AttributeType=S \
    --key-schema AttributeName=key,KeyType=HASH \
    >/dev/null
  echo "Created DynamoDB table $TABLE"
fi
