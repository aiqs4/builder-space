"""
EKS Module
Creates EKS cluster and managed node groups
Refactored to function-based style following Pulumi best practices
"""

from .functions import create_eks_resources
from typing import Dict, List, Optional

# Export the main function for creating EKS resources
__all__ = ["create_eks_resources"]

# Legacy class wrapper for backwards compatibility during migration
class EKSResources:
    """EKS cluster and node group resources - Legacy wrapper for backwards compatibility"""
    
    def __init__(self,
                 cluster_name: str,
                 cluster_version: str,
                 cluster_role_arn: 'pulumi.Output[str]',
                 node_group_role_arn: 'pulumi.Output[str]',
                 subnet_ids: 'List[pulumi.Output[str]]',
                 cluster_security_group_id: 'pulumi.Output[str]',
                 node_security_group_id: 'pulumi.Output[str]',
                 node_instance_types: List[str],
                 node_desired_size: int,
                 node_max_size: int,
                 node_min_size: int,
                 node_disk_size: int,
                 capacity_type: str = "ON_DEMAND",
                 cluster_enabled_log_types: List[str] = None,
                 cloudwatch_log_group_retention_in_days: int = 30,
                 use_existing_kms_key: bool = False,
                 existing_kms_key_arn: str = "",
                 enable_vpc_cni_addon: bool = True,
                 enable_coredns_addon: bool = True,
                 enable_kube_proxy_addon: bool = True,
                 endpoint_private_access: bool = False,
                 endpoint_public_access: bool = True,
                 public_access_cidrs: List[str] = None,
                 tags: Dict[str, str] = None):
        
        # Use the new function-based approach internally
        self._resources = create_eks_resources(
            cluster_name=cluster_name,
            cluster_version=cluster_version,
            cluster_role_arn=cluster_role_arn,
            node_group_role_arn=node_group_role_arn,
            subnet_ids=subnet_ids,
            cluster_security_group_id=cluster_security_group_id,
            node_security_group_id=node_security_group_id,
            node_instance_types=node_instance_types,
            node_desired_size=node_desired_size,
            node_max_size=node_max_size,
            node_min_size=node_min_size,
            node_disk_size=node_disk_size,
            capacity_type=capacity_type,
            cluster_enabled_log_types=cluster_enabled_log_types,
            cloudwatch_log_group_retention_in_days=cloudwatch_log_group_retention_in_days,
            use_existing_kms_key=use_existing_kms_key,
            existing_kms_key_arn=existing_kms_key_arn,
            enable_vpc_cni_addon=enable_vpc_cni_addon,
            enable_coredns_addon=enable_coredns_addon,
            enable_kube_proxy_addon=enable_kube_proxy_addon,
            endpoint_private_access=endpoint_private_access,
            endpoint_public_access=endpoint_public_access,
            public_access_cidrs=public_access_cidrs,
            tags=tags
        )
    
    @property
    def cluster_id(self):
        """Get cluster ID"""
        return self._resources["cluster_id"]
    
    @property
    def cluster_arn(self):
        """Get cluster ARN"""
        return self._resources["cluster_arn"]
    
    @property
    def cluster_endpoint(self):
        """Get cluster endpoint"""
        return self._resources["cluster_endpoint"]
    
    @property
    def cluster_version_output(self):
        """Get cluster version"""
        return self._resources["cluster_version_output"]
    
    @property
    def cluster_certificate_authority_data(self):
        """Get cluster certificate authority data"""
        return self._resources["cluster_certificate_authority_data"]
    
    @property
    def node_group_arn(self):
        """Get node group ARN"""
        return self._resources["node_group_arn"]
    
    @property
    def node_group_status(self):
        """Get node group status"""
        return self._resources["node_group_status"]