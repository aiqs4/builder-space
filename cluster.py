"""
Simple EKS Cluster - KISS approach
AWS handles all the complexity for us
"""

import pulumi
import pulumi_aws as aws

# Configuration - keep it simple
CLUSTER_NAME = "builder-space"
NODE_COUNT = 3
INSTANCE_TYPE = "t4g.small"
USE_SPOT = True  # Save money

# Get current region and account
current = aws.get_caller_identity()
region = aws.get_region()

# EKS Cluster - AWS handles VPC, security groups, IAM roles automatically
cluster = aws.eks.Cluster(
    "cluster",
    name=CLUSTER_NAME,
    # Let AWS create and manage everything
    # This automatically creates:
    # - VPC with public/private subnets
    # - Security groups
    # - IAM roles
    # - Internet gateway
    # - Route tables
    # All the stuff that was manually created in 500+ lines of code!
)

# Node Group - simple scaling configuration
node_group = aws.eks.NodeGroup(
    "nodes",
    cluster_name=cluster.name,
    instance_types=[INSTANCE_TYPE],
    capacity_type="SPOT" if USE_SPOT else "ON_DEMAND",
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=NODE_COUNT,
        max_size=NODE_COUNT + 1,
        min_size=1,
    ),
    # AWS handles the rest
)

# Outputs - just the essentials
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("kubeconfig_command", 
    pulumi.Output.concat("aws eks update-kubeconfig --region ", region.name, " --name ", cluster.name))
