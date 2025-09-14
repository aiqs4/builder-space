variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the cluster is deployed"
  type        = string
}

variable "enable_test_deployment" {
  description = "Whether to enable test deployment for connectivity verification"
  type        = bool
  default     = true
}

variable "enable_metrics_server" {
  description = "Whether to enable metrics server"
  type        = bool
  default     = true
}

variable "enable_aws_load_balancer_controller" {
  description = "Whether to enable AWS Load Balancer Controller"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}