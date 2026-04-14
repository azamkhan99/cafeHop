#!/usr/bin/env bash
# Build and push the cafe API Lambda container (services/cafe/Dockerfile.lambda).
#
# Usage:
#   export AWS_REGION=us-east-1
#   export AWS_ACCOUNT_ID=123456789012
#   export ECR_REPO=cafehop-cafe-lambda
#   ./scripts/docker_push_lambda_cafe.sh [tag]
#
# Then: terraform apply -var='enable_cafe_terraform=true' -var='cafe_lambda_image_tag=<tag>'
set -euo pipefail

TAG="${1:-latest}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT="${AWS_ACCOUNT_ID:-}"
PROJECT="${CAFEHOP_PROJECT_NAME:-cafehop}"
REPO_NAME="${ECR_REPO:-${PROJECT}-cafe-lambda}"

if [[ -z "$ACCOUNT" ]]; then
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
fi

REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_URI="${REGISTRY}/${REPO_NAME}:${TAG}"

cd "$REPO_ROOT"

echo "Building $IMAGE_URI (linux/amd64)..."
docker build --platform linux/amd64 -f services/cafe/Dockerfile.lambda -t "$IMAGE_URI" .

echo "Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "Pushing $IMAGE_URI ..."
docker push "$IMAGE_URI"

echo "Done. Apply with: -var='enable_cafe_terraform=true' -var='cafe_lambda_image_tag=${TAG}'"
