"""
State Storage Module Functions
Creates S3 bucket and DynamoDB table for Pulumi state backend
Refactored to function-based style following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List


def create_s3_bucket(name: str, bucket_name: str, tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create S3 bucket for Pulumi state storage
    
    Args:
        name: Resource name
        bucket_name: S3 bucket name
        tags: Additional tags
        
    Returns:
        Dict with bucket resource and outputs
    """
    tags = tags or {}
    
    bucket = aws.s3.Bucket(
        f"{name}-pulumi-state-bucket",
        bucket=bucket_name,
        tags={
            **tags,
            "Name": f"{name}-pulumi-state",
            "Purpose": "Pulumi state storage",
            "Environment": "development",
            "Module": "state-storage"
        }
    )
    
    return {
        "bucket": bucket,
        "bucket_id": bucket.id,
        "bucket_name": bucket_name
    }


def configure_s3_bucket_settings(name: str, bucket_id: 'pulumi.Output[str]') -> Dict[str, any]:
    """
    Configure S3 bucket settings for state storage
    
    Args:
        name: Resource name prefix
        bucket_id: S3 bucket ID
        
    Returns:
        Dict with bucket configuration resources
    """
    # Enable versioning
    versioning = aws.s3.BucketVersioning(
        f"{name}-state-bucket-versioning",
        bucket=bucket_id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled"
        )
    )
    
    # Enable encryption
    encryption = aws.s3.BucketServerSideEncryptionConfiguration(
        f"{name}-state-bucket-encryption",
        bucket=bucket_id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="AES256"
                ),
                bucket_key_enabled=True
            )
        ]
    )
    
    # Block public access
    public_access_block = aws.s3.BucketPublicAccessBlock(
        f"{name}-state-bucket-pab",
        bucket=bucket_id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True
    )
    
    # Configure lifecycle policy
    lifecycle = aws.s3.BucketLifecycleConfiguration(
        f"{name}-state-bucket-lifecycle",
        bucket=bucket_id,
        rules=[
            aws.s3.BucketLifecycleConfigurationRuleArgs(
                id="state_lifecycle",
                status="Enabled",
                filter=aws.s3.BucketLifecycleConfigurationRuleFilterArgs(
                    prefix=""
                ),
                noncurrent_version_expiration=aws.s3.BucketLifecycleConfigurationRuleNoncurrentVersionExpirationArgs(
                    noncurrent_days=30
                ),
                abort_incomplete_multipart_upload=aws.s3.BucketLifecycleConfigurationRuleAbortIncompleteMultipartUploadArgs(
                    days_after_initiation=1
                )
            )
        ]
    )
    
    return {
        "versioning": versioning,
        "encryption": encryption,
        "public_access_block": public_access_block,
        "lifecycle": lifecycle
    }


def create_dynamodb_table(name: str, table_name: str, tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create DynamoDB table for state locking
    
    Args:
        name: Resource name prefix
        table_name: DynamoDB table name
        tags: Additional tags
        
    Returns:
        Dict with table resource and outputs
    """
    tags = tags or {}
    
    table = aws.dynamodb.Table(
        f"{name}-pulumi-state-lock-table",
        name=table_name,
        billing_mode="PAY_PER_REQUEST",  # Most cost-effective for infrequent use
        hash_key="LockID",
        attributes=[
            aws.dynamodb.TableAttributeArgs(
                name="LockID",
                type="S"
            )
        ],
        server_side_encryption=aws.dynamodb.TableServerSideEncryptionArgs(
            enabled=True
        ),
        point_in_time_recovery=aws.dynamodb.TablePointInTimeRecoveryArgs(
            enabled=False  # Keep costs minimal for dev environment
        ),
        tags={
            **tags,
            "Name": f"{name}-pulumi-state-lock",
            "Purpose": "Pulumi state locking",
            "Environment": "development",
            "Module": "state-storage"
        }
    )
    
    return {
        "table": table,
        "table_name": table.name,
        "table_arn": table.arn
    }


def get_backend_configuration_commands(bucket_name: str, aws_region: str) -> List[str]:
    """
    Get commands to configure Pulumi backend
    
    Args:
        bucket_name: S3 bucket name
        aws_region: AWS region
        
    Returns:
        List of configuration commands
    """
    return [
        "# Configure Pulumi to use S3 backend:",
        f"export PULUMI_BACKEND_URL=s3://{bucket_name}",
        "",
        "# Initialize Pulumi project with S3 backend:",
        "pulumi stack init dev --secrets-provider=awskms://alias/pulumi-secrets",
        "",
        "# Set AWS region:",
        f"pulumi config set aws:region {aws_region}",
        "",
        "# Deploy infrastructure:",
        "pulumi up",
        "",
        "# Note: Ensure AWS credentials are configured before running these commands"
    ]


def create_state_storage_resources(cluster_name: str,
                                  aws_region: str,
                                  tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create complete state storage infrastructure
    
    Args:
        cluster_name: Cluster name for resource naming
        aws_region: AWS region
        tags: Additional tags for all resources
        
    Returns:
        Dict with all state storage resources and outputs
    """
    tags = tags or {}
    
    # Generate names with region for global uniqueness
    bucket_name = f"{cluster_name}-pulumi-state-{aws_region}"
    dynamodb_table_name = f"{cluster_name}-pulumi-state-lock"
    
    # Create S3 bucket
    bucket_result = create_s3_bucket(cluster_name, bucket_name, tags)
    
    # Configure bucket settings
    bucket_config_result = configure_s3_bucket_settings(cluster_name, bucket_result["bucket_id"])
    
    # Create DynamoDB table
    table_result = create_dynamodb_table(cluster_name, dynamodb_table_name, tags)
    
    # Backend configuration
    backend_config = {
        "backend_type": "s3",
        "bucket": bucket_name,
        "region": aws_region,
        "dynamodb_table": dynamodb_table_name,
        "encrypt": "true"
    }
    
    return {
        "bucket_name_output": bucket_result["bucket_id"],
        "dynamodb_table_name_output": table_result["table_name"],
        "backend_config": backend_config,
        "configuration_commands": get_backend_configuration_commands(bucket_name, aws_region),
        # Keep references to resources for dependencies
        "_bucket": bucket_result["bucket"],
        "_table": table_result["table"],
        "_bucket_config": bucket_config_result
    }