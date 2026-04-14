variable "project_name" {
  type = string
}

variable "lambda_function_name" {
  description = "Lambda function name (e.g. uploadCafePhoto to replace legacy, or cafehop-cafe-api)"
  type        = string
  default     = "cafehop-cafe-api"
}

variable "iam_role_name" {
  description = "Execution role name override for imports"
  type        = string
  default     = ""
}

variable "api_name" {
  description = "HTTP API name override for imports"
  type        = string
  default     = ""
}

variable "cafe_lambda_image_tag" {
  description = "ECR image tag (scripts/docker_push_lambda_cafe.sh)"
  type        = string
  default     = "latest"
}

variable "dynamodb_table_name" {
  description = "DynamoDB cafes table name (TABLE_NAME env)"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB cafes table ARN for IAM (include indexes via /index/*)"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket for photos (BUCKET_NAME on cafe Lambda; used in POST /v1/cafes/from-upload)"
  type        = string
}

variable "google_places_api_key" {
  description = "Optional GOOGLE_PLACES_API_KEY for geocoding/enrichment"
  type        = string
  default     = ""
  sensitive   = true
}

variable "cors_allow_origins" {
  type = list(string)
}

variable "lambda_timeout" {
  type    = number
  default = 60
}

variable "lambda_memory_size" {
  type    = number
  default = 1024
}
