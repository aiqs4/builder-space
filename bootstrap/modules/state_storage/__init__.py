"""
State Storage Module
Creates S3 bucket and DynamoDB table for Pulumi state backend
Enhanced with idempotency and error handling
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List
from .resource_utils import (
    create_or_import_s3_bucket,
    create_or_import_dynamodb_table,
    validate_s3_bucket_configuration,
    validate_dynamodb_table_configuration,
    retry_with_backoff,
    handle_aws_error
)

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
        
        # Create S3 bucket with idempotency
        pulumi.log.info(f"Setting up S3 bucket for state storage: {self.bucket_name}")
        
        def create_bucket():
            return create_or_import_s3_bucket(
                f"{cluster_name}-pulumi-state-bucket",
                self.bucket_name,
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-pulumi-state",
                    "Purpose": "Pulumi state storage",
                    "Environment": "development",
                    "Module": "state-storage"
                }
            )
        
        self.state_bucket = retry_with_backoff(create_bucket, max_retries=3)
        
        # S3 bucket versioning
        self.bucket_versioning = aws.s3.BucketVersioning(
            f"{cluster_name}-state-bucket-versioning",
            bucket=self.state_bucket.id,
            versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
                status="Enabled"
            ),
            opts=pulumi.ResourceOptions(
                depends_on=[self.state_bucket]
            )
        )
        
        # S3 bucket encryption
        self.bucket_encryption = aws.s3.BucketServerSideEncryptionConfiguration(
            f"{cluster_name}-state-bucket-encryption",
            bucket=self.state_bucket.id,
            rules=[
                aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                    apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                        sse_algorithm="AES256"
                    ),
                    bucket_key_enabled=True
                )
            ],
            opts=pulumi.ResourceOptions(
                depends_on=[self.state_bucket]
            )
        )
        
        # S3 bucket public access block
        self.bucket_public_access_block = aws.s3.BucketPublicAccessBlock(
            f"{cluster_name}-state-bucket-pab",
            bucket=self.state_bucket.id,
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
            opts=pulumi.ResourceOptions(
                depends_on=[self.state_bucket]
            )
        )
        
        # Lifecycle policy to minimize storage costs
        self.bucket_lifecycle = aws.s3.BucketLifecycleConfiguration(
            f"{cluster_name}-state-bucket-lifecycle",
            bucket=self.state_bucket.id,
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
            ],
            opts=pulumi.ResourceOptions(
                depends_on=[self.state_bucket]
            )
        )
        
        # Create DynamoDB table with idempotency
        pulumi.log.info(f"Setting up DynamoDB table for state locking: {self.dynamodb_table_name}")
        
        def create_table():
            return create_or_import_dynamodb_table(
                f"{cluster_name}-pulumi-state-lock-table",
                self.dynamodb_table_name,
                billing_mode="PAY_PER_REQUEST",  # Most cost-effective for infrequent use
                hash_key="LockID",
                attributes=[
                    aws.dynamodb.TableAttributeArgs(
                        name="LockID",
                        type="S"
                    )
                ],
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-pulumi-state-lock",
                    "Purpose": "Pulumi state locking",
                    "Environment": "development",
                    "Module": "state-storage"
                }
            )
        
        self.state_lock_table = retry_with_backoff(create_table, max_retries=3)
        
        # Configure additional table settings if created/imported successfully
        if hasattr(self.state_lock_table, 'name'):
            # Add server side encryption
            try:
                self.table_encryption = aws.dynamodb.Table(
                    f"{cluster_name}-pulumi-state-lock-table-config",
                    name=self.state_lock_table.name,
                    server_side_encryption=aws.dynamodb.TableServerSideEncryptionArgs(
                        enabled=True
                    ),
                    point_in_time_recovery=aws.dynamodb.TablePointInTimeRecoveryArgs(
                        enabled=False  # Keep costs minimal for dev environment
                    ),
                    opts=pulumi.ResourceOptions(
                        depends_on=[self.state_lock_table],
                        import_=self.state_lock_table.name if hasattr(self.state_lock_table, 'name') else None
                    )
                )
            except Exception as e:
                pulumi.log.warn(f"Could not configure additional table settings: {e}")
        
        # Validate resources post-creation
        self._validate_resources()
    
    def _validate_resources(self):
        """Validate that resources are created and configured correctly"""
        try:
            # Validate S3 bucket
            bucket_validation = validate_s3_bucket_configuration(self.bucket_name)
            if bucket_validation["exists"]:
                pulumi.log.info(f"✅ S3 bucket {self.bucket_name} validated successfully")
                if not bucket_validation.get("versioning_enabled", False):
                    pulumi.log.warn(f"⚠️ Versioning not enabled on bucket {self.bucket_name}")
                if not bucket_validation.get("encryption_enabled", False):
                    pulumi.log.warn(f"⚠️ Encryption not enabled on bucket {self.bucket_name}")
                if not bucket_validation.get("public_access_blocked", False):
                    pulumi.log.warn(f"⚠️ Public access not blocked on bucket {self.bucket_name}")
            else:
                pulumi.log.error(f"❌ S3 bucket {self.bucket_name} validation failed")
            
            # Validate DynamoDB table
            table_validation = validate_dynamodb_table_configuration(self.dynamodb_table_name)
            if table_validation["exists"]:
                pulumi.log.info(f"✅ DynamoDB table {self.dynamodb_table_name} validated successfully")
            else:
                pulumi.log.error(f"❌ DynamoDB table {self.dynamodb_table_name} validation failed")
                
        except Exception as e:
            pulumi.log.warn(f"Resource validation failed: {e}")
    
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
    
    def get_validation_commands(self) -> List[str]:
        """Get commands to validate the state storage setup"""
        return [
            "# Validate S3 bucket:",
            f"aws s3 ls s3://{self.bucket_name}/",
            "",
            "# Validate DynamoDB table:",
            f"aws dynamodb describe-table --table-name {self.dynamodb_table_name}",
            "",
            "# Test Pulumi backend connectivity:",
            "pulumi stack ls",
            "",
            "# Refresh Pulumi state:",
            "pulumi refresh"
        ]