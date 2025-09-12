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

output "cluster_platform_version" {
  description = "EKS cluster platform version"
  value       = module.eks.cluster_platform_version
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
}

output "cluster_oidc_issuer_url" {
  description = "EKS cluster OIDC issuer URL"
  value       = module.eks.cluster_oidc_issuer_url
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_security_group.cluster.id
}

output "node_groups" {
  description = "EKS node groups"
  value       = module.eks.eks_managed_node_groups
  sensitive   = true
}

output "node_security_group_id" {
  description = "EKS node group security group ID"
  value       = aws_security_group.node_group.id
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.main.id
}

output "cluster_iam_role_arn" {
  description = "EKS cluster IAM role ARN"
  value       = var.use_existing_cluster_role ? data.aws_iam_role.existing_cluster[0].arn : aws_iam_role.cluster[0].arn
}

output "node_group_iam_role_arn" {
  description = "EKS node group IAM role ARN"
  value       = var.use_existing_node_role ? data.aws_iam_role.existing_node_group[0].arn : aws_iam_role.node_group[0].arn
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "kubectl_config_command" {
  description = "kubectl configuration command"
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_name}"
}

output "test_commands" {
  description = "Commands to test the cluster"
  value = {
    get_nodes     = "kubectl get nodes"
    get_pods      = "kubectl get pods -A"
    test_internet = "kubectl logs -n test deployment/test-internet-app"
    check_metrics = "kubectl top nodes"
    cluster_info  = "kubectl cluster-info"
  }
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown (USD)"
  value = {
    eks_cluster          = "72.00" # $0.10/hour * 24 * 30
    node_group_t4g_small = "28.80" # $0.0192/hour * 2 instances * 24 * 30 (af-south-1)
    ebs_storage          = "8.00"  # 40GB total (20GB per node) * $0.20/GB/month
    total_estimated      = "108.80"
    note                 = "Actual costs may vary based on usage, data transfer, and other factors"
  }
}