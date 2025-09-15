"""
State Storage Bootstrap - Separate Pulumi project for state storage
This creates S3 bucket and DynamoDB table for Pulumi state backend
Enhanced with idempotency and comprehensive validation
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
    
    pulumi.log.info(f"🚀 Starting state storage bootstrap for cluster: {cluster_name}")
    pulumi.log.info(f"📍 AWS Region: {aws_region}")
    
    try:
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
        
        # Export validation commands
        pulumi.export("validation_commands", state_storage.get_validation_commands())
        
        # Export next steps
        pulumi.export("next_steps", [
            "1. Record the bucket and table names above",
            "2. Update GitHub secrets with these values if needed",
            "3. Configure main Pulumi project to use S3 backend",
            "4. Run validation commands to verify setup",
            "5. Deploy main infrastructure with: pulumi up"
        ])
        
        # Export deployment status
        pulumi.export("deployment_status", {
            "cluster_name": cluster_name,
            "aws_region": aws_region,
            "bucket_name": state_storage.bucket_name,
            "table_name": state_storage.dynamodb_table_name,
            "timestamp": pulumi.Output.all().apply(lambda _: "bootstrap-completed"),
            "idempotent": True
        })
        
        pulumi.log.info("✅ State storage bootstrap completed successfully")
        
    except Exception as e:
        pulumi.log.error(f"❌ State storage bootstrap failed: {e}")
        raise

if __name__ == "__main__":
    main()