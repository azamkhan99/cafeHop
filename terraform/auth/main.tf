# Auth (uploadAuth) Lambda + HTTP API — container image from ECR.
# Build & push image first: ./scripts/docker_push_lambda_auth.sh <tag>
# Then apply Terraform (set module variable auth_lambda_image_tag to the same tag).

data "aws_caller_identity" "current" {}

locals {
  auth_image = "${aws_ecr_repository.auth.repository_url}:${var.auth_lambda_image_tag}"
}

resource "aws_ecr_repository" "auth" {
  name                 = "${var.project_name}-auth-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository_policy" "auth" {
  repository = aws_ecr_repository.auth.name
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

# IAM role for auth Lambda
resource "aws_iam_role" "auth" {
  name = var.iam_role_name != "" ? var.iam_role_name : "${var.project_name}-auth-lambda-role"

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

resource "aws_iam_role_policy_attachment" "auth_basic" {
  role       = aws_iam_role.auth.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "auth" {
  function_name = "uploadAuth"
  role          = aws_iam_role.auth.arn
  package_type  = "Image"
  image_uri     = local.auth_image
  timeout       = 3
  memory_size   = 128

  architectures = ["x86_64"]

  depends_on = [aws_ecr_repository_policy.auth]

  environment {
    variables = {
      JWT_SECRET = var.jwt_secret
    }
  }
}

# HTTP API (v2) with CORS; $default stage, POST /get-token -> Lambda
resource "aws_apigatewayv2_api" "auth" {
  name          = var.api_name != "" ? var.api_name : "${var.project_name}-auth-api"
  protocol_type = "HTTP"
  description   = "Auth API (get-token)"

  cors_configuration {
    allow_origins = ["https://azamkhan99.github.io", "http://127.0.0.1:3000"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
  }
}

resource "aws_apigatewayv2_integration" "auth" {
  api_id                 = aws_apigatewayv2_api.auth.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.auth.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_token" {
  api_id    = aws_apigatewayv2_api.auth.id
  route_key = "POST /get-token"
  target    = "integrations/${aws_apigatewayv2_integration.auth.id}"
}

resource "aws_apigatewayv2_stage" "auth" {
  api_id      = aws_apigatewayv2_api.auth.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

resource "aws_lambda_permission" "auth_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.auth.execution_arn}/*/*"
}
