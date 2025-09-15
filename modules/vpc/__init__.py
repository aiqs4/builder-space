"""
VPC Module for EKS
Pure declarative infrastructure - no classes or functions
"""

import pulumi
import pulumi_aws as aws
from config import get_config

# Get configuration
config = get_config()
cluster_name = config.cluster_name
tags = config.common_tags

# Get availability zones
azs = aws.get_availability_zones(state="available")

# VPC
vpc = aws.ec2.Vpc(
    f"{cluster_name}-vpc",
    cidr_block=config.vpc_cidr,
    enable_dns_hostnames=config.enable_dns_hostnames,
    enable_dns_support=config.enable_dns_support,
    tags={
        **tags,
        "Name": f"{cluster_name}-vpc",
        f"kubernetes.io/cluster/{cluster_name}": "shared",
        "Module": "vpc"
    }
)

# Internet Gateway
igw = aws.ec2.InternetGateway(
    f"{cluster_name}-igw",
    vpc_id=vpc.id,
    tags={
        **tags,
        "Name": f"{cluster_name}-igw",
        "Module": "vpc"
    }
)

# Public Subnets
public_subnets = []
for i, cidr in enumerate(config.public_subnet_cidrs):
    subnet = aws.ec2.Subnet(
        f"{cluster_name}-public-subnet-{i+1}",
        vpc_id=vpc.id,
        cidr_block=cidr,
        availability_zone=azs.names[i],
        map_public_ip_on_launch=config.map_public_ip_on_launch,
        tags={
            **tags,
            "Name": f"{cluster_name}-public-subnet-{i+1}",
            "Type": "public",
            f"kubernetes.io/cluster/{cluster_name}": "shared",
            "kubernetes.io/role/elb": "1",
            "Module": "vpc"
        }
    )
    public_subnets.append(subnet)

# Route Table for Public Subnets
public_route_table = aws.ec2.RouteTable(
    f"{cluster_name}-public-rt",
    vpc_id=vpc.id,
    tags={
        **tags,
        "Name": f"{cluster_name}-public-rt",
        "Module": "vpc"
    }
)

# Route to Internet Gateway
public_route = aws.ec2.Route(
    f"{cluster_name}-public-route",
    route_table_id=public_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=igw.id
)

# Associate Public Subnets with Route Table
public_route_table_associations = []
for i, subnet in enumerate(public_subnets):
    association = aws.ec2.RouteTableAssociation(
        f"{cluster_name}-public-rta-{i+1}",
        subnet_id=subnet.id,
        route_table_id=public_route_table.id
    )
    public_route_table_associations.append(association)

# Security Group for EKS Cluster
cluster_security_group = aws.ec2.SecurityGroup(
    f"{cluster_name}-cluster-sg",
    name_prefix=f"{cluster_name}-cluster-",
    vpc_id=vpc.id,
    tags={
        **tags,
        "Name": f"{cluster_name}-cluster-sg",
        "Module": "vpc"
    }
)

# Cluster Security Group Egress Rule
cluster_egress_rule = aws.ec2.SecurityGroupRule(
    f"{cluster_name}-cluster-egress",
    type="egress",
    from_port=0,
    to_port=65535,
    protocol="-1",
    cidr_blocks=["0.0.0.0/0"],
    security_group_id=cluster_security_group.id
)

# Security Group for Node Group
node_group_security_group = aws.ec2.SecurityGroup(
    f"{cluster_name}-node-sg",
    name_prefix=f"{cluster_name}-node-",
    vpc_id=vpc.id,
    tags={
        **tags,
        "Name": f"{cluster_name}-node-sg",
        "Module": "vpc"
    }
)

# Node Group Security Group Rules
node_ingress_self = aws.ec2.SecurityGroupRule(
    f"{cluster_name}-node-ingress-self",
    type="ingress",
    from_port=0,
    to_port=65535,
    protocol="-1",
    self=True,
    security_group_id=node_group_security_group.id
)

node_ingress_cluster = aws.ec2.SecurityGroupRule(
    f"{cluster_name}-node-ingress-cluster",
    type="ingress",
    from_port=1025,
    to_port=65535,
    protocol="tcp",
    source_security_group_id=cluster_security_group.id,
    security_group_id=node_group_security_group.id
)

node_egress_rule = aws.ec2.SecurityGroupRule(
    f"{cluster_name}-node-egress",
    type="egress",
    from_port=0,
    to_port=65535,
    protocol="-1",
    cidr_blocks=["0.0.0.0/0"],
    security_group_id=node_group_security_group.id
)

cluster_ingress_node = aws.ec2.SecurityGroupRule(
    f"{cluster_name}-cluster-ingress-node",
    type="ingress",
    from_port=443,
    to_port=443,
    protocol="tcp",
    source_security_group_id=node_group_security_group.id,
    security_group_id=cluster_security_group.id
)

# Export resources for use by other modules
vpc_id = vpc.id
vpc_cidr_block = vpc.cidr_block
public_subnet_ids = [subnet.id for subnet in public_subnets]
cluster_security_group_id = cluster_security_group.id
node_group_security_group_id = node_group_security_group.id
availability_zones = azs.names