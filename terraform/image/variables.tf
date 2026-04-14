variable "project_name" {
  type = string
}

variable "lambda_function_name" {
  description = "Lambda function name (import existing or create new)"
  type        = string
  default     = "cafehop-image-api"
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

variable "image_lambda_image_tag" {
  description = "ECR image tag (push with scripts/docker_push_lambda_image.sh)"
  type        = string
  default     = "latest"
}

variable "s3_bucket_name" {
  description = "S3 bucket for uploads (BUCKET_NAME)"
  type        = string
}

variable "cors_allow_origins" {
  description = "Allowed origins for HTTP API CORS (browser clients)"
  type        = list(string)
  default = [
    "https://azamkhan99.github.io",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
  ]
}

variable "lambda_timeout" {
  type    = number
  default = 60
}

variable "lambda_memory_size" {
  type    = number
  default = 512
}
