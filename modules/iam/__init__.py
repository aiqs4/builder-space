"""
IAM Module for EKS
Creates IAM roles and policies for EKS cluster and node groups
Simple function-based approach following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, Optional


def create_iam_resources(cluster_name: str,
                        use_existing_cluster_role: bool = False,
                        existing_cluster_role_name: str = "",
                        use_existing_node_role: bool = False,
                        existing_node_role_name: str = "",
                        tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create IAM resources for EKS cluster
    
    Args:
        cluster_name: EKS cluster name
        use_existing_cluster_role: Whether to use existing cluster role
        existing_cluster_role_name: Name of existing cluster role
        use_existing_node_role: Whether to use existing node role
        existing_node_role_name: Name of existing node role
        tags: Additional tags for all resources
        
    Returns:
        Dict with IAM resources and outputs
    """
    tags = tags or {}
    
    # Get current AWS account info
    current = aws.get_caller_identity()
    
    # EKS Cluster IAM Role
    if use_existing_cluster_role and existing_cluster_role_name:
        # Use existing cluster role
        cluster_role = aws.iam.get_role(name=existing_cluster_role_name)
        cluster_role_arn = pulumi.Output.from_input(cluster_role.arn)
        cluster_role_name = pulumi.Output.from_input(cluster_role.name)
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
        
        # Attach required policies to cluster role
        cluster_policy_attachment = aws.iam.RolePolicyAttachment(
            f"{cluster_name}-cluster-policy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
            role=cluster_role.name
        )
    
    # EKS Node Group IAM Role
    if use_existing_node_role and existing_node_role_name:
        # Use existing node role
        node_group_role = aws.iam.get_role(name=existing_node_role_name)
        node_group_role_arn = pulumi.Output.from_input(node_group_role.arn)
        node_group_role_name = pulumi.Output.from_input(node_group_role.name)
    else:
        # Create new node group role
        node_group_role = aws.iam.Role(
            f"{cluster_name}-ng-role",
            name=f"{cluster_name}-ng-role",
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
                "Name": f"{cluster_name}-node-group-role",
                "Module": "iam"
            }
        )
        node_group_role_arn = node_group_role.arn
        node_group_role_name = node_group_role.name
        
        # Attach required policies to node group role
        node_worker_policy = aws.iam.RolePolicyAttachment(
            f"{cluster_name}-node-worker-policy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
            role=node_group_role.name
        )
        
        node_cni_policy = aws.iam.RolePolicyAttachment(
            f"{cluster_name}-node-cni-policy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
            role=node_group_role.name
        )
        
        node_registry_policy = aws.iam.RolePolicyAttachment(
            f"{cluster_name}-node-registry-policy",
            policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
            role=node_group_role.name
        )
        
        # Additional policy for systems manager access (useful for debugging)
        node_ssm_policy = aws.iam.RolePolicyAttachment(
            f"{cluster_name}-node-ssm-policy",
            policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
            role=node_group_role.name
        )
        
        # Instance profile for node group
        node_instance_profile = aws.iam.InstanceProfile(
            f"{cluster_name}-node-instance-profile",
            name=f"{cluster_name}-node-instance-profile",
            role=node_group_role.name,
            tags={
                **tags,
                "Name": f"{cluster_name}-node-instance-profile",
                "Module": "iam"
            }
        )
    
    return {
        "cluster_role_arn": cluster_role_arn,
        "cluster_role_name": cluster_role_name,
        "node_group_role_arn": node_group_role_arn,
        "node_group_role_name": node_group_role_name,
    }