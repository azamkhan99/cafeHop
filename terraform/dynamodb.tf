# DynamoDB table for cafe list (data sourced from S3 cafes.json; load with scripts/load_cafes_to_dynamodb.py)
resource "aws_dynamodb_table" "cafes" {
  name         = "${var.project_name}-cafes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "key"

  attribute {
    name = "key"
    type = "S"
  }
  attribute {
    name = "neighborhood"
    type = "S"
  }
  attribute {
    name = "name"
    type = "S"
  }

  global_secondary_index {
    name            = "neighborhood-index"
    hash_key        = "neighborhood"
    range_key       = "name"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-cafes"
  }
}

# Outputs for use by Lambdas or load script
output "cafes_table_name" {
  description = "DynamoDB table name for cafes"
  value       = aws_dynamodb_table.cafes.name
}

output "cafes_table_arn" {
  description = "DynamoDB table ARN for cafes"
  value       = aws_dynamodb_table.cafes.arn
}
