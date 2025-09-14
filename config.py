"""
Configuration management for Builder Space EKS deployment
"""

import pulumi
from typing import Dict, Any, List

class Config:
    """Centralized configuration management for the EKS deployment"""
    
    def __init__(self):
        self.config = pulumi.Config()
        
        # AWS Configuration
        self.aws_region = self.config.get("aws:region") or "af-south-1"
        
        # Cluster Configuration
        self.cluster_name = self.config.get("cluster_name") or "builder-space"
        self.cluster_version = self.config.get("cluster_version") or "1.32"
        
        # Node Configuration
        self.node_instance_types = self.config.get_object("node_instance_types") or ["t4g.small", "t3.small"]
        self.node_desired_size = self.config.get_int("node_desired_size") or 2
        self.node_max_size = self.config.get_int("node_max_size") or 3
        self.node_min_size = self.config.get_int("node_min_size") or 1
        self.node_disk_size = self.config.get_int("node_disk_size") or 20
        
        # VPC Configuration
        self.vpc_cidr = self.config.get("vpc_cidr") or "10.0.0.0/16"
        self.public_subnet_cidrs = self.config.get_object("public_subnet_cidrs") or ["10.0.1.0/24", "10.0.2.0/24"]
        self.enable_dns_hostnames = self.config.get_bool("enable_dns_hostnames") or True
        self.enable_dns_support = self.config.get_bool("enable_dns_support") or True
        self.map_public_ip_on_launch = self.config.get_bool("map_public_ip_on_launch") or True
        
        # Cost Optimization Features
        self.enable_spot_instances = self.config.get_bool("enable_spot_instances") or False
        self.enable_reserved_instances = self.config.get_bool("enable_reserved_instances") or False
        self.enable_cluster_autoscaler = self.config.get_bool("enable_cluster_autoscaler") or False
        self.enable_scheduled_scaling = self.config.get_bool("enable_scheduled_scaling") or False
        self.enable_cost_monitoring = self.config.get_bool("enable_cost_monitoring") or True
        self.cost_alert_threshold = self.config.get_int("cost_alert_threshold") or 100
        
        # Resource Management
        self.use_existing_cluster_role = self.config.get_bool("use_existing_cluster_role") or False
        self.existing_cluster_role_name = self.config.get("existing_cluster_role_name") or ""
        self.use_existing_node_role = self.config.get_bool("use_existing_node_role") or False
        self.existing_node_role_name = self.config.get("existing_node_role_name") or ""
        self.use_existing_kms_key = self.config.get_bool("use_existing_kms_key") or False
        self.existing_kms_key_arn = self.config.get("existing_kms_key_arn") or ""
        
        # Logging Configuration
        self.cluster_enabled_log_types = self.config.get_object("cluster_enabled_log_types") or ["api", "audit", "authenticator"]
        self.cloudwatch_log_group_retention_in_days = self.config.get_int("cloudwatch_log_group_retention_in_days") or 30
        
        # EKS Addons
        self.enable_vpc_cni_addon = self.config.get_bool("enable_vpc_cni_addon") or True
        self.enable_coredns_addon = self.config.get_bool("enable_coredns_addon") or True
        self.enable_kube_proxy_addon = self.config.get_bool("enable_kube_proxy_addon") or True
        
        # Additional tags
        self.additional_tags = self.config.get_object("tags") or {}
        
    @property
    def common_tags(self) -> Dict[str, str]:
        """Get common tags for all resources"""
        base_tags = {
            "Environment": "development",
            "Project": "builder-space-eks",
            "Repository": "aiqs4/builder-space",
            "ManagedBy": "pulumi",
            "CostCenter": "development"
        }
        base_tags.update(self.additional_tags)
        return base_tags
    
    @property
    def capacity_type(self) -> str:
        """Get node group capacity type based on spot instance configuration"""
        return "SPOT" if self.enable_spot_instances else "ON_DEMAND"
    
    @property
    def optimized_instance_types(self) -> List[str]:
        """Get optimized instance types based on spot instance configuration"""
        if self.enable_spot_instances:
            return ["t4g.small", "t3.small", "t2.small"]
        return self.node_instance_types

def get_config() -> Config:
    """Get the global configuration instance"""
    return Config()