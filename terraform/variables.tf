variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "cafehop"
}

# Auth (uploadAuth) Lambda and HTTP API
variable "auth_iam_role_name" {
  description = "Existing IAM role name when importing auth (e.g. uploadAuth-role-xsoy3fe5); leave empty for new deployments"
  type        = string
  default     = ""
}

variable "auth_api_name" {
  description = "Existing HTTP API name when importing auth (e.g. cafeUploadAuth); leave empty for project_name-auth-api"
  type        = string
  default     = ""
}

variable "auth_lambda_image_tag" {
  description = "ECR image tag for auth Lambda (push with scripts/docker_push_lambda_auth.sh before first apply)"
  type        = string
  default     = "latest"
}

variable "jwt_secret" {
  description = "Secret used to sign JWTs (set via TF_VAR_jwt_secret or terraform.tfvars, do not commit)"
  type        = string
  default     = "supersecret"
  sensitive   = true
}

# --- Photo bucket (BUCKET_NAME on image + cafe Lambdas) ---
variable "photo_s3_bucket_name" {
  description = "S3 bucket for cafe photos (maps to BUCKET_NAME on Lambdas)"
  type        = string
  default     = "azamcafelistphotos"
}

# --- Cafe FastAPI Lambda + HTTP API (optional module; replaces legacy uploadCafePhoto) ---
variable "enable_cafe_terraform" {
  description = "When true, create/manage module.cafe (ECR + IAM + Lambda + HTTP API for /cafes, /v1/cafes/from-upload, …)."
  type        = bool
  default     = false
}

variable "cafe_lambda_function_name" {
  description = "Lambda function name (use cafehop-cafe-api for a new function, or uploadCafePhoto only after deleting the legacy Lambda in AWS)"
  type        = string
  default     = "cafehop-cafe-api"
}

variable "cafe_iam_role_name" {
  description = "Existing IAM role name when importing cafe module; leave empty for default"
  type        = string
  default     = ""
}

variable "cafe_api_name" {
  description = "Existing HTTP API name when importing; leave empty for default project-prefixed name"
  type        = string
  default     = ""
}

variable "cafe_lambda_image_tag" {
  description = "ECR image tag for cafe Lambda (scripts/docker_push_lambda_cafe.sh)"
  type        = string
  default     = "latest"
}

variable "cafe_google_places_api_key" {
  description = "Optional GOOGLE_PLACES_API_KEY for services/cafe geocoding"
  type        = string
  default     = ""
  sensitive   = true
}

variable "cafe_cors_allow_origins" {
  description = "CORS allow_origins for the cafe HTTP API"
  type        = list(string)
  default = [
    "https://azamkhan99.github.io",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
  ]
}

variable "cafe_lambda_timeout" {
  type    = number
  default = 60
}

variable "cafe_lambda_memory_size" {
  type    = number
  default = 1024
}

# --- Image microservice Lambda + HTTP API (optional module) ---
variable "enable_image_terraform" {
  description = "When true, create/manage module.image (ECR + IAM + Lambda + HTTP API for /presigned-url and /process)."
  type        = bool
  default     = false
}

variable "image_lambda_function_name" {
  description = "Lambda function name Terraform will create for the image API (change only if that name is already taken or you are importing a different name)"
  type        = string
  default     = "cafehop-image-api"
}

variable "image_iam_role_name" {
  description = "Existing IAM role name when importing image module; leave empty for default"
  type        = string
  default     = ""
}

variable "image_api_name" {
  description = "Existing HTTP API name when importing; leave empty for the default project-prefixed API name"
  type        = string
  default     = ""
}

variable "image_lambda_image_tag" {
  description = "ECR image tag for image Lambda (scripts/docker_push_lambda_image.sh)"
  type        = string
  default     = "latest"
}

variable "image_cors_allow_origins" {
  description = "CORS allow_origins for the image HTTP API"
  type        = list(string)
  default = [
    "https://azamkhan99.github.io",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
  ]
}

variable "image_lambda_timeout" {
  type    = number
  default = 60
}

variable "image_lambda_memory_size" {
  type    = number
  default = 512
}
