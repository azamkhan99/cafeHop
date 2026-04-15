# Terraform: cafe API (FastAPI on Lambda)

Module: `terraform/cafe` — DynamoDB-backed **`GET /cafes`**, **`POST /v1/cafes/from-upload`**, etc. This **replaces** the old **`uploadCafePhoto`** monolith for café data; presigns stay on **`module.image`**.

## Enable

```bash
export TF_VAR_enable_cafe_terraform=true
export TF_VAR_photo_s3_bucket_name=your-photo-bucket
```

## New deployment

1. **ECR only** (first apply so you can push an image):

   ```bash
   cd terraform
   terraform apply \
     -target='module.cafe[0].aws_ecr_repository.cafe' \
     -target='module.cafe[0].aws_ecr_repository_policy.cafe'
   ```

2. **Build and push** (repo root):

   ```bash
   ./scripts/docker_push_lambda_cafe.sh v1
   ```

3. **Full apply:**

   ```bash
   cd terraform
   terraform apply -var='cafe_lambda_image_tag=v1'
   ```

4. Set **`web/api-config.js`** **`cafeUrl`** to the Terraform output **`cafe_api_url`** (no trailing slash).

## Lambda name vs legacy `uploadCafePhoto`

Default function name is **`cafehop-cafe-api`**. To reuse the name **`uploadCafePhoto`**, **delete** the old Lambda in AWS first (or remove it from any old Terraform state), then:

```bash
terraform apply -var='cafe_lambda_function_name=uploadCafePhoto'
```

## Optional

- **`TF_VAR_cafe_google_places_api_key`** — geocoding / enrichment in `services/cafe`.
- **`cafe_cors_allow_origins`** — if your Pages origin differs from the defaults.

## Import (existing API + Lambda)

Same pattern as `docs/terraform-import-image.md`: import ECR, IAM, Lambda, HTTP API, **`$default`** route, integration, stage, Lambda permission. Use your API ID and route ID for **`$default`**.
