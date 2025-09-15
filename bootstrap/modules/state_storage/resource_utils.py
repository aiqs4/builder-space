"""
Resource utilities for handling existing AWS resources in Pulumi
"""

import pulumi
import pulumi_aws as aws
from typing import Optional, Dict, Any
import time
import logging


def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Retry a function with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
    
    Returns:
        Result of the function call
    
    Raises:
        Exception: Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                pulumi.log.warn(f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                pulumi.log.error(f"All {max_retries + 1} attempts failed")
    
    raise last_exception


def check_s3_bucket_exists(bucket_name: str) -> bool:
    """
    Check if S3 bucket exists and is accessible
    
    Args:
        bucket_name: Name of the S3 bucket
        
    Returns:
        True if bucket exists and is accessible, False otherwise
    """
    try:
        # Use Pulumi's AWS provider to check if bucket exists
        bucket_check = aws.s3.get_bucket_output(bucket=bucket_name)
        return True
    except Exception:
        return False


def check_dynamodb_table_exists(table_name: str) -> bool:
    """
    Check if DynamoDB table exists and is accessible
    
    Args:
        table_name: Name of the DynamoDB table
        
    Returns:
        True if table exists and is accessible, False otherwise
    """
    try:
        # Use Pulumi's AWS provider to check if table exists
        table_check = aws.dynamodb.get_table_output(name=table_name)
        return True
    except Exception:
        return False


def create_or_import_s3_bucket(
    resource_name: str,
    bucket_name: str,
    tags: Dict[str, str] = None,
    opts: pulumi.ResourceOptions = None
) -> aws.s3.Bucket:
    """
    Create a new S3 bucket or import existing one
    
    Args:
        resource_name: Pulumi resource name
        bucket_name: S3 bucket name
        tags: Tags to apply to the bucket
        opts: Pulumi resource options
        
    Returns:
        S3 Bucket resource
    """
    # Check if bucket exists
    if check_s3_bucket_exists(bucket_name):
        pulumi.log.info(f"S3 bucket {bucket_name} already exists, importing...")
        # Import existing bucket
        import_opts = pulumi.ResourceOptions(
            import_=bucket_name,
            **(opts.__dict__ if opts else {})
        )
        return aws.s3.Bucket(
            resource_name,
            bucket=bucket_name,
            tags=tags,
            opts=import_opts
        )
    else:
        pulumi.log.info(f"Creating new S3 bucket {bucket_name}...")
        # Create new bucket
        return aws.s3.Bucket(
            resource_name,
            bucket=bucket_name,
            tags=tags,
            opts=opts
        )


def create_or_import_dynamodb_table(
    resource_name: str,
    table_name: str,
    billing_mode: str = "PAY_PER_REQUEST",
    hash_key: str = "LockID",
    attributes: list = None,
    tags: Dict[str, str] = None,
    opts: pulumi.ResourceOptions = None
) -> aws.dynamodb.Table:
    """
    Create a new DynamoDB table or import existing one
    
    Args:
        resource_name: Pulumi resource name
        table_name: DynamoDB table name
        billing_mode: DynamoDB billing mode
        hash_key: Primary key for the table
        attributes: Table attributes
        tags: Tags to apply to the table
        opts: Pulumi resource options
        
    Returns:
        DynamoDB Table resource
    """
    if attributes is None:
        attributes = [
            aws.dynamodb.TableAttributeArgs(
                name=hash_key,
                type="S"
            )
        ]
    
    # Check if table exists
    if check_dynamodb_table_exists(table_name):
        pulumi.log.info(f"DynamoDB table {table_name} already exists, importing...")
        # Import existing table
        import_opts = pulumi.ResourceOptions(
            import_=table_name,
            **(opts.__dict__ if opts else {})
        )
        return aws.dynamodb.Table(
            resource_name,
            name=table_name,
            billing_mode=billing_mode,
            hash_key=hash_key,
            attributes=attributes,
            tags=tags,
            opts=import_opts
        )
    else:
        pulumi.log.info(f"Creating new DynamoDB table {table_name}...")
        # Create new table
        return aws.dynamodb.Table(
            resource_name,
            name=table_name,
            billing_mode=billing_mode,
            hash_key=hash_key,
            attributes=attributes,
            tags=tags,
            opts=opts
        )


def handle_aws_error(error: Exception) -> bool:
    """
    Check if AWS error should be handled gracefully
    
    Args:
        error: Exception from AWS operation
        
    Returns:
        True if error should be handled gracefully, False otherwise
    """
    error_str = str(error).lower()
    
    # Common errors that indicate resource already exists
    graceful_errors = [
        "bucketalreadyownedbyyou",
        "bucketalreadyexists", 
        "resourceinuseexception",
        "table already exists",
        "already exists"
    ]
    
    return any(graceful_error in error_str for graceful_error in graceful_errors)


def validate_s3_bucket_configuration(bucket_name: str) -> Dict[str, Any]:
    """
    Validate S3 bucket configuration and return current settings
    
    Args:
        bucket_name: Name of the S3 bucket
        
    Returns:
        Dictionary with bucket configuration details
    """
    try:
        bucket = aws.s3.get_bucket_output(bucket=bucket_name)
        
        # Check versioning
        try:
            versioning = aws.s3.get_bucket_versioning_output(bucket=bucket_name)
            versioning_enabled = versioning.status == "Enabled"
        except:
            versioning_enabled = False
            
        # Check encryption
        try:
            encryption = aws.s3.get_bucket_server_side_encryption_configuration_output(bucket=bucket_name)
            encryption_enabled = len(encryption.rules) > 0
        except:
            encryption_enabled = False
            
        # Check public access block
        try:
            pab = aws.s3.get_bucket_public_access_block_output(bucket=bucket_name)
            public_access_blocked = (
                pab.block_public_acls and 
                pab.block_public_policy and
                pab.ignore_public_acls and 
                pab.restrict_public_buckets
            )
        except:
            public_access_blocked = False
        
        return {
            "exists": True,
            "versioning_enabled": versioning_enabled,
            "encryption_enabled": encryption_enabled,
            "public_access_blocked": public_access_blocked,
            "bucket": bucket
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }


def validate_dynamodb_table_configuration(table_name: str) -> Dict[str, Any]:
    """
    Validate DynamoDB table configuration and return current settings
    
    Args:
        table_name: Name of the DynamoDB table
        
    Returns:
        Dictionary with table configuration details
    """
    try:
        table = aws.dynamodb.get_table_output(name=table_name)
        
        return {
            "exists": True,
            "billing_mode": table.billing_mode,
            "hash_key": table.hash_key,
            "table": table
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }