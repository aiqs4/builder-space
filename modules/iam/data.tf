# Lookup existing cluster role if reuse is enabled
data "aws_iam_role" "existing_cluster" {
  count = var.use_existing_cluster_role ? 1 : 0
  name  = var.existing_cluster_role_name
}

# Lookup existing node group role if reuse is enabled
data "aws_iam_role" "existing_node_group" {
  count = var.use_existing_node_role ? 1 : 0
  name  = var.existing_node_role_name
}