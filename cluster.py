"""
Simple EKS Cluster - KISS approach
Minimal IAM roles + EKS cluster + GitHub Actions access
"""

import pulumi
import pulumi_aws as aws
import json

# Configuration - keep it simple
CLUSTER_NAME = "builder-space"
NODE_COUNT = 2  # Reduced to avoid spot quota limits
INSTANCE_TYPE = "t4g.xlarge"  # Changed from t4g.medium (17 pods) to t4g.xlarge (58 pods)

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
    disk_size=80)  # Increased from 50GB to 80GB for more local storage

# Spot Node Group
spot_nodes = aws.eks.NodeGroup("spot-nodes",
    cluster_name=cluster.name,
    node_role_arn=node_role.arn,
    subnet_ids=[subnet1.id, subnet2.id],
    instance_types=["t4g.xlarge"],
    ami_type="AL2023_ARM_64_STANDARD",
    capacity_type="SPOT",
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=6,  # 6 instances = 24 vCPUs (leaving headroom under 32 vCPU quota)
        min_size=3,      # Min 3 instances = 12 vCPUs
        max_size=8,      # Max 8 instances = 32 vCPUs (full quota)
    ),
    disk_size=100)  # 100GB disk for spot instances

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
    iam_database_authentication_enabled=True,  # Enable IAM auth
    apply_immediately=True,
    publicly_accessible=False)

# IAM policy for RDS IAM authentication
rds_iam_policy = aws.iam.Policy("rds-iam-auth-policy",
    policy=database.endpoint.apply(lambda endpoint: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["rds-db:connect"],
            "Resource": [
                f"arn:aws:rds-db:{region.name}:{current.account_id}:dbuser:*/*"
            ]
        }]
    })))

# Create IAM roles for each application with IRSA
def create_app_role(app_name, namespace):
    role = aws.iam.Role(f"{app_name}-rds-role",
        assume_role_policy=cluster.identities[0].oidcs[0].issuer.apply(
            lambda issuer: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": f"arn:aws:iam::{current.account_id}:oidc-provider/{issuer.replace('https://', '')}"
                    },
                    "Action": "sts:AssumeRoleWithWebIdentity",
                    "Condition": {
                        "StringEquals": {
                            f"{issuer.replace('https://', '')}:sub": f"system:serviceaccount:{namespace}:{app_name}",
                            f"{issuer.replace('https://', '')}:aud": "sts.amazonaws.com"
                        }
                    }
                }]
            })
        ))
    
    aws.iam.RolePolicyAttachment(f"{app_name}-rds-policy-attach",
        role=role.name,
        policy_arn=rds_iam_policy.arn)
    
    return role

# Create roles for each app
nextcloud_role = create_app_role("nextcloud", "nextcloud")
erpnext_role = create_app_role("erpnext", "erpnext")
nocodb_role = create_app_role("nocodb", "nocodb")

# EFS CSI Driver IAM Role for dynamic provisioning
efs_csi_role = aws.iam.Role("efs-csi-controller-role",
    assume_role_policy=cluster.identities[0].oidcs[0].issuer.apply(
        lambda issuer: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{current.account_id}:oidc-provider/{issuer.replace('https://', '')}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{issuer.replace('https://', '')}:sub": "system:serviceaccount:kube-system:efs-csi-controller-sa",
                        f"{issuer.replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })))

efs_csi_policy = aws.iam.Policy("efs-csi-policy",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "elasticfilesystem:DescribeAccessPoints",
                "elasticfilesystem:DescribeFileSystems",
                "elasticfilesystem:DescribeMountTargets",
                "elasticfilesystem:CreateAccessPoint",
                "elasticfilesystem:DeleteAccessPoint",
                "elasticfilesystem:TagResource"
            ],
            "Resource": "*"
        }, {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeAvailabilityZones"
            ],
            "Resource": "*"
        }]
    }))

aws.iam.RolePolicyAttachment("efs-csi-policy-attach",
    role=efs_csi_role.name,
    policy_arn=efs_csi_policy.arn)

# Outputs
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("vpc_id", vpc.id)
pulumi.export("subnet_ids", [subnet1.id, subnet2.id])
pulumi.export("database_endpoint", database.endpoint)
pulumi.export("database_name", database.db_name)
pulumi.export("rds_iam_roles", {
    "nextcloud": nextcloud_role.arn,
    "erpnext": erpnext_role.arn,
    "nocodb": nocodb_role.arn
})
pulumi.export("efs_csi_role_arn", efs_csi_role.arn)
pulumi.export("kubeconfig_command", 
pulumi.Output.concat("aws eks update-kubeconfig --region ", region.name, " --name ", cluster.name))

