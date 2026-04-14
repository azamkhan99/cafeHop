#!/usr/bin/env bash
# Build the auth Lambda container from repo root and push to ECR.
# Prerequisites: aws CLI, docker, ECR repo already exists (terraform apply targeting ECR first), docker login to ECR.
#
# Usage:
#   export AWS_REGION=us-east-1   # optional, default us-east-1
#   export AWS_ACCOUNT_ID=123456789012
#   export ECR_REPO=cafehop-auth-lambda   # optional, default cafehop-auth-lambda
#   ./scripts/docker_push_lambda_auth.sh [tag]
#
# Example:
#   ./scripts/docker_push_lambda_auth.sh v20250412-1
# Then: terraform apply -var="auth_lambda_image_tag=v20250412-1"
set -euo pipefail

TAG="${1:-latest}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT="${AWS_ACCOUNT_ID:-}"
REPO_NAME="${ECR_REPO:-cafehop-auth-lambda}"

if [[ -z "$ACCOUNT" ]]; then
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
fi

REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_URI="${REGISTRY}/${REPO_NAME}:${TAG}"

cd "$REPO_ROOT"

echo "Building $IMAGE_URI (linux/amd64 for Lambda x86_64)..."
docker build --platform linux/amd64 -f services/auth/Dockerfile -t "$IMAGE_URI" .

echo "Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "Pushing $IMAGE_URI ..."
docker push "$IMAGE_URI"

echo "Done. Set Terraform: -var=\"auth_lambda_image_tag=${TAG}\" (or terraform.tfvars) and apply."
