"""
Network Infrastructure
Simple VPC with public subnets for EKS
"""
import pulumi_aws as aws

def create_network():
    """Create VPC with 2 public subnets in different AZs"""
    
    vpc = aws.ec2.Vpc("vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={"Name": "builder-space-vpc"})

    igw = aws.ec2.InternetGateway("igw", 
        vpc_id=vpc.id,
        tags={"Name": "builder-space-igw"})

    # Public subnets with /22 CIDR (1,022 usable IPs each)
    subnet1 = aws.ec2.Subnet("public-subnet-1",
        vpc_id=vpc.id,
        cidr_block="10.0.0.0/22",
        availability_zone="af-south-1a",
        map_public_ip_on_launch=True,
        tags={
            "Name": "builder-space-public-1",
            "kubernetes.io/role/elb": "1",
        })

    subnet2 = aws.ec2.Subnet("public-subnet-2",
        vpc_id=vpc.id,
        cidr_block="10.0.4.0/22",
        availability_zone="af-south-1b",
        map_public_ip_on_launch=True,
        tags={
            "Name": "builder-space-public-2",
            "kubernetes.io/role/elb": "1",
        })

    # Single route table for public access
    route_table = aws.ec2.RouteTable("public-rt",
        vpc_id=vpc.id,
        routes=[aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id)],
        tags={"Name": "builder-space-public-rt"})

    aws.ec2.RouteTableAssociation("subnet1-rt",
        subnet_id=subnet1.id, 
        route_table_id=route_table.id)
    
    aws.ec2.RouteTableAssociation("subnet2-rt",
        subnet_id=subnet2.id, 
        route_table_id=route_table.id)

    return {
        "vpc": vpc,
        "subnet_ids": [subnet1.id, subnet2.id],
        "subnets": [subnet1, subnet2]
    }
