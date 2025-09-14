output "cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = var.use_existing_cluster_role ? data.aws_iam_role.existing_cluster[0].arn : aws_iam_role.cluster[0].arn
}

output "cluster_role_name" {
  description = "Name of the EKS cluster IAM role"
  value       = var.use_existing_cluster_role ? data.aws_iam_role.existing_cluster[0].name : aws_iam_role.cluster[0].name
}

output "node_group_role_arn" {
  description = "ARN of the EKS node group IAM role"
  value       = var.use_existing_node_role ? data.aws_iam_role.existing_node_group[0].arn : aws_iam_role.node_group[0].arn
}

output "node_group_role_name" {
  description = "Name of the EKS node group IAM role"
  value       = var.use_existing_node_role ? data.aws_iam_role.existing_node_group[0].name : aws_iam_role.node_group[0].name
}

output "node_group_instance_profile_name" {
  description = "Name of the node group instance profile"
  value       = var.use_existing_node_role ? "" : aws_iam_instance_profile.node_group[0].name
}