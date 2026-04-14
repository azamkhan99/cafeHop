output "auth_api_url" {
  description = "Base URL for the auth HTTP API (POST /get-token)"
  value       = trim(aws_apigatewayv2_stage.auth.invoke_url, "/")
}

output "auth_lambda_name" {
  description = "Name of the auth Lambda function (uploadAuth)"
  value       = aws_lambda_function.auth.function_name
}

output "auth_ecr_repository_url" {
  description = "ECR repository URL for auth Lambda images (docker push target)"
  value       = aws_ecr_repository.auth.repository_url
}
