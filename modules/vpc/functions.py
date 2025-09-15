"""
VPC Module Functions
Creates VPC, subnets, route tables, and security groups for EKS
Refactored to function-based style following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List, Any


def create_vpc(name: str, cidr: str, tags: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create VPC with DNS settings
    
    Args:
        name: VPC name
        cidr: VPC CIDR block
        tags: Additional tags
        
    Returns:
        Dict with vpc resource and outputs
    """
    tags = tags or {}
    
    vpc = aws.ec2.Vpc(
        f"{name}-vpc",
        cidr_block=cidr,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={
            **tags,
            "Name": f"{name}-vpc",
            f"kubernetes.io/cluster/{name}": "shared",
            "Module": "vpc"
        }
    )
    
    return {
        "vpc": vpc,
        "vpc_id": vpc.id,
        "vpc_cidr_block": vpc.cidr_block
    }


def create_internet_gateway(name: str, vpc_id: pulumi.Output[str], tags: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create Internet Gateway for VPC
    
    Args:
        name: Resource name prefix
        vpc_id: VPC ID to attach to
        tags: Additional tags
        
    Returns:
        Dict with igw resource and outputs
    """
    tags = tags or {}
    
    igw = aws.ec2.InternetGateway(
        f"{name}-igw",
        vpc_id=vpc_id,
        tags={
            **tags,
            "Name": f"{name}-igw",
            "Module": "vpc"
        }
    )
    
    return {
        "igw": igw,
        "igw_id": igw.id
    }


def create_public_subnets(name: str, vpc_id: pulumi.Output[str], subnet_cidrs: List[str], 
                         availability_zones: List[str], tags: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create public subnets for EKS
    
    Args:
        name: Resource name prefix
        vpc_id: VPC ID
        subnet_cidrs: List of CIDR blocks for subnets
        availability_zones: List of availability zones
        tags: Additional tags
        
    Returns:
        Dict with subnet resources and outputs
    """
    tags = tags or {}
    
    subnets = []
    for i, cidr in enumerate(subnet_cidrs):
        subnet = aws.ec2.Subnet(
            f"{name}-public-subnet-{i+1}",
            vpc_id=vpc_id,
            cidr_block=cidr,
            availability_zone=availability_zones[i],
            map_public_ip_on_launch=True,
            tags={
                **tags,
                "Name": f"{name}-public-subnet-{i+1}",
                "Type": "public",
                f"kubernetes.io/cluster/{name}": "shared",
                "kubernetes.io/role/elb": "1",
                "Module": "vpc"
            }
        )
        subnets.append(subnet)
    
    return {
        "subnets": subnets,
        "subnet_ids": [subnet.id for subnet in subnets],
        "availability_zones": availability_zones
    }


def create_public_route_table(name: str, vpc_id: pulumi.Output[str], igw_id: pulumi.Output[str], 
                             subnet_ids: List[pulumi.Output[str]], tags: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create route table for public subnets
    
    Args:
        name: Resource name prefix
        vpc_id: VPC ID
        igw_id: Internet Gateway ID
        subnet_ids: List of subnet IDs to associate
        tags: Additional tags
        
    Returns:
        Dict with route table resources and outputs
    """
    tags = tags or {}
    
    # Create route table
    route_table = aws.ec2.RouteTable(
        f"{name}-public-rt",
        vpc_id=vpc_id,
        tags={
            **tags,
            "Name": f"{name}-public-rt",
            "Module": "vpc"
        }
    )
    
    # Create route to internet gateway
    route = aws.ec2.Route(
        f"{name}-public-route",
        route_table_id=route_table.id,
        destination_cidr_block="0.0.0.0/0",
        gateway_id=igw_id
    )
    
    # Associate subnets with route table
    associations = []
    for i, subnet_id in enumerate(subnet_ids):
        association = aws.ec2.RouteTableAssociation(
            f"{name}-public-rta-{i+1}",
            subnet_id=subnet_id,
            route_table_id=route_table.id
        )
        associations.append(association)
    
    return {
        "route_table": route_table,
        "route": route,
        "associations": associations,
        "route_table_id": route_table.id
    }


def create_cluster_security_group(name: str, vpc_id: pulumi.Output[str], tags: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create security group for EKS cluster
    
    Args:
        name: Resource name prefix
        vpc_id: VPC ID
        tags: Additional tags
        
    Returns:
        Dict with security group resources and outputs
    """
    tags = tags or {}
    
    security_group = aws.ec2.SecurityGroup(
        f"{name}-cluster-sg",
        name_prefix=f"{name}-cluster-",
        vpc_id=vpc_id,
        tags={
            **tags,
            "Name": f"{name}-cluster-sg",
            "Module": "vpc"
        }
    )
    
    # Egress rule for cluster security group
    egress_rule = aws.ec2.SecurityGroupRule(
        f"{name}-cluster-egress",
        type="egress",
        from_port=0,
        to_port=65535,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        security_group_id=security_group.id
    )
    
    return {
        "security_group": security_group,
        "egress_rule": egress_rule,
        "security_group_id": security_group.id
    }


def create_node_security_group(name: str, vpc_id: pulumi.Output[str], cluster_sg_id: pulumi.Output[str], 
                              tags: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create security group for EKS node group
    
    Args:
        name: Resource name prefix
        vpc_id: VPC ID
        cluster_sg_id: Cluster security group ID
        tags: Additional tags
        
    Returns:
        Dict with security group resources and outputs
    """
    tags = tags or {}
    
    security_group = aws.ec2.SecurityGroup(
        f"{name}-node-sg",
        name_prefix=f"{name}-node-",
        vpc_id=vpc_id,
        tags={
            **tags,
            "Name": f"{name}-node-sg",
            "Module": "vpc"
        }
    )
    
    # Allow communication between nodes
    node_ingress_self = aws.ec2.SecurityGroupRule(
        f"{name}-node-ingress-self",
        type="ingress",
        from_port=0,
        to_port=65535,
        protocol="-1",
        self=True,
        security_group_id=security_group.id
    )
    
    # Allow nodes to communicate with cluster API server
    node_ingress_cluster = aws.ec2.SecurityGroupRule(
        f"{name}-node-ingress-cluster",
        type="ingress",
        from_port=1025,
        to_port=65535,
        protocol="tcp",
        source_security_group_id=cluster_sg_id,
        security_group_id=security_group.id
    )
    
    # Allow nodes egress to internet
    node_egress_rule = aws.ec2.SecurityGroupRule(
        f"{name}-node-egress",
        type="egress",
        from_port=0,
        to_port=65535,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        security_group_id=security_group.id
    )
    
    # Allow cluster to communicate with nodes
    cluster_ingress_node = aws.ec2.SecurityGroupRule(
        f"{name}-cluster-ingress-node",
        type="ingress",
        from_port=443,
        to_port=443,
        protocol="tcp",
        source_security_group_id=security_group.id,
        security_group_id=cluster_sg_id
    )
    
    return {
        "security_group": security_group,
        "node_ingress_self": node_ingress_self,
        "node_ingress_cluster": node_ingress_cluster,
        "node_egress_rule": node_egress_rule,
        "cluster_ingress_node": cluster_ingress_node,
        "security_group_id": security_group.id
    }


def create_vpc_resources(cluster_name: str, vpc_cidr: str, public_subnet_cidrs: List[str],
                        enable_dns_hostnames: bool = True, enable_dns_support: bool = True,
                        map_public_ip_on_launch: bool = True, tags: Dict[str, str] = None) -> Dict[str, Any]:
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
    vpc_result = create_vpc(cluster_name, vpc_cidr, tags)
    
    # Create Internet Gateway
    igw_result = create_internet_gateway(cluster_name, vpc_result["vpc_id"], tags)
    
    # Create public subnets
    subnets_result = create_public_subnets(
        cluster_name, 
        vpc_result["vpc_id"], 
        public_subnet_cidrs, 
        azs.names, 
        tags
    )
    
    # Create route table
    route_table_result = create_public_route_table(
        cluster_name,
        vpc_result["vpc_id"],
        igw_result["igw_id"],
        subnets_result["subnet_ids"],
        tags
    )
    
    # Create cluster security group
    cluster_sg_result = create_cluster_security_group(cluster_name, vpc_result["vpc_id"], tags)
    
    # Create node security group
    node_sg_result = create_node_security_group(
        cluster_name, 
        vpc_result["vpc_id"], 
        cluster_sg_result["security_group_id"], 
        tags
    )
    
    return {
        "vpc_id": vpc_result["vpc_id"],
        "vpc_cidr_block": vpc_result["vpc_cidr_block"],
        "public_subnet_ids": subnets_result["subnet_ids"],
        "availability_zones": subnets_result["availability_zones"],
        "cluster_security_group_id": cluster_sg_result["security_group_id"],
        "node_group_security_group_id": node_sg_result["security_group_id"],
        # Keep references to all resources for dependencies
        "_vpc": vpc_result["vpc"],
        "_igw": igw_result["igw"],
        "_subnets": subnets_result["subnets"],
        "_route_table": route_table_result["route_table"],
        "_cluster_sg": cluster_sg_result["security_group"],
        "_node_sg": node_sg_result["security_group"]
    }