# EKS Module
# Creates EKS cluster and managed node groups

# CloudWatch Log Group for EKS cluster
resource "aws_cloudwatch_log_group" "cluster" {
  count             = var.use_existing_log_group ? 0 : 1
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = var.cloudwatch_log_group_retention_in_days

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-eks-log-group"
    Module = "eks"
  })
}

# KMS Key for EKS encryption (optional)
resource "aws_kms_key" "eks" {
  count       = var.use_existing_kms_key ? 0 : 1
  description = "EKS Secret Encryption Key for ${var.cluster_name}"

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-eks-kms-key"
    Module = "eks"
  })
}

resource "aws_kms_alias" "eks" {
  count         = var.use_existing_kms_key ? 0 : 1
  name          = "alias/${var.cluster_name}-eks"
  target_key_id = aws_kms_key.eks[0].key_id
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.cluster_version
  role_arn = var.cluster_role_arn

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = var.endpoint_private_access
    endpoint_public_access  = var.endpoint_public_access
    public_access_cidrs     = var.public_access_cidrs
    security_group_ids      = [var.cluster_security_group_id]
  }

  enabled_cluster_log_types = var.cluster_enabled_log_types

  # Use existing or new log group
  depends_on = [
    aws_cloudwatch_log_group.cluster
  ]

  # Optional KMS encryption
  encryption_config {
    provider {
      key_arn = var.use_existing_kms_key ? var.existing_kms_key_arn : aws_kms_key.eks[0].arn
    }
    resources = ["secrets"]
  }

  tags = merge(var.tags, {
    Name   = var.cluster_name
    Module = "eks"
  })
}

# EKS Node Group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-nodes"
  node_role_arn   = var.node_group_role_arn
  subnet_ids      = var.subnet_ids

  capacity_type  = var.capacity_type
  instance_types = var.instance_types
  disk_size      = var.node_disk_size

  scaling_config {
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
    min_size     = var.node_min_size
  }

  update_config {
    max_unavailable = 1
  }

  # Spot instance configuration (if enabled)
  dynamic "taint" {
    for_each = var.capacity_type == "SPOT" ? [1] : []
    content {
      key    = "spot-instance"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
  }

  # Ensure that IAM Role permissions are created before and deleted after EKS Node Group handling
  depends_on = [
    aws_eks_cluster.main
  ]

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-node-group"
    Module = "eks"
  })
}

# EKS Add-ons (optional but recommended)
resource "aws_eks_addon" "vpc_cni" {
  count                       = var.enable_vpc_cni_addon ? 1 : 0
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-vpc-cni-addon"
    Module = "eks"
  })
}

resource "aws_eks_addon" "coredns" {
  count                       = var.enable_coredns_addon ? 1 : 0
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "coredns"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  # Ensure node group is created first
  depends_on = [aws_eks_node_group.main]

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-coredns-addon"
    Module = "eks"
  })
}

resource "aws_eks_addon" "kube_proxy" {
  count                       = var.enable_kube_proxy_addon ? 1 : 0
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = merge(var.tags, {
    Name   = "${var.cluster_name}-kube-proxy-addon"
    Module = "eks"
  })
}