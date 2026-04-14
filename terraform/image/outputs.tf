output "image_api_url" {
  description = "Base URL for the image HTTP API (POST /presigned-url, POST /process)"
  value       = trim(aws_apigatewayv2_stage.image.invoke_url, "/")
}

output "image_lambda_name" {
  value = aws_lambda_function.image.function_name
}

output "image_ecr_repository_url" {
  value = aws_ecr_repository.image.repository_url
}

output "image_api_id" {
  value = aws_apigatewayv2_api.image.id
}

output "image_role_name" {
  value = aws_iam_role.image.name
}
