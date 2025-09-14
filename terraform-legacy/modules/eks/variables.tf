variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.32"
}

variable "cluster_role_arn" {
  description = "ARN of the IAM role for the EKS cluster"
  type        = string
}

variable "node_group_role_arn" {
  description = "ARN of the IAM role for the EKS node group"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the EKS cluster"
  type        = list(string)
}

variable "cluster_security_group_id" {
  description = "Security group ID for the EKS cluster"
  type        = string
}

variable "instance_types" {
  description = "Instance types for EKS node group"
  type        = list(string)
  default     = ["t4g.small", "t3.small"]
}

variable "capacity_type" {
  description = "Type of capacity associated with the EKS Node Group. Valid values: ON_DEMAND, SPOT"
  type        = string
  default     = "ON_DEMAND"
}

variable "node_desired_size" {
  description = "Desired number of nodes in the node group"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of nodes in the node group"
  type        = number
  default     = 3
}

variable "node_min_size" {
  description = "Minimum number of nodes in the node group"
  type        = number
  default     = 1
}

variable "node_disk_size" {
  description = "Disk size for worker nodes in GB"
  type        = number
  default     = 20
}

variable "endpoint_private_access" {
  description = "Whether the Amazon EKS private API server endpoint is enabled"
  type        = bool
  default     = false
}

variable "endpoint_public_access" {
  description = "Whether the Amazon EKS public API server endpoint is enabled"
  type        = bool
  default     = true
}

variable "public_access_cidrs" {
  description = "List of CIDR blocks that can access the Amazon EKS public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "cluster_enabled_log_types" {
  description = "List of control plane log types to enable"
  type        = list(string)
  default     = ["api", "audit", "authenticator"]
}

variable "cloudwatch_log_group_retention_in_days" {
  description = "Retention in days for EKS control plane log group"
  type        = number
  default     = 30
}

variable "use_existing_log_group" {
  description = "Whether to use an existing CloudWatch log group"
  type        = bool
  default     = false
}

variable "existing_log_group_name" {
  description = "Name of existing CloudWatch log group to use"
  type        = string
  default     = ""
}

variable "use_existing_kms_key" {
  description = "Whether to use an existing KMS key for EKS encryption"
  type        = bool
  default     = false
}

variable "existing_kms_key_arn" {
  description = "ARN of existing KMS key to use for EKS encryption"
  type        = string
  default     = ""
}

variable "enable_vpc_cni_addon" {
  description = "Whether to enable the VPC CNI addon"
  type        = bool
  default     = true
}

variable "enable_coredns_addon" {
  description = "Whether to enable the CoreDNS addon"
  type        = bool
  default     = true
}

variable "enable_kube_proxy_addon" {
  description = "Whether to enable the kube-proxy addon"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}