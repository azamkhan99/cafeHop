variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "iam_role_name" {
  description = "Override IAM role name (set when importing existing role, e.g. uploadAuth-role-xxx)"
  type        = string
  default     = ""
}

variable "api_name" {
  description = "Override HTTP API name (set when importing existing API, e.g. cafeUploadAuth); leave empty for project_name-auth-api"
  type        = string
  default     = ""
}

variable "auth_lambda_image_tag" {
  description = "ECR image tag for the auth Lambda container (must exist in ECR before apply; build with scripts/docker_push_lambda_auth.sh)"
  type        = string
  default     = "latest"
}

variable "jwt_secret" {
  description = "Secret used to sign JWTs"
  type        = string
  sensitive   = true
}
