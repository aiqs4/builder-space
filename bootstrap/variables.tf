variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "funda"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "af-south-1"
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
