#!/usr/bin/env bash
# Build and push both Lambda container images (cafe API + image microservice).
#
# Usage:
#   export AWS_REGION=us-east-1
#   ./scripts/docker_push_lambda_cafe_and_image.sh [tag]
#
# Default tag: latest
# Then terraform apply with matching cafe_lambda_image_tag and image_lambda_image_tag.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"

echo "=== Pushing cafe + image Lambdas with tag: ${TAG} ==="
"${REPO_ROOT}/scripts/docker_push_lambda_cafe.sh" "${TAG}"
"${REPO_ROOT}/scripts/docker_push_lambda_image.sh" "${TAG}"

echo ""
echo "=== Both images pushed. Apply Terraform (example): ==="
echo "  cd terraform && terraform apply \\"
echo "    -var='enable_cafe_terraform=true' \\"
echo "    -var='enable_image_terraform=true' \\"
echo "    -var='cafe_lambda_image_tag=${TAG}' \\"
echo "    -var='image_lambda_image_tag=${TAG}'"
