# Import existing auth resources into Terraform

Use this to adopt your current **uploadAuth** Lambda and HTTP API so Terraform manages them instead of creating new ones.

**Prerequisites**

- Auth Lambda is a **container image** in ECR. The module creates the ECR repository; build and push with `./scripts/docker_push_lambda_auth.sh <tag>`, then apply with the same `auth_lambda_image_tag`.
- For a **first-time** apply you may need a short sequence: apply (or target) ECR → push image → apply Lambda + API.
- All commands below are run from the `terraform/` directory.

## 0. ECR (if the repo already exists in AWS)

Repository name defaults to `{project_name}-auth-lambda` (e.g. `cafehop-auth-lambda`).

```bash
cd terraform
terraform import 'module.auth.aws_ecr_repository.auth' cafehop-auth-lambda
terraform import 'module.auth.aws_ecr_repository_policy.auth' cafehop-auth-lambda
```

If Terraform created the repo first, skip import and only push the image.

## 1. Get IDs from AWS

- **API ID** — HTTP API → Overview (e.g. `abc123xyz`)
- **Integration ID** — API → Integrations → Lambda integration
- **Route IDs** — API → Routes → `POST /get-token`
- **Lambda** — name is usually `uploadAuth`
- **IAM role** — Lambda → Configuration → Permissions → Role name

CLI:

```bash
API_ID=your-api-id-here
aws apigatewayv2 get-integrations --api-id "$API_ID"
aws apigatewayv2 get-routes --api-id "$API_ID"
```

## 2. Run imports

Replace placeholders with your role name, API ID, integration ID, and route ID.

```bash
cd terraform

terraform import 'module.auth.aws_iam_role.auth' YOUR_AUTH_ROLE_NAME

terraform import 'module.auth.aws_iam_role_policy_attachment.auth_basic' YOUR_AUTH_ROLE_NAME/arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

terraform import 'module.auth.aws_lambda_function.auth' uploadAuth

terraform import 'module.auth.aws_apigatewayv2_api.auth' YOUR_API_ID

terraform import 'module.auth.aws_apigatewayv2_integration.auth' YOUR_API_ID/YOUR_INTEGRATION_ID

terraform import 'module.auth.aws_apigatewayv2_route.get_token' YOUR_API_ID/YOUR_ROUTE_ID

terraform import 'module.auth.aws_apigatewayv2_stage.auth' YOUR_API_ID/\$default

terraform import 'module.auth.aws_lambda_permission.auth_api' uploadAuth/AllowAPIGatewayInvoke
```

If the live Lambda is still a **zip** deployment, `terraform plan` will show a large change until you migrate to the container image (push to ECR and align `package_type` / `image_uri` in config) or adjust Terraform to match reality.

## 3. Plan and apply

```bash
terraform plan
```

Resolve any mismatches (role name, API name, CORS, image tag). Then:

```bash
terraform apply
```

After this, Terraform owns the existing API and Lambda; the API URL stays the same if imports matched your live resources.
