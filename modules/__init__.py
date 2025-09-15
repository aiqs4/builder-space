"""
Pulumi modules for EKS infrastructure
Simple function-based approach following Pulumi best practices
"""

from .vpc import create_vpc_resources
from .iam import create_iam_resources  
from .eks import create_eks_resources
from .addons import create_addons_resources
from .state_storage import create_state_storage_resources

__all__ = [
    "create_vpc_resources",
    "create_iam_resources", 
    "create_eks_resources",
    "create_addons_resources",
    "create_state_storage_resources"
]