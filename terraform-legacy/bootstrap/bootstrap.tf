terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

module "backend_bootstrap" {
  source = "../modules/backend-bootstrap"

  cluster_name = var.cluster_name
  aws_region   = var.aws_region
  tags         = var.tags
}

output "backend_config" {
  description = "Backend configuration for main infrastructure"
  value       = module.backend_bootstrap.backend_config
}

output "backend_configuration_commands" {
  description = "Commands to configure the backend"
  value       = module.backend_bootstrap.backend_configuration_commands
}

output "bucket_name" {
  description = "S3 bucket name for state storage"
  value       = module.backend_bootstrap.bucket_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for state locking"
  value       = module.backend_bootstrap.dynamodb_table_name
}
