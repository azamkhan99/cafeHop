module "auth" {
  source = "./auth"

  project_name           = var.project_name
  iam_role_name          = var.auth_iam_role_name
  api_name               = var.auth_api_name
  auth_lambda_image_tag  = var.auth_lambda_image_tag
  jwt_secret             = var.jwt_secret
}

# Opt-in: FastAPI cafe API — see docs/terraform-import-cafe.md
module "cafe" {
  count  = var.enable_cafe_terraform ? 1 : 0
  source = "./cafe"

  project_name             = var.project_name
  lambda_function_name     = var.cafe_lambda_function_name
  iam_role_name            = var.cafe_iam_role_name
  api_name                 = var.cafe_api_name
  cafe_lambda_image_tag    = var.cafe_lambda_image_tag
  dynamodb_table_name      = aws_dynamodb_table.cafes.name
  dynamodb_table_arn       = aws_dynamodb_table.cafes.arn
  s3_bucket_name           = var.photo_s3_bucket_name
  google_places_api_key    = var.cafe_google_places_api_key
  cors_allow_origins       = var.cafe_cors_allow_origins
  lambda_timeout           = var.cafe_lambda_timeout
  lambda_memory_size       = var.cafe_lambda_memory_size
}

# Opt-in: FastAPI image API (presigned-url, process) — see docs/terraform-import-image.md
module "image" {
  count  = var.enable_image_terraform ? 1 : 0
  source = "./image"

  project_name             = var.project_name
  lambda_function_name     = var.image_lambda_function_name
  iam_role_name            = var.image_iam_role_name
  api_name                 = var.image_api_name
  image_lambda_image_tag   = var.image_lambda_image_tag
  s3_bucket_name           = var.photo_s3_bucket_name
  cors_allow_origins       = var.image_cors_allow_origins
  lambda_timeout           = var.image_lambda_timeout
  lambda_memory_size       = var.image_lambda_memory_size
}
