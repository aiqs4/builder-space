"""
State Storage Bootstrap - Simple Pulumi project for state storage
Creates S3 bucket and DynamoDB table for Pulumi state backend
"""

import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
cluster_name = config.get("cluster_name") or "builder-space"
aws_region = config.get("aws:region") or "af-south-1"

# Resource names
bucket_name = f"{cluster_name}-pulumi-state-{aws_region}"
dynamodb_table_name = f"{cluster_name}-pulumi-state-lock"

# Tags
tags = {
    "Project": "builder-space-eks",
    "Environment": "development",
    "ManagedBy": "pulumi",
    "Purpose": "state-storage-bootstrap"
}

# S3 Bucket with all configurations
state_bucket = aws.s3.Bucket(
    f"{cluster_name}-pulumi-state-bucket",
    bucket=bucket_name,

    tags={**tags, "Name": f"{cluster_name}-pulumi-state"}
)

# S3 configurations
aws.s3.BucketVersioning(
    f"{cluster_name}-state-bucket-versioning",
    bucket=state_bucket.id,
    versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(status="Enabled")
)

aws.s3.BucketServerSideEncryptionConfiguration(
    f"{cluster_name}-state-bucket-encryption",
    bucket=state_bucket.id,
    rules=[aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
        apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
            sse_algorithm="AES256"
        ),
        bucket_key_enabled=True
    )]
)

aws.s3.BucketPublicAccessBlock(
    f"{cluster_name}-state-bucket-pab",
    bucket=state_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True
)

aws.s3.BucketLifecycleConfiguration(
    f"{cluster_name}-state-bucket-lifecycle",
    bucket=state_bucket.id,
    rules=[aws.s3.BucketLifecycleConfigurationRuleArgs(
        id="state_lifecycle",
        status="Enabled",
        filter=aws.s3.BucketLifecycleConfigurationRuleFilterArgs(prefix=""),
        noncurrent_version_expiration=aws.s3.BucketLifecycleConfigurationRuleNoncurrentVersionExpirationArgs(
            noncurrent_days=30
        ),
        abort_incomplete_multipart_upload=aws.s3.BucketLifecycleConfigurationRuleAbortIncompleteMultipartUploadArgs(
            days_after_initiation=1
        )
    )]
)

# KMS Key
kms_key = aws.kms.Key(
    f"{cluster_name}-pulumi-secrets-key",
    description=f"Pulumi secrets encryption key for {cluster_name}",
    key_usage="ENCRYPT_DECRYPT",
    tags={**tags, "Name": f"{cluster_name}-pulumi-secrets"}
)

# KMS Alias
aws.kms.Alias(
    f"{cluster_name}-pulumi-secrets-alias",
    name=f"alias/{cluster_name}-pulumi-secrets",
    target_key_id=kms_key.key_id
)

# DynamoDB Table
state_lock_table = aws.dynamodb.Table(
    f"{cluster_name}-pulumi-state-lock-table",
    name=dynamodb_table_name,
    billing_mode="PAY_PER_REQUEST",
    hash_key="LockID",
    attributes=[aws.dynamodb.TableAttributeArgs(name="LockID", type="S")],
    tags={**tags, "Name": f"{cluster_name}-pulumi-state-lock"}
)

# Exports
pulumi.export("bucket_name", state_bucket.id)
pulumi.export("dynamodb_table_name", state_lock_table.name)
pulumi.export("kms_key_arn", kms_key.arn)
pulumi.export("kms_key_id", kms_key.key_id)

pulumi.export("backend_config", {
    "backend_type": "s3",
    "bucket": bucket_name,
    "region": aws_region,
    "dynamodb_table": dynamodb_table_name,
    "encrypt": "true"
})

pulumi.export("backend_configuration_commands", [
    f"export PULUMI_BACKEND_URL=s3://{bucket_name}",
    f"pulumi config set aws:region {aws_region}",
    "pulumi up"
])