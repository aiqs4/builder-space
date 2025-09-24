"""
Simple EKS Cluster - KISS approach
Minimal IAM roles + EKS cluster + GitHub Actions access
"""

import pulumi
import pulumi_aws as aws
import json

# Configuration - keep it simple
CLUSTER_NAME = "builder-space"
NODE_COUNT = 5
INSTANCE_TYPE = "t4g.medium"

# Get current region and account
current = aws.get_caller_identity()
region = aws.get_region()

# GitHub Actions role ARN from config
github_actions_role_arn = pulumi.Config().get("github_actions_role_arn")

# Simple VPC (EKS needs explicit subnets)
vpc = aws.ec2.Vpc("vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True)

# Internet Gateway
igw = aws.ec2.InternetGateway("igw", vpc_id=vpc.id)

# Public subnets in 2 AZs (EKS requirement)
subnet1 = aws.ec2.Subnet("subnet1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="af-south-1a",
    map_public_ip_on_launch=True)

subnet2 = aws.ec2.Subnet("subnet2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="af-south-1b",
    map_public_ip_on_launch=True)

# Route table for public access
route_table = aws.ec2.RouteTable("route-table",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        gateway_id=igw.id)])

# Associate subnets with route table
aws.ec2.RouteTableAssociation("subnet1-rt", 
    subnet_id=subnet1.id, route_table_id=route_table.id)
aws.ec2.RouteTableAssociation("subnet2-rt",
    subnet_id=subnet2.id, route_table_id=route_table.id)

# Minimal IAM roles (required by EKS)
cluster_role = aws.iam.Role("cluster-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": ["sts:AssumeRole"],
            "Effect": "Allow",
            "Principal": {"Service": "eks.amazonaws.com"},
        }],
    }))

node_role = aws.iam.Role("node-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": ["sts:AssumeRole"],
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
        }],
    }))

# Attach required policies
aws.iam.RolePolicyAttachment("cluster-policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    role=cluster_role.name)

aws.iam.RolePolicyAttachment("node-policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    role=node_role.name)

aws.iam.RolePolicyAttachment("node-cni-policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    role=node_role.name)

aws.iam.RolePolicyAttachment("node-registry-policy",
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    role=node_role.name)

# EKS Cluster with API authentication
cluster = aws.eks.Cluster("cluster",
    name=CLUSTER_NAME,
    role_arn=cluster_role.arn,
    version="1.33",
    vpc_config=aws.eks.ClusterVpcConfigArgs(
        subnet_ids=[subnet1.id, subnet2.id],
        endpoint_public_access=True,
        endpoint_private_access=False,
    ),
    access_config=aws.eks.ClusterAccessConfigArgs(
        authentication_mode="API_AND_CONFIG_MAP"
    ))


github_access = aws.eks.AccessEntry("github-actions-access",
    cluster_name=cluster.name,
    principal_arn=github_actions_role_arn,
    type="STANDARD")

aws.eks.AccessPolicyAssociation("github-actions-cluster-admin",
    cluster_name=cluster.name,
    principal_arn=github_actions_role_arn,
    policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
    access_scope=aws.eks.AccessPolicyAssociationAccessScopeArgs(type="cluster"))

# Namespace-specific access (e.g., for 'dev' and 'staging' namespaces)
# aws.eks.AccessPolicyAssociation("github-actions-namespace-access",
#     cluster_name=cluster.name,
#     principal_arn=github_actions_role_arn,
#     policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy",  # Example: View-only policy
#     access_scope=aws.eks.AccessPolicyAssociationAccessScopeArgs(
#         type="namespace",
#         namespaces=["dev", "staging"]
#     ),
#     depends_on=[github_access]
# )

# Node Group - minimal configuration
node_group = aws.eks.NodeGroup("nodes",
    cluster_name=cluster.name,
    node_role_arn=node_role.arn,
    subnet_ids=[subnet1.id, subnet2.id],
    instance_types=[INSTANCE_TYPE],
    ami_type="AL2023_ARM_64_STANDARD",
    capacity_type="SPOT",
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=NODE_COUNT,
        max_size=NODE_COUNT + 1,
        min_size=1,
    ),
    disk_size=20)

# Spot Node Group
spot_nodes = aws.eks.NodeGroup("spot-nodes",
    cluster_name=cluster.name,
    node_role_arn=node_role.arn,
    subnet_ids=[subnet1.id, subnet2.id],
    instance_types=["t4g.xlarge"],
    ami_type="AL2023_ARM_64_STANDARD",
    capacity_type="SPOT",
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=2,
        min_size=0,
        max_size=3,
    ),
    disk_size=40)

# Simple RDS for storage
db_subnet_group = aws.rds.SubnetGroup("db-subnet-group",
    subnet_ids=[subnet1.id, subnet2.id])

database = aws.rds.Instance("postgres-db",
    db_name="builderspace",
    engine="postgres",
    engine_version="17.6",
    instance_class="db.t3.micro",
    allocated_storage=20,
    storage_type="gp2",
    db_subnet_group_name=db_subnet_group.name,
    skip_final_snapshot=True,
    username="postgres",
    password="changeme123",
    publicly_accessible=False)

# Outputs
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("database_endpoint", database.endpoint)
pulumi.export("database_name", database.db_name)
pulumi.export("kubeconfig_command", 
pulumi.Output.concat("aws eks update-kubeconfig --region ", region.name, " --name ", cluster.name))
