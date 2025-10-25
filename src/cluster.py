"""
EKS Cluster Core
Minimal cluster setup with required IAM roles
"""
import json
import pulumi
import pulumi_aws as aws
from . import network

# Configuration
config = pulumi.Config()
cluster_name = config.get("cluster_name") or "k8s.lightsphere.space"
github_role_arn = config.get("github_actions_role_arn")
node_count = int(config.get("node_count") or "3")
instance_type = config.get("instance_type") or "t3.xlarge"

# IAM role for cluster
cluster_role = aws.iam.Role("eks-cluster-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "eks.amazonaws.com"}
        }]
    }))

aws.iam.RolePolicyAttachment("eks-cluster-policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    role=cluster_role.name)

# IAM role for nodes
node_role = aws.iam.Role("eks-node-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"}
        }]
    }))

# Attach required node policies
aws.iam.RolePolicyAttachment("node-policy-worker",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    role=node_role.name)

aws.iam.RolePolicyAttachment("node-policy-cni",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    role=node_role.name)

aws.iam.RolePolicyAttachment("node-policy-ecr",
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    role=node_role.name)

aws.iam.RolePolicyAttachment("node-policy-ssm",
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    role=node_role.name)

# EKS Cluster
cluster = aws.eks.Cluster("cluster",
    name=cluster_name,
    role_arn=cluster_role.arn,
    version="1.34",
    vpc_config=aws.eks.ClusterVpcConfigArgs(
        subnet_ids=network.subnet_ids,
        endpoint_public_access=True,
        endpoint_private_access=True,
    ),
    access_config=aws.eks.ClusterAccessConfigArgs(
        authentication_mode="API"
    ),
    enabled_cluster_log_types=["api", "audit", "authenticator"])

# GitHub Actions access
github_access = aws.eks.AccessEntry("github-actions-access",
    cluster_name=cluster.name,
    principal_arn=github_role_arn,
    type="STANDARD",
    opts=pulumi.ResourceOptions(depends_on=[cluster]))

aws.eks.AccessPolicyAssociation("github-actions-admin",
    cluster_name=cluster.name,
    principal_arn=github_role_arn,
    policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
    access_scope=aws.eks.AccessPolicyAssociationAccessScopeArgs(type="cluster"),
    opts=pulumi.ResourceOptions(depends_on=[github_access]))

# Node Group across 3 AZs
node_group = aws.eks.NodeGroup("primary-nodes",
    cluster_name=cluster.name,
    node_role_arn=node_role.arn,
    subnet_ids=network.subnet_ids,
    instance_types=[instance_type],
    capacity_type="ON_DEMAND",
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=node_count,
        max_size=node_count, # + 3,
        min_size=1,
    ),
    disk_size=100,
    tags={"Name": f"{cluster_name}-primary-nodes"})


# Spot Node Group
spot_nodes = aws.eks.NodeGroup("spot-nodes",
    cluster_name=cluster.name,
    node_role_arn=node_role.arn,
    subnet_ids=[subnet1.id, subnet2.id],
    instance_types=["t4g.2xlarge"],
    ami_type="AL2023_ARM_64_STANDARD",
    capacity_type="SPOT",
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=4,
        min_size=2,
        max_size=4,
    ),
    disk_size=100)  # 100GB disk for spot instances