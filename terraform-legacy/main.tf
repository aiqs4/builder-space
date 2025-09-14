# Main Terraform configuration entry point
# This file orchestrates the modular infrastructure setup

terraform {
  required_version = ">= 1.11"

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
    bucket         = "builder-space-terraform-state-af-south-1"
    # bucket         = "${var.cluster_name}-terraform-state-${var.aws_region}" --- IGNORE ---
    key            = "terraform.tfstate"
    region         = "af-south-1"
    use_lockfile = true
    # TODO: delete the dynamo db deployment
    # dynamodb_table = "${var.cluster_name}-terraform-state-lock"
    encrypt        = true
  }
}

# Provider configurations
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(local.common_tags, {
      Project     = "builder-space-eks"
      Environment = "development"
      ManagedBy   = "terraform"
    })
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Local values for resource naming and configuration
locals {
  cluster_name = var.cluster_name
  region       = var.aws_region

  common_tags = merge(var.tags, {
    Terraform   = "true"
    Environment = "development"
    Project     = "builder-space-eks"
    Repository  = "aiqs4/builder-space"
  })

  # Cost optimization configurations
  capacity_type  = var.enable_spot_instances ? "SPOT" : "ON_DEMAND"
  instance_types = var.enable_spot_instances ? ["t4g.small", "t3.small", "t2.small"] : var.node_instance_types
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  cluster_name            = var.cluster_name
  vpc_cidr                = var.vpc_cidr
  public_subnet_cidrs     = var.public_subnet_cidrs
  enable_dns_hostnames    = var.enable_dns_hostnames
  enable_dns_support      = var.enable_dns_support
  map_public_ip_on_launch = var.map_public_ip_on_launch
  tags                    = local.common_tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  cluster_name               = var.cluster_name
  use_existing_cluster_role  = var.use_existing_cluster_role
  existing_cluster_role_name = var.existing_cluster_role_name
  use_existing_node_role     = var.use_existing_node_role
  existing_node_role_name    = var.existing_node_role_name
  tags                       = local.common_tags
}

# EKS Module
module "eks" {
  source = "./modules/eks"

  cluster_name              = var.cluster_name
  cluster_version           = var.cluster_version
  cluster_role_arn          = module.iam.cluster_role_arn
  node_group_role_arn       = module.iam.node_group_role_arn
  subnet_ids                = module.vpc.public_subnet_ids
  cluster_security_group_id = module.vpc.cluster_security_group_id

  # Instance configuration with cost optimization
  instance_types    = local.instance_types
  capacity_type     = local.capacity_type
  node_desired_size = var.node_desired_size
  node_max_size     = var.node_max_size
  node_min_size     = var.node_min_size
  node_disk_size    = var.node_disk_size

  # Logging and encryption
  cluster_enabled_log_types              = var.cluster_enabled_log_types
  cloudwatch_log_group_retention_in_days = var.cloudwatch_log_group_retention_in_days
  use_existing_log_group                 = var.existing_cloudwatch_log_group_name != ""
  existing_log_group_name                = var.existing_cloudwatch_log_group_name
  use_existing_kms_key                   = var.use_existing_kms_key
  existing_kms_key_arn                   = var.existing_kms_key_arn

  tags = local.common_tags
}

# Addons Module
module "addons" {
  source = "./modules/addons"

  cluster_name                        = var.cluster_name
  aws_region                          = var.aws_region
  vpc_id                              = module.vpc.vpc_id
  enable_test_deployment              = true
  enable_metrics_server               = true
  enable_aws_load_balancer_controller = false # Disabled by default for cost savings
  tags                                = local.common_tags

  depends_on = [module.eks]
}