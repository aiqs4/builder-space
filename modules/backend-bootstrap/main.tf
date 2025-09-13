# Backend Bootstrap Module
# This module creates S3 bucket and DynamoDB table for Terraform state backend
# Should be deployed separately before main infrastructure

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # random = {
    #   source  = "hashicorp/random"
    #   version = "~> 3.0"
    # }
  }
}

# Random suffix to ensure globally unique bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 bucket for Terraform state with encryption
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.cluster_name}-terraform-state-${var.aws_region}"

  tags = merge(var.tags, {
    Name        = "${var.cluster_name}-terraform-state"
    Purpose     = "Terraform state storage"
    Environment = "development"
    Module      = "backend-bootstrap"
  })
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
  name         = "${var.cluster_name}-terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST" # Most cost-effective for infrequent use
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = false # Keep costs minimal for dev environment
  }

  tags = merge(var.tags, {
    Name        = "${var.cluster_name}-terraform-state-lock"
    Purpose     = "Terraform state locking"
    Environment = "development"
    Module      = "backend-bootstrap"
  })
}

# Lifecycle policy for S3 bucket to minimize storage costs
resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "state_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

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