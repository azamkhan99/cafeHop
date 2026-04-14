# Image microservice: HTTP API → Lambda (FastAPI + Mangum): POST /presigned-url, POST /process, GET /, /docs, …
# Build: services/image/Dockerfile.lambda — push: scripts/docker_push_lambda_image.sh

data "aws_caller_identity" "current" {}

locals {
  image_uri   = "${aws_ecr_repository.image.repository_url}:${var.image_lambda_image_tag}"
  iam_name    = var.iam_role_name != "" ? var.iam_role_name : "${var.project_name}-image-lambda-role"
  api_name    = var.api_name != "" ? var.api_name : "${var.project_name}-image-api"
}

resource "aws_ecr_repository" "image" {
  name                 = "${var.project_name}-image-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository_policy" "image" {
  repository = aws_ecr_repository.image.name
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

resource "aws_iam_role" "image" {
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

resource "aws_iam_role_policy_attachment" "image_basic" {
  role       = aws_iam_role.image.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "image_s3" {
  name = "${var.project_name}-image-lambda-s3"
  role = aws_iam_role.image.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}"
      },
      {
        Sid    = "ObjectRW"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:GetObjectVersion",
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      },
    ]
  })
}

resource "aws_lambda_function" "image" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.image.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  architectures = ["x86_64"]

  depends_on = [aws_ecr_repository_policy.image]

  environment {
    variables = {
      BUCKET_NAME = var.s3_bucket_name
    }
  }
}

resource "aws_apigatewayv2_api" "image" {
  name          = local.api_name
  protocol_type = "HTTP"
  description   = "Image API (presigned-url, process)"

  cors_configuration {
    allow_origins = var.cors_allow_origins
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
  }
}

resource "aws_apigatewayv2_integration" "image" {
  api_id                 = aws_apigatewayv2_api.image.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.image.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Single catch-all so GET /, GET /docs, and POST routes all reach Mangum/FastAPI (same pattern as module.cafe).
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.image.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.image.id}"
}

resource "aws_apigatewayv2_stage" "image" {
  api_id      = aws_apigatewayv2_api.image.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

resource "aws_lambda_permission" "image_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.image.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.image.execution_arn}/*/*"
}
