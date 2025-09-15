"""
Addons Module
Kubernetes add-ons and applications for EKS cluster
Refactored to function-based style following Pulumi best practices
"""

from .functions import create_addons_resources
from typing import Dict, Optional

# Export the main function for creating addon resources
__all__ = ["create_addons_resources"]

# Legacy class wrapper for backwards compatibility during migration
class AddonsResources:
    """Kubernetes addons for EKS cluster - Legacy wrapper for backwards compatibility"""
    
    def __init__(self,
                 cluster_name: str,
                 cluster_endpoint: 'pulumi.Output[str]',
                 cluster_ca_data: 'pulumi.Output[str]',
                 enable_metrics_server: bool = True,
                 enable_aws_load_balancer_controller: bool = False,
                 enable_test_deployment: bool = True,
                 tags: Dict[str, str] = None):
        
        # Use the new function-based approach internally
        self._resources = create_addons_resources(
            cluster_name=cluster_name,
            cluster_endpoint=cluster_endpoint,
            cluster_ca_data=cluster_ca_data,
            enable_metrics_server=enable_metrics_server,
            enable_aws_load_balancer_controller=enable_aws_load_balancer_controller,
            enable_test_deployment=enable_test_deployment,
            tags=tags
        )
    
    @property
    def metrics_server_status(self) -> str:
        """Get metrics server status"""
        return self._resources["metrics_server_status"]
    
    @property
    def aws_load_balancer_controller_status(self) -> str:
        """Get AWS Load Balancer Controller status"""
        return self._resources["aws_load_balancer_controller_status"]
    
    @property
    def test_namespace_name(self):
        """Get test namespace name"""
        return self._resources["test_namespace_name"]
    
    @property
    def test_deployment_name(self) -> str:
        """Get test deployment name"""
        return self._resources["test_deployment_name"]