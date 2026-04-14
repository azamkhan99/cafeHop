output "auth_api_url" {
  description = "Base URL for the auth HTTP API (POST /get-token)"
  value       = module.auth.auth_api_url
}

output "auth_lambda_name" {
  description = "Name of the auth Lambda function (uploadAuth)"
  value       = module.auth.auth_lambda_name
}

output "auth_ecr_repository_url" {
  description = "ECR repository URL for auth Lambda container images"
  value       = module.auth.auth_ecr_repository_url
}

output "cafe_api_url" {
  description = "Base URL for cafe HTTP API when module.cafe is enabled"
  value       = length(module.cafe) > 0 ? module.cafe[0].cafe_api_url : null
}

output "cafe_lambda_name" {
  description = "Cafe Lambda function name when module.cafe is enabled"
  value       = length(module.cafe) > 0 ? module.cafe[0].cafe_lambda_name : null
}

output "cafe_ecr_repository_url" {
  description = "ECR URL for cafe Lambda when module.cafe is enabled"
  value       = length(module.cafe) > 0 ? module.cafe[0].cafe_ecr_repository_url : null
}

output "image_api_url" {
  description = "Base URL for image HTTP API when module.image is enabled (append /presigned-url or /process)"
  value       = length(module.image) > 0 ? module.image[0].image_api_url : null
}

output "image_lambda_name" {
  description = "Image Lambda function name when module.image is enabled"
  value       = length(module.image) > 0 ? module.image[0].image_lambda_name : null
}

output "image_ecr_repository_url" {
  description = "ECR URL for image Lambda when module.image is enabled"
  value       = length(module.image) > 0 ? module.image[0].image_ecr_repository_url : null
}
