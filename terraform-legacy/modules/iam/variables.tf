variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "use_existing_cluster_role" {
  description = "If true, skip creation of the EKS cluster IAM role and use the provided existing role name"
  type        = bool
  default     = false
}

variable "existing_cluster_role_name" {
  description = "Name of an existing IAM role to use for the EKS cluster (required if use_existing_cluster_role = true)"
  type        = string
  default     = ""
}

variable "use_existing_node_role" {
  description = "If true, skip creation of the node group IAM role and use the provided existing role name"
  type        = bool
  default     = false
}

variable "existing_node_role_name" {
  description = "Name of an existing IAM role to use for the EKS managed node group (required if use_existing_node_role = true)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}