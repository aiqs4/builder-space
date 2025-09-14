# Outputs for the main infrastructure
# These outputs provide essential information about the deployed infrastructure

# Individual resource outputs for compatibility
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = module.eks.cluster_version
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
}

# Grouped outputs for better organization
output "cluster_info" {
  description = "Quick cluster information"
  value = {
    cluster_name     = module.eks.cluster_name
    cluster_endpoint = module.eks.cluster_endpoint
    cluster_arn      = module.eks.cluster_arn
    cluster_version  = module.eks.cluster_version
    region           = data.aws_region.current.id
    account_id       = data.aws_caller_identity.current.account_id
  }
}

output "vpc_info" {
  description = "VPC information"
  value = {
    vpc_id             = module.vpc.vpc_id
    vpc_cidr_block     = module.vpc.vpc_cidr_block
    public_subnet_ids  = module.vpc.public_subnet_ids
    availability_zones = module.vpc.availability_zones
  }
}

output "iam_info" {
  description = "IAM role information"
  value = {
    cluster_role_arn     = module.iam.cluster_role_arn
    cluster_role_name    = module.iam.cluster_role_name
    node_group_role_arn  = module.iam.node_group_role_arn
    node_group_role_name = module.iam.node_group_role_name
  }
}

# Compatibility outputs for existing scripts
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.vpc.cluster_security_group_id
}

output "node_security_group_id" {
  description = "EKS node group security group ID"
  value       = module.vpc.node_group_security_group_id
}

output "cluster_iam_role_arn" {
  description = "EKS cluster IAM role ARN"
  value       = module.iam.cluster_role_arn
}

output "node_group_iam_role_arn" {
  description = "EKS node group IAM role ARN"
  value       = module.iam.node_group_role_arn
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "kubectl_config_command" {
  description = "kubectl configuration command"
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_name}"
}

# Next steps and commands
output "next_steps" {
  description = "Next steps after deployment"
  value = [
    "1. Configure kubectl: aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_name}",
    "2. Verify nodes: kubectl get nodes",
    "3. Check system pods: kubectl get pods -n kube-system",
    "4. Test internet connectivity: kubectl logs -n ${module.addons.test_namespace} deployment/${module.addons.test_deployment_name}",
    "5. Verify metrics server: kubectl top nodes",
    "6. View estimated costs below"
  ]
}

output "test_commands" {
  description = "Commands to test the deployment"
  value = [
    "# Check cluster status",
    "kubectl cluster-info",
    "",
    "# Check nodes",
    "kubectl get nodes -o wide",
    "",
    "# Check system pods",
    "kubectl get pods -n kube-system",
    "",
    "# Test internet connectivity",
    "kubectl logs -n ${module.addons.test_namespace} deployment/${module.addons.test_deployment_name} --tail=10",
    "",
    "# Check resource usage",
    "kubectl top nodes",
    "kubectl top pods -A"
  ]
}

# Cost estimation with optimization info
output "estimated_monthly_cost" {
  description = "Estimated monthly costs based on current configuration"
  value = {
    eks_cluster_cost  = "$72.00"
    node_group_cost   = var.enable_spot_instances ? "~$8.64 (${var.node_desired_size}x ${join(",", local.instance_types)} spot instances ~70% savings)" : "~$28.80 (${var.node_desired_size}x ${join(",", local.instance_types)} on-demand instances)"
    storage_cost      = "~$${var.node_desired_size * var.node_disk_size * 0.10}"
    total_estimated   = var.enable_spot_instances ? "~$88-95/month (with spot instances)" : "~$108-115/month (on-demand instances)"
    savings_potential = var.enable_spot_instances ? "Current: Using spot instances" : "Potential: Enable spot instances to save ~$20/month"
  }
}

# Migration information for existing resources
output "migration_info" {
  description = "Information for migrating existing resources"
  value = {
    import_commands = [
      "# Import existing IAM roles (if they exist):",
      "terraform import module.iam.aws_iam_role.cluster[0] ${var.cluster_name}-cluster-role",
      "terraform import module.iam.aws_iam_role.node_group[0] ${var.cluster_name}-ng-role",
      "",
      "# Import existing CloudWatch log group (if it exists):",
      "terraform import module.eks.aws_cloudwatch_log_group.cluster[0] /aws/eks/${var.cluster_name}/cluster",
      "",
      "# Import existing KMS key (if managed by Terraform):",
      "# terraform import module.eks.aws_kms_key.eks[0] <key-id>"
    ]
    use_existing_flags = {
      cluster_role = "Set use_existing_cluster_role = true and existing_cluster_role_name = \"<role-name>\""
      node_role    = "Set use_existing_node_role = true and existing_node_role_name = \"<role-name>\""
      log_group    = "Set existing_cloudwatch_log_group_name = \"/aws/eks/${var.cluster_name}/cluster\""
      kms_key      = "Set use_existing_kms_key = true and existing_kms_key_arn = \"<key-arn>\""
    }
  }
}

# Configuration summary
output "configuration_summary" {
  description = "Summary of current configuration and cost optimization settings"
  value = {
    cluster_name        = var.cluster_name
    cluster_version     = var.cluster_version
    node_instance_types = local.instance_types
    capacity_type       = local.capacity_type
    node_count          = "${var.node_min_size}-${var.node_max_size} (desired: ${var.node_desired_size})"
    cost_optimizations = {
      spot_instances     = var.enable_spot_instances ? "✅ Enabled" : "❌ Disabled (enable for ~70% savings)"
      reserved_instances = var.enable_reserved_instances ? "✅ Enabled" : "❌ Disabled"
      cluster_autoscaler = var.enable_cluster_autoscaler ? "✅ Enabled" : "❌ Disabled"
      scheduled_scaling  = var.enable_scheduled_scaling ? "✅ Enabled" : "❌ Disabled"
    }
    addons_status = {
      metrics_server               = module.addons.metrics_server_status
      aws_load_balancer_controller = module.addons.aws_load_balancer_controller_status
      test_deployment              = module.addons.test_deployment_name != "" ? "✅ Deployed" : "❌ Not deployed"
    }
  }
}