output "cafe_api_url" {
  description = "Base URL for the cafe HTTP API (e.g. GET /cafes, POST /v1/cafes/from-upload)"
  value       = trim(aws_apigatewayv2_stage.cafe.invoke_url, "/")
}

output "cafe_lambda_name" {
  value = aws_lambda_function.cafe.function_name
}

output "cafe_ecr_repository_url" {
  value = aws_ecr_repository.cafe.repository_url
}

output "cafe_api_id" {
  value = aws_apigatewayv2_api.cafe.id
}

output "cafe_role_name" {
  value = aws_iam_role.cafe.name
}
