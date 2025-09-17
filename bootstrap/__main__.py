"""
State Storage Bootstrap - Simple Pulumi project for state storage
Creates S3 bucket and DynamoDB table for Pulumi state backend
"""

import pulumi
import pulumi_aws as aws

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

# Generate names with region for global uniqueness
bucket_name = f"{cluster_name}-pulumi-state-{aws_region}"
dynamodb_table_name = f"{cluster_name}-pulumi-state-lock"

# Create S3 bucket for state storage
state_bucket = aws.s3.Bucket(
    f"{cluster_name}-pulumi-state-bucket",
    bucket=bucket_name,
    tags={
        **tags,
        "Name": f"{cluster_name}-pulumi-state",
        "Purpose": "Pulumi state storage"
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

# Create KMS key for Pulumi secrets encryption
kms_key = aws.kms.Key(
    f"{cluster_name}-pulumi-secrets-key",
    description=f"Pulumi secrets encryption key for {cluster_name}",
    key_usage="ENCRYPT_DECRYPT",
    tags={
        **tags,
        "Name": f"{cluster_name}-pulumi-secrets",
        "Purpose": "Pulumi secrets encryption"
    }
)

# Create KMS alias for easier reference
kms_alias = aws.kms.Alias(
    f"{cluster_name}-pulumi-secrets-alias",
    name=f"alias/{cluster_name}-pulumi-secrets",
    target_key_id=kms_key.key_id
)

# Create DynamoDB table for state locking
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
        "Purpose": "Pulumi state locking"
    }
)

# Export outputs
pulumi.export("bucket_name", state_bucket.id)
pulumi.export("dynamodb_table_name", state_lock_table.name)
pulumi.export("kms_key_arn", kms_key.arn)
pulumi.export("kms_key_id", kms_key.key_id)

# Export backend configuration
pulumi.export("backend_config", {
    "backend_type": "s3",
    "bucket": bucket_name,
    "region": aws_region,
    "dynamodb_table": dynamodb_table_name,
    "encrypt": "true"
})

# Export configuration commands
pulumi.export("backend_configuration_commands", [
    "# Configure Pulumi to use S3 backend:",
    f"export PULUMI_BACKEND_URL=s3://{bucket_name}",
    "",
    "# Initialize Pulumi project with S3 backend:",
    "# Note: Replace <KMS_KEY_ARN> with the actual KMS key ARN from above",
    "# pulumi stack init dev --secrets-provider=awskms://<KMS_KEY_ARN>",
    "",
    "# Set AWS region:",
    f"pulumi config set aws:region {aws_region}",
    "",
    "# Deploy infrastructure:",
    "pulumi up"
])

pulumi.log.info("✅ State storage bootstrap completed successfully")