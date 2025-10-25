"""
Network Infrastructure
Simple VPC with public subnets across 3 AZs for EKS
"""
import pulumi_aws as aws

# VPC
vpc = aws.ec2.Vpc("vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={"Name": "lightsphere-vpc"})

# Internet Gateway
igw = aws.ec2.InternetGateway("igw", 
    vpc_id=vpc.id,
    tags={"Name": "lightsphere-igw"})

# Public subnets with /22 CIDR (1,022 usable IPs each) across 3 AZs
subnet1 = aws.ec2.Subnet("public-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.0.0/22",
    availability_zone="af-south-1a",
    map_public_ip_on_launch=True,
    tags={
        "Name": "lightsphere-public-1a",
        "kubernetes.io/role/elb": "1",
    })

subnet2 = aws.ec2.Subnet("public-subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.4.0/22",
    availability_zone="af-south-1b",
    map_public_ip_on_launch=True,
    tags={
        "Name": "lightsphere-public-1b",
        "kubernetes.io/role/elb": "1",
    })

subnet3 = aws.ec2.Subnet("public-subnet-3",
    vpc_id=vpc.id,
    cidr_block="10.0.8.0/22",
    availability_zone="af-south-1c",
    map_public_ip_on_launch=True,
    tags={
        "Name": "lightsphere-public-1c",
        "kubernetes.io/role/elb": "1",
    })

# Route table for public access
route_table = aws.ec2.RouteTable("public-rt",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        gateway_id=igw.id)],
    tags={"Name": "lightsphere-public-rt"})

# Associate all subnets with route table
aws.ec2.RouteTableAssociation("subnet1-rt",
    subnet_id=subnet1.id, 
    route_table_id=route_table.id)

aws.ec2.RouteTableAssociation("subnet2-rt",
    subnet_id=subnet2.id, 
    route_table_id=route_table.id)

aws.ec2.RouteTableAssociation("subnet3-rt",
    subnet_id=subnet3.id, 
    route_table_id=route_table.id)

# Exports for use in other modules
subnet_ids = [subnet1.id, subnet2.id, subnet3.id]
