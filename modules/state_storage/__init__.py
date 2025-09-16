"""
State Storage Module
Pure declarative infrastructure - no classes or functions
This module is deprecated. State storage is now managed by the bootstrap stack.
Resources are referenced but not created here to avoid interference.
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

# NOTE: State storage resources are created by the bootstrap stack.
# This module only defines the expected resource names for reference.
# Do NOT create actual resources here to avoid conflicts.

# Export expected resource names for compatibility
# These are the names that the bootstrap stack creates
state_bucket_name = bucket_name
state_lock_table_name = dynamodb_table_name

# For backward compatibility, export empty ARNs since resources aren't created here
state_bucket_arn = ""
state_lock_table_arn = ""