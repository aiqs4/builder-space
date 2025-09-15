"""
VPC Module for EKS
Creates VPC, subnets, route tables, and security groups for EKS
Simple function-based approach following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List


def create_vpc_resources(cluster_name: str, vpc_cidr: str, public_subnet_cidrs: List[str],
                        enable_dns_hostnames: bool = True, enable_dns_support: bool = True,
                        map_public_ip_on_launch: bool = True, tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create complete VPC infrastructure for EKS
    
    Args:
        cluster_name: EKS cluster name
        vpc_cidr: VPC CIDR block
        public_subnet_cidrs: List of public subnet CIDR blocks
        enable_dns_hostnames: Enable DNS hostnames in VPC
        enable_dns_support: Enable DNS support in VPC
        map_public_ip_on_launch: Auto-assign public IPs to instances
        tags: Additional tags for all resources
        
    Returns:
        Dict with all VPC resources and outputs
    """
    tags = tags or {}
    
    # Get availability zones
    azs = aws.get_availability_zones(state="available")
    
    # Create VPC
    vpc = aws.ec2.Vpc(
        f"{cluster_name}-vpc",
        cidr_block=vpc_cidr,
        enable_dns_hostnames=enable_dns_hostnames,
        enable_dns_support=enable_dns_support,
        tags={
            **tags,
            "Name": f"{cluster_name}-vpc",
            f"kubernetes.io/cluster/{cluster_name}": "shared",
            "Module": "vpc"
        }
    )
    
    # Create Internet Gateway
    igw = aws.ec2.InternetGateway(
        f"{cluster_name}-igw",
        vpc_id=vpc.id,
        tags={
            **tags,
            "Name": f"{cluster_name}-igw",
            "Module": "vpc"
        }
    )
    
    # Create public subnets
    public_subnets = []
    for i, cidr in enumerate(public_subnet_cidrs):
        subnet = aws.ec2.Subnet(
            f"{cluster_name}-public-subnet-{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=azs.names[i],
            map_public_ip_on_launch=map_public_ip_on_launch,
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
    
    # Create route table for public subnets
    public_route_table = aws.ec2.RouteTable(
        f"{cluster_name}-public-rt",
        vpc_id=vpc.id,
        tags={
            **tags,
            "Name": f"{cluster_name}-public-rt",
            "Module": "vpc"
        }
    )
    
    # Create route to internet gateway
    public_route = aws.ec2.Route(
        f"{cluster_name}-public-route",
        route_table_id=public_route_table.id,
        destination_cidr_block="0.0.0.0/0",
        gateway_id=igw.id
    )
    
    # Associate public subnets with route table
    public_route_table_associations = []
    for i, subnet in enumerate(public_subnets):
        association = aws.ec2.RouteTableAssociation(
            f"{cluster_name}-public-rta-{i+1}",
            subnet_id=subnet.id,
            route_table_id=public_route_table.id
        )
        public_route_table_associations.append(association)
    
    # Create security group for EKS cluster
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
    
    # Create egress rule for cluster security group
    cluster_egress_rule = aws.ec2.SecurityGroupRule(
        f"{cluster_name}-cluster-egress",
        type="egress",
        from_port=0,
        to_port=65535,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        security_group_id=cluster_security_group.id
    )
    
    # Create security group for node group
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
    
    # Node group security group rules
    # Allow communication between nodes
    node_ingress_self = aws.ec2.SecurityGroupRule(
        f"{cluster_name}-node-ingress-self",
        type="ingress",
        from_port=0,
        to_port=65535,
        protocol="-1",
        self=True,
        security_group_id=node_group_security_group.id
    )
    
    # Allow nodes to communicate with cluster API server
    node_ingress_cluster = aws.ec2.SecurityGroupRule(
        f"{cluster_name}-node-ingress-cluster",
        type="ingress",
        from_port=1025,
        to_port=65535,
        protocol="tcp",
        source_security_group_id=cluster_security_group.id,
        security_group_id=node_group_security_group.id
    )
    
    # Allow nodes egress to internet
    node_egress_rule = aws.ec2.SecurityGroupRule(
        f"{cluster_name}-node-egress",
        type="egress",
        from_port=0,
        to_port=65535,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        security_group_id=node_group_security_group.id
    )
    
    # Allow cluster to communicate with nodes
    cluster_ingress_node = aws.ec2.SecurityGroupRule(
        f"{cluster_name}-cluster-ingress-node",
        type="ingress",
        from_port=443,
        to_port=443,
        protocol="tcp",
        source_security_group_id=node_group_security_group.id,
        security_group_id=cluster_security_group.id
    )
    
    return {
        "vpc_id": vpc.id,
        "vpc_cidr_block": vpc.cidr_block,
        "public_subnet_ids": [subnet.id for subnet in public_subnets],
        "availability_zones": azs.names,
        "cluster_security_group_id": cluster_security_group.id,
        "node_group_security_group_id": node_group_security_group.id,
    }