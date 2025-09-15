"""
State Storage Module
Pure declarative infrastructure - no classes or functions
"""

import pulumi
import pulumi_aws as aws
from config import get_config

# Get configuration
config = get_config()
cluster_name = config.cluster_name
aws_region = config.aws_region
tags = config.common_tags

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

# DynamoDB table for state locking
state_lock_table = aws.dynamodb.Table(
    f"{cluster_name}-pulumi-state-lock-table",
    name=dynamodb_table_name,
    billing_mode="PAY_PER_REQUEST",
    hash_key="LockID",
    attributes=[
        aws.dynamodb.TableAttributeArgs(
            name="LockID",
            type="S"
        )
    ],
    tags={
        **tags,
        "Name": f"{cluster_name}-pulumi-state-lock",
        "Purpose": "Pulumi state locking",
        "Environment": "development",
        "Module": "state-storage"
    }
)

# Export information for setup
state_bucket_name = state_bucket.bucket
state_bucket_arn = state_bucket.arn
state_lock_table_name = state_lock_table.name
state_lock_table_arn = state_lock_table.arn