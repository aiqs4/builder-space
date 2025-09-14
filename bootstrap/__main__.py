"""
State Storage Bootstrap - Separate Pulumi project for state storage
This creates S3 bucket and DynamoDB table for Pulumi state backend
"""

import pulumi
import pulumi_aws as aws
from modules.state_storage import StateStorageResources

def main():
    """Bootstrap state storage resources"""
    
    # Get configuration
    config = pulumi.Config()
    cluster_name = config.get("cluster_name") or "builder-space"
    aws_region = config.get("aws:region") or "af-south-1"
    
    # Additional tags
    tags = {
        "Project": "builder-space-eks",
        "Environment": "development",
        "CostCenter": "development",
        "ManagedBy": "pulumi",
        "Purpose": "state-storage-bootstrap"
    }
    
    # Create state storage resources
    state_storage = StateStorageResources(
        cluster_name=cluster_name,
        aws_region=aws_region,
        tags=tags
    )
    
    # Export backend configuration
    pulumi.export("backend_config", state_storage.backend_config)
    pulumi.export("bucket_name", state_storage.bucket_name_output)
    pulumi.export("dynamodb_table_name", state_storage.dynamodb_table_name_output)
    
    # Export configuration commands
    pulumi.export("backend_configuration_commands", state_storage.get_backend_configuration_commands())
    
    # Export next steps
    pulumi.export("next_steps", [
        "1. Record the bucket and table names above",
        "2. Update GitHub secrets with these values if needed",
        "3. Configure main Pulumi project to use S3 backend",
        "4. Deploy main infrastructure with: pulumi up"
    ])

if __name__ == "__main__":
    main()