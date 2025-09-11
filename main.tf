# Main Terraform configuration entry point
# This file orchestrates the entire infrastructure setup

# Local values for resource naming and configuration
locals {
  cluster_name = var.cluster_name
  region       = var.aws_region

  common_tags = merge(var.tags, {
    Terraform   = "true"
    Environment = "development"
    Project     = "builder-space-eks"
  })
}

# Data sources
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# Outputs for quick reference
output "cluster_info" {
  description = "Quick cluster information"
  value = {
    cluster_name     = module.eks.cluster_name
    cluster_endpoint = module.eks.cluster_endpoint
    region           = data.aws_region.current.name
    account_id       = data.aws_caller_identity.current.account_id
  }
}

output "next_steps" {
  description = "Next steps after deployment"
  value = [
    "1. Configure kubectl: aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_name}",
    "2. Verify nodes: kubectl get nodes",
    "3. Check system pods: kubectl get pods -n kube-system",
    "4. Test internet connectivity: kubectl logs -n test deployment/test-internet-app",
    "5. Verify metrics server: kubectl top nodes",
    "6. View estimated costs in the 'estimated_monthly_cost' output"
  ]
}