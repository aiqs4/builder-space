"""
State Storage Module
Creates S3 bucket and DynamoDB table for Pulumi state backend
Simple function-based approach following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List


def create_state_storage_resources(cluster_name: str,
                                  aws_region: str,
                                  tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create state storage resources for Pulumi backend
    
    Args:
        cluster_name: Cluster name for resource naming
        aws_region: AWS region for resources
        tags: Additional tags for all resources
        
    Returns:
        Dict with state storage resources and outputs
    """
    tags = tags or {}
    
    # Generate bucket name with region for global uniqueness
    bucket_name = f"{cluster_name}-pulumi-state-{aws_region}"
    dynamodb_table_name = f"{cluster_name}-pulumi-state-lock"
    
    # S3 bucket for Pulumi state
    state_bucket = aws.s3.Bucket(
        f"{cluster_name}-pulumi-state-bucket",
        bucket=bucket_name,
        tags={
            **tags,
            "Name": f"{cluster_name}-pulumi-state",
            "Purpose": "Pulumi state storage",
            "Environment": "development",
            "Module": "state-storage"
        }
    )
    
    # S3 bucket versioning
    bucket_versioning = aws.s3.BucketVersioning(
        f"{cluster_name}-state-bucket-versioning",
        bucket=state_bucket.id,
        versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
            status="Enabled"
        )
    )
    
    # S3 bucket encryption
    bucket_encryption = aws.s3.BucketServerSideEncryptionConfiguration(
        f"{cluster_name}-state-bucket-encryption",
        bucket=state_bucket.id,
        rules=[
            aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="AES256"
                ),
                bucket_key_enabled=True
            )
        ]
    )
    
    # S3 bucket public access block
    bucket_public_access_block = aws.s3.BucketPublicAccessBlock(
        f"{cluster_name}-state-bucket-pab",
        bucket=state_bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True
    )
    
    # Lifecycle policy to minimize storage costs
    bucket_lifecycle = aws.s3.BucketLifecycleConfiguration(
        f"{cluster_name}-state-bucket-lifecycle",
        bucket=state_bucket.id,
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
    
    # DynamoDB table for state locking
    state_lock_table = aws.dynamodb.Table(
        f"{cluster_name}-pulumi-state-lock-table",
        name=dynamodb_table_name,
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
            "Name": f"{cluster_name}-pulumi-state-lock",
            "Purpose": "Pulumi state locking",
            "Environment": "development",
            "Module": "state-storage"
        }
    )
    
    # Generate backend configuration commands
    backend_config_commands = [
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
    
    return {
        "bucket_name": state_bucket.id,
        "dynamodb_table_name": state_lock_table.name,
        "backend_config": {
            "backend_type": "s3",
            "bucket": bucket_name,
            "region": aws_region,
            "dynamodb_table": dynamodb_table_name,
            "encrypt": "true"
        },
        "backend_configuration_commands": backend_config_commands,
    }