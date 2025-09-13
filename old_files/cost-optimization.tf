# Cost Optimization Configuration
# Apply these settings to minimize costs while maintaining cluster functionality

# Node group optimizations for cost efficiency
variable "enable_spot_instances" {
  description = "Use spot instances for significant cost savings (~70%)"
  type        = bool
  default     = false
}

variable "enable_single_node_dev" {
  description = "Use single node for development to save costs"
  type        = bool
  default     = false
}

variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling for off-hours cost savings"
  type        = bool
  default     = false
}

# Cost-optimized instance configuration
locals {
  # Spot instance configuration (save ~70% on compute)
  spot_instance_config = var.enable_spot_instances ? {
    capacity_type  = "SPOT"
    instance_types = ["t4g.small", "t3.small", "t3a.small", "t2.small"]
    } : {
    capacity_type  = "ON_DEMAND"
    instance_types = var.node_instance_types
  }

  # Development single-node configuration
  dev_node_config = var.enable_single_node_dev ? {
    min_size     = 1
    max_size     = 2
    desired_size = 1
    } : {
    min_size     = var.node_min_size
    max_size     = var.node_max_size
    desired_size = var.node_desired_size
  }

  # Optimized disk size (minimum viable)
  optimized_disk_size = 20 # Reduced from default, sufficient for most workloads
}
