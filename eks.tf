# Import EKS module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name    = var.cluster_name
  kubernetes_version = var.cluster_version

  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.public[*].id

  endpoint_public_access = true

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    main = {
      # name = "main"
      name    = "${var.cluster_name}-ng"

      instance_types = var.node_instance_types
      ami_type       = "AL2_ARM_64" # ARM-based AMI for t4g instances

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      disk_size = var.node_disk_size

      # Let the module create IAM role with proper policies
      # The module will automatically attach required policies

      # Additional security groups
      vpc_security_group_ids = [aws_security_group.node_group.id]

      # Launch template configuration
      launch_template_name            = "${var.cluster_name}-ng-lt"
      launch_template_use_name_prefix = true
      launch_template_description     = "Launch template for ${var.cluster_name} EKS managed node group"

      update_config = {
        max_unavailable_percentage = 33
      }

      labels = {
        Environment = "development"
        NodeGroup   = "main"
      }

      taints = {}

      tags = merge(var.tags, {
        Name = "${var.cluster_name}-ng"
      })
    }
  }

  # Cluster access configuration
  authentication_mode = "API_AND_CONFIG_MAP"
  enable_cluster_creator_admin_permissions = true

  # Access entries for node group role (equivalent to old aws_auth_roles)
  access_entries = {
    node_group = {
      principal_arn     = aws_iam_role.node_group.arn
      type              = "EC2_LINUX"
      user_name         = "system:node:{{EC2PrivateDNSName}}"
      kubernetes_groups = ["system:bootstrappers", "system:nodes"]
    }
  }


  tags = var.tags
}

# EKS Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = module.eks.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = "v1.15.1-eksbuild.1"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  service_account_role_arn    = null

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = module.eks.cluster_name
  addon_name                  = "coredns"
  addon_version               = "v1.10.1-eksbuild.5"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = module.eks.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = "v1.28.2-eksbuild.2"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.tags

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = module.eks.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = "v1.24.0-eksbuild.1"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  service_account_role_arn    = aws_iam_role.ebs_csi_driver.arn

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