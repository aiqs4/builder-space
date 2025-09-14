"""
VPC Module for EKS
Creates VPC, subnets, route tables, and security groups for EKS
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List, Any

class VPCResources:
    """VPC resources for EKS cluster"""
    
    def __init__(self, 
                 cluster_name: str,
                 vpc_cidr: str,
                 public_subnet_cidrs: List[str],
                 enable_dns_hostnames: bool = True,
                 enable_dns_support: bool = True,
                 map_public_ip_on_launch: bool = True,
                 tags: Dict[str, str] = None):
        
        self.cluster_name = cluster_name
        self.tags = tags or {}
        
        # Get availability zones
        self.azs = aws.get_availability_zones(state="available")
        
        # Create VPC
        self.vpc = aws.ec2.Vpc(
            f"{cluster_name}-vpc",
            cidr_block=vpc_cidr,
            enable_dns_hostnames=enable_dns_hostnames,
            enable_dns_support=enable_dns_support,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-vpc",
                f"kubernetes.io/cluster/{cluster_name}": "shared",
                "Module": "vpc"
            }
        )
        
        # Create Internet Gateway
        self.igw = aws.ec2.InternetGateway(
            f"{cluster_name}-igw",
            vpc_id=self.vpc.id,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-igw",
                "Module": "vpc"
            }
        )
        
        # Create public subnets
        self.public_subnets = []
        for i, cidr in enumerate(public_subnet_cidrs):
            subnet = aws.ec2.Subnet(
                f"{cluster_name}-public-subnet-{i+1}",
                vpc_id=self.vpc.id,
                cidr_block=cidr,
                availability_zone=self.azs.names[i],
                map_public_ip_on_launch=map_public_ip_on_launch,
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-public-subnet-{i+1}",
                    "Type": "public",
                    f"kubernetes.io/cluster/{cluster_name}": "shared",
                    "kubernetes.io/role/elb": "1",
                    "Module": "vpc"
                }
            )
            self.public_subnets.append(subnet)
        
        # Create route table for public subnets
        self.public_route_table = aws.ec2.RouteTable(
            f"{cluster_name}-public-rt",
            vpc_id=self.vpc.id,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-public-rt",
                "Module": "vpc"
            }
        )
        
        # Create route to internet gateway
        self.public_route = aws.ec2.Route(
            f"{cluster_name}-public-route",
            route_table_id=self.public_route_table.id,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=self.igw.id
        )
        
        # Associate public subnets with route table
        self.public_route_table_associations = []
        for i, subnet in enumerate(self.public_subnets):
            association = aws.ec2.RouteTableAssociation(
                f"{cluster_name}-public-rta-{i+1}",
                subnet_id=subnet.id,
                route_table_id=self.public_route_table.id
            )
            self.public_route_table_associations.append(association)
        
        # Create security group for EKS cluster
        self.cluster_security_group = aws.ec2.SecurityGroup(
            f"{cluster_name}-cluster-sg",
            name_prefix=f"{cluster_name}-cluster-",
            vpc_id=self.vpc.id,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-cluster-sg",
                "Module": "vpc"
            }
        )
        
        # Create egress rule for cluster security group
        self.cluster_egress_rule = aws.ec2.SecurityGroupRule(
            f"{cluster_name}-cluster-egress",
            type="egress",
            from_port=0,
            to_port=65535,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=self.cluster_security_group.id
        )
        
        # Create security group for node group
        self.node_group_security_group = aws.ec2.SecurityGroup(
            f"{cluster_name}-node-sg",
            name_prefix=f"{cluster_name}-node-",
            vpc_id=self.vpc.id,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-node-sg",
                "Module": "vpc"
            }
        )
        
        # Node group security group rules
        # Allow communication between nodes
        self.node_ingress_self = aws.ec2.SecurityGroupRule(
            f"{cluster_name}-node-ingress-self",
            type="ingress",
            from_port=0,
            to_port=65535,
            protocol="-1",
            self=True,
            security_group_id=self.node_group_security_group.id
        )
        
        # Allow nodes to communicate with cluster API server
        self.node_ingress_cluster = aws.ec2.SecurityGroupRule(
            f"{cluster_name}-node-ingress-cluster",
            type="ingress",
            from_port=1025,
            to_port=65535,
            protocol="tcp",
            source_security_group_id=self.cluster_security_group.id,
            security_group_id=self.node_group_security_group.id
        )
        
        # Allow nodes egress to internet
        self.node_egress_rule = aws.ec2.SecurityGroupRule(
            f"{cluster_name}-node-egress",
            type="egress",
            from_port=0,
            to_port=65535,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
            security_group_id=self.node_group_security_group.id
        )
        
        # Allow cluster to communicate with nodes
        self.cluster_ingress_node = aws.ec2.SecurityGroupRule(
            f"{cluster_name}-cluster-ingress-node",
            type="ingress",
            from_port=443,
            to_port=443,
            protocol="tcp",
            source_security_group_id=self.node_group_security_group.id,
            security_group_id=self.cluster_security_group.id
        )
    
    @property
    def vpc_id(self) -> pulumi.Output[str]:
        """Get VPC ID"""
        return self.vpc.id
    
    @property
    def vpc_cidr_block(self) -> pulumi.Output[str]:
        """Get VPC CIDR block"""
        return self.vpc.cidr_block
    
    @property
    def public_subnet_ids(self) -> List[pulumi.Output[str]]:
        """Get public subnet IDs"""
        return [subnet.id for subnet in self.public_subnets]
    
    @property
    def cluster_security_group_id(self) -> pulumi.Output[str]:
        """Get cluster security group ID"""
        return self.cluster_security_group.id
    
    @property
    def node_group_security_group_id(self) -> pulumi.Output[str]:
        """Get node group security group ID"""
        return self.node_group_security_group.id
    
    @property
    def availability_zones(self) -> List[str]:
        """Get availability zones"""
        return self.azs.names