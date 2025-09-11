# Import EKS module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id                         = aws_vpc.main.id
  subnet_ids                     = aws_subnet.public[*].id
  cluster_endpoint_public_access = true

  # Cluster security group
  cluster_security_group_id = aws_security_group.cluster.id

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    main = {
      name = "${var.cluster_name}-node-group"

      instance_types = var.node_instance_types
      ami_type       = "AL2_ARM_64" # ARM-based AMI for t4g instances

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      disk_size = var.node_disk_size

      # Use our custom IAM role
      iam_role_arn = aws_iam_role.node_group.arn

      # Security group for nodes
      vpc_security_group_ids = [aws_security_group.node_group.id]

      # Launch template
      launch_template_name            = "${var.cluster_name}-node-group-lt"
      launch_template_use_name_prefix = true
      launch_template_description     = "Launch template for ${var.cluster_name} EKS managed node group"

      update_config = {
        max_unavailable_percentage = 33
      }

      labels = {
        Environment = "development"
        NodeGroup   = "main"
      }

      taints = []

      tags = merge(var.tags, {
        Name = "${var.cluster_name}-node-group"
      })
    }
  }

  # Cluster access entry
  access_entries = {
    cluster = {
      kubernetes_groups = []
      principal_arn     = aws_iam_role.cluster.arn

      policy_associations = {
        cluster = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }

  tags = var.tags
}

# EKS Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "vpc-cni"
  addon_version            = "v1.15.1-eksbuild.1"
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = null

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "aws_eks_addon" "coredns" {
  cluster_name      = module.eks.cluster_name
  addon_name        = "coredns"
  addon_version     = "v1.10.1-eksbuild.5"
  resolve_conflicts = "OVERWRITE"

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name      = module.eks.cluster_name
  addon_name        = "kube-proxy"
  addon_version     = "v1.28.2-eksbuild.2"
  resolve_conflicts = "OVERWRITE"

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = "v1.24.0-eksbuild.1"
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = aws_iam_role.ebs_csi_driver.arn

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

# IAM role for EBS CSI driver
resource "aws_iam_role" "ebs_csi_driver" {
  name = "${var.cluster_name}-ebs-csi-driver-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi_driver" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.ebs_csi_driver.name
}