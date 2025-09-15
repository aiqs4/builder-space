"""
IAM Module for EKS
Creates IAM roles and policies for EKS cluster and node groups
Refactored to function-based style following Pulumi best practices
"""

from .functions import create_iam_resources
from typing import Dict, Optional

# Export the main function for creating IAM resources
__all__ = ["create_iam_resources"]

# Legacy class wrapper for backwards compatibility during migration
class IAMResources:
    """IAM resources for EKS cluster - Legacy wrapper for backwards compatibility"""
    
    def __init__(self,
                 cluster_name: str,
                 use_existing_cluster_role: bool = False,
                 existing_cluster_role_name: str = "",
                 use_existing_node_role: bool = False,
                 existing_node_role_name: str = "",
                 tags: Dict[str, str] = None):
        
        # Use the new function-based approach internally
        self._resources = create_iam_resources(
            cluster_name=cluster_name,
            use_existing_cluster_role=use_existing_cluster_role,
            existing_cluster_role_name=existing_cluster_role_name,
            use_existing_node_role=use_existing_node_role,
            existing_node_role_name=existing_node_role_name,
            tags=tags
        )
    
    @property
    def cluster_role_arn(self):
        """Get cluster role ARN"""
        return self._resources["cluster_role_arn"]
    
    @property
    def cluster_role_name(self):
        """Get cluster role name"""
        return self._resources["cluster_role_name"]
    
    @property
    def node_group_role_arn(self):
        """Get node group role ARN"""
        return self._resources["node_group_role_arn"]
    
    @property
    def node_group_role_name(self):
        """Get node group role name"""
        return self._resources["node_group_role_name"]