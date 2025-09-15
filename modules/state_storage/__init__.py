"""
State Storage Module
Creates S3 bucket and DynamoDB table for Pulumi state backend
Refactored to function-based style following Pulumi best practices
"""

from .functions import create_state_storage_resources
from typing import Dict, List

# Export the main function for creating state storage resources
__all__ = ["create_state_storage_resources"]

# Legacy class wrapper for backwards compatibility during migration
class StateStorageResources:
    """State storage resources for Pulumi backend - Legacy wrapper for backwards compatibility"""
    
    def __init__(self,
                 cluster_name: str,
                 aws_region: str,
                 tags: Dict[str, str] = None):
        
        # Use the new function-based approach internally
        self._resources = create_state_storage_resources(
            cluster_name=cluster_name,
            aws_region=aws_region,
            tags=tags
        )
        
        # Store values for legacy methods
        self.bucket_name = f"{cluster_name}-pulumi-state-{aws_region}"
        self.dynamodb_table_name = f"{cluster_name}-pulumi-state-lock"
        self.aws_region = aws_region
    
    @property
    def bucket_name_output(self):
        """Get S3 bucket name"""
        return self._resources["bucket_name_output"]
    
    @property
    def dynamodb_table_name_output(self):
        """Get DynamoDB table name"""
        return self._resources["dynamodb_table_name_output"]
    
    @property
    def backend_config(self) -> Dict[str, str]:
        """Get backend configuration for Pulumi"""
        return self._resources["backend_config"]
    
    def get_backend_configuration_commands(self) -> List[str]:
        """Get commands to configure Pulumi backend"""
        return self._resources["configuration_commands"]