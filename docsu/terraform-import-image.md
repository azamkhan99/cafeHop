# Terraform: image microservice (new or import)

Module: `terraform/image` — Lambda (container) + HTTP API v2 with a **`$default`** route (same idea as `module.cafe`): all paths hit FastAPI, including `POST /presigned-url`, `POST /process`, `GET /`, and `/docs`. `add.html` uses `CafeHopConfig.imageUrl` as the **API base URL** (no path); it appends `/presigned-url` and `/process`.

## New deployment (no existing Lambda)

Use this when you are creating the image API for the first time.

**1. Turn the module on** (from `terraform/`), using your real bucket name:

```bash
export TF_VAR_enable_image_terraform=true
export TF_VAR_photo_s3_bucket_name=azamcafelistphotos   # or your bucket
```

**2. Create the ECR repo only** (so you have somewhere to push; the Lambda image must exist before AWS will accept the function):

```bash
cd terraform

terraform apply \
  -target='module.image[0].aws_ecr_repository.image' \
  -target='module.image[0].aws_ecr_repository_policy.image'
```

**3. Build and push** the image (repo root). Use the same tag you will pass to Terraform:

```bash
cd ..
./scripts/docker_push_lambda_image.sh v1
```

**4. Apply everything** (IAM, Lambda, API, routes):

```bash
cd terraform
terraform apply -var='image_lambda_image_tag=v1'
```

**5. Point the static site at the new API** — copy the Terraform output `image_api_url` into `web/api-config.js` as `imageUrl` (no trailing slash).

Optional: pick any unused function name with `-var='image_lambda_function_name=my-image-api'`. The default is `cafehop-image-api`.

---

## Optional: import existing API + Lambda

Skip this section if you followed the steps above and Terraform already created the resources.

If something already exists in AWS with the **same names** Terraform expects, use imports and align `image_lambda_function_name`, `image_iam_role_name`, and `image_api_name` with the console. Gather API ID, integration ID, the **`$default`** route ID (or recreate routes to match Terraform), Lambda name, and IAM role name.

```bash
cd terraform

terraform import 'module.image[0].aws_ecr_repository.image' cafehop-image-lambda
terraform import 'module.image[0].aws_ecr_repository_policy.image' cafehop-image-lambda

terraform import 'module.image[0].aws_iam_role.image' YOUR_IMAGE_ROLE_NAME
terraform import 'module.image[0].aws_iam_role_policy_attachment.image_basic' YOUR_IMAGE_ROLE_NAME/arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
terraform import 'module.image[0].aws_iam_role_policy.image_s3' YOUR_IMAGE_ROLE_NAME:cafehop-image-lambda-s3

terraform import 'module.image[0].aws_lambda_function.image' YOUR_LAMBDA_NAME

terraform import 'module.image[0].aws_apigatewayv2_api.image' YOUR_API_ID
terraform import 'module.image[0].aws_apigatewayv2_integration.image' YOUR_API_ID/YOUR_INTEGRATION_ID
terraform import 'module.image[0].aws_apigatewayv2_route.default' YOUR_API_ID/YOUR_DEFAULT_ROUTE_ID

terraform import 'module.image[0].aws_apigatewayv2_stage.image' YOUR_API_ID/\$default

terraform import 'module.image[0].aws_lambda_permission.image_api' YOUR_LAMBDA_NAME/AllowAPIGatewayInvoke
```

Then `terraform plan` and fix any drift before `terraform apply`.
