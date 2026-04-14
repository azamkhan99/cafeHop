#!/usr/bin/env bash
# Build and push the image microservice Lambda container (services/image/Dockerfile.lambda).
#
# Usage:
#   export AWS_REGION=us-east-1
#   export AWS_ACCOUNT_ID=123456789012
#   export ECR_REPO=cafehop-image-lambda
#   ./scripts/docker_push_lambda_image.sh [tag]
#
# Then enable module.image and apply with -var="image_lambda_image_tag=<tag>".
set -euo pipefail

TAG="${1:-latest}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT="${AWS_ACCOUNT_ID:-}"
PROJECT="${CAFEHOP_PROJECT_NAME:-cafehop}"
REPO_NAME="${ECR_REPO:-${PROJECT}-image-lambda}"

if [[ -z "$ACCOUNT" ]]; then
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
fi

REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_URI="${REGISTRY}/${REPO_NAME}:${TAG}"

cd "$REPO_ROOT"

echo "Building $IMAGE_URI (linux/amd64)..."
docker build --platform linux/amd64 -f services/image/Dockerfile.lambda -t "$IMAGE_URI" .

echo "Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "Pushing $IMAGE_URI ..."
docker push "$IMAGE_URI"

echo "Done. Enable Terraform: -var='enable_image_terraform=true' -var='image_lambda_image_tag=${TAG}'"
