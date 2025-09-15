"""
IAM Module for EKS
Pure declarative infrastructure - no classes or functions
"""

import pulumi
import pulumi_aws as aws
from config import get_config

# Get configuration
config = get_config()
cluster_name = config.cluster_name
tags = config.common_tags

# Get current AWS account info
current = aws.get_caller_identity()

# EKS Cluster IAM Role
if config.use_existing_cluster_role and config.existing_cluster_role_name:
    # Use existing cluster role
    cluster_role_data = aws.iam.get_role(name=config.existing_cluster_role_name)
    cluster_role_arn = pulumi.Output.from_input(cluster_role_data.arn)
    cluster_role_name = pulumi.Output.from_input(cluster_role_data.name)
else:
    # Create new cluster role
    cluster_role = aws.iam.Role(
        f"{cluster_name}-cluster-role",
        name=f"{cluster_name}-cluster-role",
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "eks.amazonaws.com"
                    }
                }
            ]
        }""",
        tags={
            **tags,
            "Name": f"{cluster_name}-cluster-role",
            "Module": "iam"
        }
    )
    cluster_role_arn = cluster_role.arn
    cluster_role_name = cluster_role.name
    
    # Attach AWS managed policies to cluster role
    cluster_policy_attachment = aws.iam.RolePolicyAttachment(
        f"{cluster_name}-cluster-policy",
        role=cluster_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
    )

# EKS Node Group IAM Role
if config.use_existing_node_role and config.existing_node_role_name:
    # Use existing node role
    node_role_data = aws.iam.get_role(name=config.existing_node_role_name)
    node_group_role_arn = pulumi.Output.from_input(node_role_data.arn)
    node_group_role_name = pulumi.Output.from_input(node_role_data.name)
else:
    # Create new node role
    node_role = aws.iam.Role(
        f"{cluster_name}-node-role",
        name=f"{cluster_name}-node-role",
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    }
                }
            ]
        }""",
        tags={
            **tags,
            "Name": f"{cluster_name}-node-role",
            "Module": "iam"
        }
    )
    node_group_role_arn = node_role.arn
    node_group_role_name = node_role.name
    
    # Attach AWS managed policies to node role
    node_worker_policy = aws.iam.RolePolicyAttachment(
        f"{cluster_name}-node-worker-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
    )
    
    node_cni_policy = aws.iam.RolePolicyAttachment(
        f"{cluster_name}-node-cni-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
    )
    
    node_registry_policy = aws.iam.RolePolicyAttachment(
        f"{cluster_name}-node-registry-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
    )
    
    node_ssm_policy = aws.iam.RolePolicyAttachment(
        f"{cluster_name}-node-ssm-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    )
    
    # Create instance profile for node group
    node_instance_profile = aws.iam.InstanceProfile(
        f"{cluster_name}-node-instance-profile",
        name=f"{cluster_name}-node-instance-profile",
        role=node_role.name,
        tags={
            **tags,
            "Name": f"{cluster_name}-node-instance-profile",
            "Module": "iam"
        }
    )