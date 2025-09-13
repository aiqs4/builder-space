terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Backend configuration - update bucket and table names after bootstrap
  backend "s3" {
    bucket         = "UPDATE_WITH_BOOTSTRAP_BUCKET_NAME"
    key            = "terraform.tfstate"
    region         = "af-south-1"
    dynamodb_table = "UPDATE_WITH_BOOTSTRAP_TABLE_NAME"
    encrypt        = true
  }
}