variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "af-south-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "builder-space"
}

variable "cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.32"
}

variable "node_instance_types" {
  description = "Instance types for EKS node group"
  type        = list(string)
  default     = ["t4g.small", "t3.small"] # ARM preferred, fallback to x86
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

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "enable_dns_hostnames" {
  description = "Enable DNS hostnames in VPC"
  type        = bool
  default     = true
}

variable "enable_dns_support" {
  description = "Enable DNS support in VPC"
  type        = bool
  default     = true
}

variable "map_public_ip_on_launch" {
  description = "Map public IP on instance launch"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default = {
    Project     = "builder-space-eks"
    Environment = "development"
    CostCenter  = "development"
  }
}

# Optional: Reuse pre-existing IAM roles instead of creating new ones
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

# Control plane logging configuration
variable "cluster_enabled_log_types" {
  description = "List of control plane log types to enable (api, audit, authenticator, controllerManager, scheduler)"
  type        = list(string)
  default     = ["api", "audit", "authenticator"]
}

variable "cloudwatch_log_group_retention_in_days" {
  description = "Retention in days for EKS control plane log group"
  type        = number
  default     = 30
}

variable "existing_cloudwatch_log_group_name" {
  description = "If set (non-empty), Terraform will import/use this existing CloudWatch log group instead of creating one (name must match module convention or be provided here)."
  type        = string
  default     = ""
}

# Cost-saving feature flags (disabled by default for free-credit period)
variable "enable_spot_instances" {
  description = "Enable spot instances for cost savings (~70% reduction). WARNING: Spot instances can be terminated at any time."
  type        = bool
  default     = false
}

variable "enable_reserved_instances" {
  description = "Enable reserved instances for long-term cost savings. Only use if running cluster 24/7 for extended periods."
  type        = bool
  default     = false
}

variable "enable_cluster_autoscaler" {
  description = "Enable cluster autoscaler to automatically scale nodes based on workload demand"
  type        = bool
  default     = false
}

variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling for dev environments (scale down during off-hours)"
  type        = bool
  default     = false
}

variable "scheduled_scale_down_time" {
  description = "Cron expression for when to scale down the cluster (e.g., '0 18 * * 1-5' for 6 PM weekdays)"
  type        = string
  default     = "0 18 * * 1-5"
}

variable "scheduled_scale_up_time" {
  description = "Cron expression for when to scale up the cluster (e.g., '0 8 * * 1-5' for 8 AM weekdays)"
  type        = string
  default     = "0 8 * * 1-5"
}

variable "enable_cost_monitoring" {
  description = "Enable cost monitoring and alerts"
  type        = bool
  default     = true
}

variable "cost_alert_threshold" {
  description = "Monthly cost threshold for alerts (in USD)"
  type        = number
  default     = 100
}

# KMS key reuse / creation
variable "use_existing_kms_key" {
  description = "If true, use an existing KMS key for EKS secrets encryption instead of creating a new one"
  type        = bool
  default     = false
}

variable "existing_kms_key_arn" {
  description = "ARN of existing KMS key to use when use_existing_kms_key = true"
  type        = string
  default     = ""
}