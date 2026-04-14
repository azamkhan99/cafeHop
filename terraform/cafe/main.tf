# Cafe HTTP API (FastAPI + Mangum): DynamoDB cafes, /v1/cafes/from-upload, etc.
# HTTP API uses $default route so all paths proxy to the Lambda.
# Build: services/cafe/Dockerfile.lambda — push: scripts/docker_push_lambda_cafe.sh

data "aws_caller_identity" "current" {}

locals {
  cafe_image_uri = "${aws_ecr_repository.cafe.repository_url}:${var.cafe_lambda_image_tag}"
  iam_name       = var.iam_role_name != "" ? var.iam_role_name : "${var.project_name}-cafe-lambda-role"
  api_name       = var.api_name != "" ? var.api_name : "${var.project_name}-cafe-api"
}

resource "aws_ecr_repository" "cafe" {
  name                 = "${var.project_name}-cafe-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository_policy" "cafe" {
  repository = aws_ecr_repository.cafe.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaPull"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
        ]
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "cafe" {
  name = local.iam_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cafe_basic" {
  role       = aws_iam_role.cafe.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "cafe_dynamodb" {
  name = "${var.project_name}-cafe-lambda-dynamodb"
  role = aws_iam_role.cafe.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoCafesTable"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*",
        ]
      },
    ]
  })
}

resource "aws_lambda_function" "cafe" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.cafe.arn
  package_type  = "Image"
  image_uri     = local.cafe_image_uri
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  architectures = ["x86_64"]

  depends_on = [aws_ecr_repository_policy.cafe]

  environment {
    variables = merge(
      {
        TABLE_NAME  = var.dynamodb_table_name
        BUCKET_NAME = var.s3_bucket_name
      },
      var.google_places_api_key != "" ? { GOOGLE_PLACES_API_KEY = var.google_places_api_key } : {}
    )
  }
}

resource "aws_apigatewayv2_api" "cafe" {
  name          = local.api_name
  protocol_type = "HTTP"
  description   = "Cafe API (FastAPI /cafes, /v1/cafes/from-upload, …)"

  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
  }
}

resource "aws_apigatewayv2_integration" "cafe" {
  api_id                 = aws_apigatewayv2_api.cafe.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.cafe.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Single catch-all so API Gateway forwards all paths/methods to Mangum/FastAPI.
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.cafe.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.cafe.id}"
}

resource "aws_apigatewayv2_stage" "cafe" {
  api_id      = aws_apigatewayv2_api.cafe.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

resource "aws_lambda_permission" "cafe_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cafe.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.cafe.execution_arn}/*/*"
}
