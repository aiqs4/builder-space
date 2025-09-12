output "backend_config" {
  description = "Backend configuration for terraform"
  value = {
    bucket         = aws_s3_bucket.terraform_state.bucket
    dynamodb_table = aws_dynamodb_table.terraform_state_lock.name
    region         = var.aws_region
    encrypt        = true
    key            = "terraform.tfstate"
  }
}

output "backend_configuration_commands" {
  description = "Commands to configure the backend"
  value = [
    "# Add this to your terraform block:",
    "terraform {",
    "  backend \"s3\" {",
    "    bucket         = \"${aws_s3_bucket.terraform_state.bucket}\"",
    "    key            = \"terraform.tfstate\"",
    "    region         = \"${var.aws_region}\"",
    "    dynamodb_table = \"${aws_dynamodb_table.terraform_state_lock.name}\"",
    "    encrypt        = true",
    "  }",
    "}",
    "",
    "# Then run:",
    "terraform init -backend-config=\"bucket=${aws_s3_bucket.terraform_state.bucket}\" -backend-config=\"dynamodb_table=${aws_dynamodb_table.terraform_state_lock.name}\""
  ]
}

output "bucket_name" {
  description = "Name of the S3 bucket for state storage"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.terraform_state_lock.name
}