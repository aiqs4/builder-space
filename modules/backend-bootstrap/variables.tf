variable "cluster_name" {
  description = "Name of the EKS cluster (used for resource naming)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}