"""
VPC Module for EKS
Creates VPC, subnets, route tables, and security groups for EKS
Refactored to function-based style following Pulumi best practices
"""

from .functions import create_vpc_resources
from typing import Dict, List, Any

# Export the main function for creating VPC resources
__all__ = ["create_vpc_resources"]

# Legacy class wrapper for backwards compatibility during migration
class VPCResources:
    """VPC resources for EKS cluster - Legacy wrapper for backwards compatibility"""
    
    def __init__(self, 
                 cluster_name: str,
                 vpc_cidr: str,
                 public_subnet_cidrs: List[str],
                 enable_dns_hostnames: bool = True,
                 enable_dns_support: bool = True,
                 map_public_ip_on_launch: bool = True,
                 tags: Dict[str, str] = None):
        
        # Use the new function-based approach internally
        self._resources = create_vpc_resources(
            cluster_name=cluster_name,
            vpc_cidr=vpc_cidr,
            public_subnet_cidrs=public_subnet_cidrs,
            enable_dns_hostnames=enable_dns_hostnames,
            enable_dns_support=enable_dns_support,
            map_public_ip_on_launch=map_public_ip_on_launch,
            tags=tags
        )
    
    @property
    def vpc_id(self):
        """Get VPC ID"""
        return self._resources["vpc_id"]
    
    @property
    def vpc_cidr_block(self):
        """Get VPC CIDR block"""
        return self._resources["vpc_cidr_block"]
    
    @property
    def public_subnet_ids(self):
        """Get public subnet IDs"""
        return self._resources["public_subnet_ids"]
    
    @property
    def cluster_security_group_id(self):
        """Get cluster security group ID"""
        return self._resources["cluster_security_group_id"]
    
    @property
    def node_group_security_group_id(self):
        """Get node group security group ID"""
        return self._resources["node_group_security_group_id"]
    
    @property
    def availability_zones(self):
        """Get availability zones"""
        return self._resources["availability_zones"]