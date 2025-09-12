# IAM Role for EKS Cluster
resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

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

  tags = var.tags
}

# Attach EKS Cluster Service Role Policy
resource "aws_iam_role_policy_attachment" "cluster_amazon_eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

# IAM Role for EKS Node Group
resource "aws_iam_role" "node_group" {
  name = "${var.cluster_name}-ng-role"

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

  tags = var.tags
}

# Attach required policies to Node Group role
resource "aws_iam_role_policy_attachment" "node_group_amazon_eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_amazon_eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_amazon_ec2_container_registry_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node_group.name
}

# Additional policy for systems manager access (useful for debugging)
resource "aws_iam_role_policy_attachment" "node_group_amazon_ssm_managed_instance_core" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.node_group.name
}

# Instance profile for the node group
resource "aws_iam_instance_profile" "node_group" {
  name = "${var.cluster_name}-ng-ip"
  role = aws_iam_role.node_group.name

  tags = var.tags
}

/*
  Attach a minimal identity policy to the existing GitHub Actions role
  named 'github-deploy-eks' so that the AWS data source used by the
  EKS module (aws_iam_session_context) can call iam:GetRole on the
  assumed role. This addresses the AccessDenied: iam:GetRole error
  observed when running Terraform from the OIDC-assumed role.

  Notes:
  - This resource will attach an inline policy to an existing role
    named 'github-deploy-eks' in the account where Terraform runs.
  - If the role does not exist yet, either create it first or attach
    the policy manually in the console. Attaching via Terraform to a
    role that doesn't exist will fail at apply time.
*/

# resource "aws_iam_role_policy" "github_deploy_role_self_read" {
#   name = "github-deploy-role-self-read"
#   role = "github-deploy-eks"  # existing role name created for GitHub Actions OIDC

#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Effect = "Allow"
#         Action = "iam:GetRole"
#         Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-deploy-eks"
#       }
#     ]
#   })
# }

/*
  The data source `aws_caller_identity.current` already exists in
  `main.tf`, so we reference it here. If you prefer this file to be
  self-contained, uncomment the data block below and remove the one in
  `main.tf`.

data "aws_caller_identity" "current" {}
*/