# S3 backend configuration for encrypted state storage
# This file should be applied first to create the backend infrastructure

# S3 bucket for Terraform state with encryption
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.cluster_name}-terraform-state-${random_id.bucket_suffix.hex}"

  tags = merge(var.tags, {
    Name        = "${var.cluster_name}-terraform-state"
    Purpose     = "Terraform state storage"
    Environment = "development"
  })
}

# Random suffix to ensure globally unique bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for state locking (minimal cost configuration)
resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "${var.cluster_name}-terraform-state-lock"
  billing_mode   = "PAY_PER_REQUEST"  # Most cost-effective for infrequent use
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = false  # Keep costs minimal for dev environment
  }

  tags = merge(var.tags, {
    Name        = "${var.cluster_name}-terraform-state-lock"
    Purpose     = "Terraform state locking"
    Environment = "development"
  })
}

# Lifecycle policy for S3 bucket to minimize storage costs
resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "state_lifecycle"
    status = "Enabled"

    # Delete old versions after 30 days to save costs
    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    # Abort incomplete multipart uploads after 1 day
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Output the backend configuration for reference
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
    "# Add this to your main.tf or create backend.tf:",
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
