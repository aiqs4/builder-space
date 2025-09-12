# IAM Module
# Creates IAM roles and policies for EKS cluster and node groups

# Data sources
data "aws_caller_identity" "current" {}

# EKS Cluster IAM Role
resource "aws_iam_role" "cluster" {
  count = var.use_existing_cluster_role ? 0 : 1
  name  = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-cluster-role"
    Module = "iam"
  })
}

# Attach required policies to EKS cluster role
resource "aws_iam_role_policy_attachment" "cluster_amazon_eks_cluster_policy" {
  count      = var.use_existing_cluster_role ? 0 : 1
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster[0].name
}

# EKS Node Group IAM Role
resource "aws_iam_role" "node_group" {
  count = var.use_existing_node_role ? 0 : 1
  name  = "${var.cluster_name}-ng-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-node-group-role"
    Module = "iam"
  })
}

# Attach required policies to node group role
resource "aws_iam_role_policy_attachment" "node_group_amazon_eks_worker_node_policy" {
  count      = var.use_existing_node_role ? 0 : 1
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node_group[0].name
}

resource "aws_iam_role_policy_attachment" "node_group_amazon_eks_cni_policy" {
  count      = var.use_existing_node_role ? 0 : 1
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node_group[0].name
}

resource "aws_iam_role_policy_attachment" "node_group_amazon_ec2_container_registry_read_only" {
  count      = var.use_existing_node_role ? 0 : 1
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node_group[0].name
}

# Additional policy for systems manager access (useful for debugging)
resource "aws_iam_role_policy_attachment" "node_group_amazon_ssm_managed_instance_core" {
  count      = var.use_existing_node_role ? 0 : 1
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.node_group[0].name
}

# Instance profile for the node group
resource "aws_iam_instance_profile" "node_group" {
  count = var.use_existing_node_role ? 0 : 1
  name  = "${var.cluster_name}-ng-ip"
  role  = aws_iam_role.node_group[0].name

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-node-group-instance-profile"
    Module = "iam"
  })
}