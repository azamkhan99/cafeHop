#!/usr/bin/env bash
# Build/push cafe + image Lambda images, then terraform apply so AWS runs the new digests.
#
# Usage (from repo root or any cwd):
#   export AWS_REGION=us-east-1
#   ./scripts/deploy_cafe_and_image_lambdas.sh [tag]
#
# Default tag: latest
# Set TF_VAR_* / use terraform.tfvars for photo bucket, Places key, etc. (unchanged by this script).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"

"${REPO_ROOT}/scripts/docker_push_lambda_cafe_and_image.sh" "${TAG}"

cd "${REPO_ROOT}/terraform"
terraform apply -auto-approve \
  -var="enable_cafe_terraform=true" \
  -var="enable_image_terraform=true" \
  -var="cafe_lambda_image_tag=${TAG}" \
  -var="image_lambda_image_tag=${TAG}"

echo "=== Deploy finished (tag=${TAG}) ==="
