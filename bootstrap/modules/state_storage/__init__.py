"""
State Storage Module
Creates S3 bucket and DynamoDB table for Pulumi state backend
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List

class StateStorageResources:
    """State storage resources for Pulumi backend"""
    
    def __init__(self,
                 cluster_name: str,
                 aws_region: str,
                 tags: Dict[str, str] = None):
        
        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.tags = tags or {}
        
        # Generate bucket name with region for global uniqueness
        self.bucket_name = f"{cluster_name}-pulumi-state-{aws_region}"
        self.dynamodb_table_name = f"{cluster_name}-pulumi-state-lock"
        
        # S3 bucket for Pulumi state
        self.state_bucket = aws.s3.Bucket(
            f"{cluster_name}-pulumi-state-bucket",
            bucket=self.bucket_name,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-pulumi-state",
                "Purpose": "Pulumi state storage",
                "Environment": "development",
                "Module": "state-storage"
            }
        )
        
        # S3 bucket versioning
        self.bucket_versioning = aws.s3.BucketVersioningV2(
            f"{cluster_name}-state-bucket-versioning",
            bucket=self.state_bucket.id,
            versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(
                status="Enabled"
            )
        )
        
        # S3 bucket encryption
        self.bucket_encryption = aws.s3.BucketServerSideEncryptionConfigurationV2(
            f"{cluster_name}-state-bucket-encryption",
            bucket=self.state_bucket.id,
            rules=[
                aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                    apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                        sse_algorithm="AES256"
                    ),
                    bucket_key_enabled=True
                )
            ]
        )
        
        # S3 bucket public access block
        self.bucket_public_access_block = aws.s3.BucketPublicAccessBlock(
            f"{cluster_name}-state-bucket-pab",
            bucket=self.state_bucket.id,
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True
        )
        
        # Lifecycle policy to minimize storage costs
        self.bucket_lifecycle = aws.s3.BucketLifecycleConfigurationV2(
            f"{cluster_name}-state-bucket-lifecycle",
            bucket=self.state_bucket.id,
            rules=[
                aws.s3.BucketLifecycleConfigurationV2RuleArgs(
                    id="state_lifecycle",
                    status="Enabled",
                    filter=aws.s3.BucketLifecycleConfigurationV2RuleFilterArgs(
                        prefix=""
                    ),
                    noncurrent_version_expiration=aws.s3.BucketLifecycleConfigurationV2RuleNoncurrentVersionExpirationArgs(
                        noncurrent_days=30
                    ),
                    abort_incomplete_multipart_upload=aws.s3.BucketLifecycleConfigurationV2RuleAbortIncompleteMultipartUploadArgs(
                        days_after_initiation=1
                    )
                )
            ]
        )
        
        # DynamoDB table for state locking
        self.state_lock_table = aws.dynamodb.Table(
            f"{cluster_name}-pulumi-state-lock-table",
            name=self.dynamodb_table_name,
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
                **self.tags,
                "Name": f"{cluster_name}-pulumi-state-lock",
                "Purpose": "Pulumi state locking",
                "Environment": "development",
                "Module": "state-storage"
            }
        )
    
    @property
    def bucket_name_output(self) -> pulumi.Output[str]:
        """Get S3 bucket name"""
        return self.state_bucket.id
    
    @property
    def dynamodb_table_name_output(self) -> pulumi.Output[str]:
        """Get DynamoDB table name"""
        return self.state_lock_table.name
    
    @property
    def backend_config(self) -> Dict[str, str]:
        """Get backend configuration for Pulumi"""
        return {
            "backend_type": "s3",
            "bucket": self.bucket_name,
            "region": self.aws_region,
            "dynamodb_table": self.dynamodb_table_name,
            "encrypt": "true"
        }
    
    def get_backend_configuration_commands(self) -> List[str]:
        """Get commands to configure Pulumi backend"""
        return [
            "# Configure Pulumi to use S3 backend:",
            f"export PULUMI_BACKEND_URL=s3://{self.bucket_name}",
            "",
            "# Initialize Pulumi project with S3 backend:",
            "pulumi stack init dev --secrets-provider=awskms://alias/pulumi-secrets",
            "",
            "# Set AWS region:",
            f"pulumi config set aws:region {self.aws_region}",
            "",
            "# Deploy infrastructure:",
            "pulumi up",
            "",
            "# Note: Ensure AWS credentials are configured before running these commands"
        ]