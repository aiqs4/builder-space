output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = aws_eks_cluster.main.version
}

output "node_group_arn" {
  description = "EKS node group ARN"
  value       = aws_eks_node_group.main.arn
}

output "node_group_status" {
  description = "EKS node group status"
  value       = aws_eks_node_group.main.status
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = var.use_existing_log_group ? var.existing_log_group_name : (length(aws_cloudwatch_log_group.cluster) > 0 ? aws_cloudwatch_log_group.cluster[0].name : "")
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for EKS encryption"
  value       = var.use_existing_kms_key ? var.existing_kms_key_arn : (length(aws_kms_key.eks) > 0 ? aws_kms_key.eks[0].arn : "")
}