"""
IAM Module Functions
Creates IAM roles and policies for EKS cluster and node groups
Refactored to function-based style following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, Optional


def create_cluster_role(name: str, tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create IAM role for EKS cluster
    
    Args:
        name: Role name
        tags: Additional tags
        
    Returns:
        Dict with role resource and outputs
    """
    tags = tags or {}
    
    role = aws.iam.Role(
        f"{name}-cluster-role",
        name=f"{name}-cluster-role",
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
            "Name": f"{name}-cluster-role",
            "Module": "iam"
        }
    )
    
    # Attach required policy
    policy_attachment = aws.iam.RolePolicyAttachment(
        f"{name}-cluster-policy",
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
        role=role.name
    )
    
    return {
        "role": role,
        "policy_attachment": policy_attachment,
        "role_arn": role.arn,
        "role_name": role.name
    }


def create_node_group_role(name: str, tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create IAM role for EKS node group
    
    Args:
        name: Role name prefix
        tags: Additional tags
        
    Returns:
        Dict with role resource and outputs
    """
    tags = tags or {}
    
    role = aws.iam.Role(
        f"{name}-ng-role",
        name=f"{name}-ng-role",
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
            "Name": f"{name}-node-group-role",
            "Module": "iam"
        }
    )
    
    # Attach required policies
    policies = [
        ("worker", "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"),
        ("cni", "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"),
        ("registry", "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"),
        ("ssm", "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore")
    ]
    
    policy_attachments = {}
    for policy_name, policy_arn in policies:
        attachment = aws.iam.RolePolicyAttachment(
            f"{name}-node-{policy_name}-policy",
            policy_arn=policy_arn,
            role=role.name
        )
        policy_attachments[f"{policy_name}_policy"] = attachment
    
    # Instance profile for node group
    instance_profile = aws.iam.InstanceProfile(
        f"{name}-node-instance-profile",
        name=f"{name}-node-instance-profile",
        role=role.name,
        tags={
            **tags,
            "Name": f"{name}-node-instance-profile",
            "Module": "iam"
        }
    )
    
    return {
        "role": role,
        "policy_attachments": policy_attachments,
        "instance_profile": instance_profile,
        "role_arn": role.arn,
        "role_name": role.name
    }


def get_existing_role(role_name: str) -> Dict[str, any]:
    """
    Get existing IAM role
    
    Args:
        role_name: Name of existing role
        
    Returns:
        Dict with role information
    """
    role = aws.iam.get_role(name=role_name)
    
    return {
        "role": role,
        "role_arn": pulumi.Output.from_input(role.arn),
        "role_name": pulumi.Output.from_input(role.name)
    }


def create_iam_resources(cluster_name: str,
                        use_existing_cluster_role: bool = False,
                        existing_cluster_role_name: str = "",
                        use_existing_node_role: bool = False,
                        existing_node_role_name: str = "",
                        tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create or reference IAM resources for EKS
    
    Args:
        cluster_name: EKS cluster name
        use_existing_cluster_role: Use existing cluster role
        existing_cluster_role_name: Name of existing cluster role
        use_existing_node_role: Use existing node role
        existing_node_role_name: Name of existing node role
        tags: Additional tags
        
    Returns:
        Dict with all IAM resources and outputs
    """
    tags = tags or {}
    
    # Handle cluster role
    if use_existing_cluster_role and existing_cluster_role_name:
        cluster_role_result = get_existing_role(existing_cluster_role_name)
    else:
        cluster_role_result = create_cluster_role(cluster_name, tags)
    
    # Handle node group role
    if use_existing_node_role and existing_node_role_name:
        node_role_result = get_existing_role(existing_node_role_name)
    else:
        node_role_result = create_node_group_role(cluster_name, tags)
    
    return {
        "cluster_role_arn": cluster_role_result["role_arn"],
        "cluster_role_name": cluster_role_result["role_name"],
        "node_group_role_arn": node_role_result["role_arn"],
        "node_group_role_name": node_role_result["role_name"],
        # Keep references to resources for dependencies
        "_cluster_role": cluster_role_result.get("role"),
        "_node_role": node_role_result.get("role"),
        "_cluster_policy_attachment": cluster_role_result.get("policy_attachment"),
        "_node_policy_attachments": node_role_result.get("policy_attachments"),
        "_instance_profile": node_role_result.get("instance_profile")
    }