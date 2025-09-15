"""
IAM Module for EKS
Creates IAM roles and policies for EKS cluster and node groups
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, Optional

class IAMResources:
    """IAM resources for EKS cluster"""
    
    def __init__(self,
                 cluster_name: str,
                 use_existing_cluster_role: bool = False,
                 existing_cluster_role_name: str = "",
                 use_existing_node_role: bool = False,
                 existing_node_role_name: str = "",
                 tags: Dict[str, str] = None):
        
        self.cluster_name = cluster_name
        self.tags = tags or {}
        
        # Get current AWS account info
        self.current = aws.get_caller_identity()
        
        # EKS Cluster IAM Role
        if use_existing_cluster_role and existing_cluster_role_name:
            # Use existing cluster role
            self.cluster_role = aws.iam.get_role(name=existing_cluster_role_name)
            self._cluster_role_arn = pulumi.Output.from_input(self.cluster_role.arn)
            self._cluster_role_name = pulumi.Output.from_input(self.cluster_role.name)
        else:
            # Create new cluster role
            self.cluster_role = aws.iam.Role(
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
                    **self.tags,
                    "Name": f"{cluster_name}-cluster-role",
                    "Module": "iam"
                }
            )
            self._cluster_role_arn = self.cluster_role.arn
            self._cluster_role_name = self.cluster_role.name
            
            # Attach required policies to cluster role
            self.cluster_policy_attachment = aws.iam.RolePolicyAttachment(
                f"{cluster_name}-cluster-policy",
                policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
                role=self.cluster_role.name
            )
        
        # EKS Node Group IAM Role
        if use_existing_node_role and existing_node_role_name:
            # Use existing node role
            self.node_group_role = aws.iam.get_role(name=existing_node_role_name)
            self._node_group_role_arn = pulumi.Output.from_input(self.node_group_role.arn)
            self._node_group_role_name = pulumi.Output.from_input(self.node_group_role.name)
        else:
            # Create new node group role
            self.node_group_role = aws.iam.Role(
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
                    **self.tags,
                    "Name": f"{cluster_name}-node-group-role",
                    "Module": "iam"
                }
            )
            self._node_group_role_arn = self.node_group_role.arn
            self._node_group_role_name = self.node_group_role.name
            
            # Attach required policies to node group role
            self.node_worker_policy = aws.iam.RolePolicyAttachment(
                f"{cluster_name}-node-worker-policy",
                policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
                role=self.node_group_role.name
            )
            
            self.node_cni_policy = aws.iam.RolePolicyAttachment(
                f"{cluster_name}-node-cni-policy",
                policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
                role=self.node_group_role.name
            )
            
            self.node_registry_policy = aws.iam.RolePolicyAttachment(
                f"{cluster_name}-node-registry-policy",
                policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
                role=self.node_group_role.name
            )
            
            # Additional policy for systems manager access (useful for debugging)
            self.node_ssm_policy = aws.iam.RolePolicyAttachment(
                f"{cluster_name}-node-ssm-policy",
                policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
                role=self.node_group_role.name
            )
            
            # Instance profile for node group
            self.node_instance_profile = aws.iam.InstanceProfile(
                f"{cluster_name}-node-instance-profile",
                name=f"{cluster_name}-node-instance-profile",
                role=self.node_group_role.name,
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-node-instance-profile",
                    "Module": "iam"
                }
            )
    
    @property
    def cluster_role_arn(self) -> pulumi.Output[str]:
        """Get cluster role ARN"""
        return self._cluster_role_arn
    
    @property
    def cluster_role_name(self) -> pulumi.Output[str]:
        """Get cluster role name"""
        return self._cluster_role_name
    
    @property
    def node_group_role_arn(self) -> pulumi.Output[str]:
        """Get node group role ARN"""
        return self._node_group_role_arn
    
    @property
    def node_group_role_name(self) -> pulumi.Output[str]:
        """Get node group role name"""
        return self._node_group_role_name