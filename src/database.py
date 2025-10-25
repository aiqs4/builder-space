"""
Database Infrastructure
Aurora PostgreSQL Serverless v2 for production
"""
import pulumi
import pulumi_aws as aws
from . import network

# Configuration
config = pulumi.Config()

# Security group for database
db_sg = aws.ec2.SecurityGroup("db-sg",
    vpc_id=network.vpc.id,
    description="Aurora PostgreSQL security group",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp",
        from_port=5432,
        to_port=5432,
        cidr_blocks=["10.0.0.0/16"],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"],
    )])

# Subnet group across 3 AZs
db_subnet_group = aws.rds.SubnetGroup("aurora-subnet-group",
    subnet_ids=network.subnet_ids,
    tags={"Name": "lightsphere-aurora-subnet"})

# Aurora Serverless v2 cluster
aurora_cluster = aws.rds.Cluster("aurora-postgres",
    cluster_identifier="lightsphere-postgres",
    engine="aurora-postgresql",
    engine_mode="provisioned",
    engine_version="16.4",
    database_name="builderspace",
    master_username="postgres",
    master_password=config.require_secret("db_password"),
    db_subnet_group_name=db_subnet_group.name,
    vpc_security_group_ids=[db_sg.id],
    skip_final_snapshot=True,
    serverlessv2_scaling_configuration=aws.rds.ClusterServerlessv2ScalingConfigurationArgs(
        max_capacity=2.0,
        min_capacity=0.5,
    ),
    iam_database_authentication_enabled=True,
    storage_encrypted=True,
    backup_retention_period=7,
    preferred_backup_window="03:00-04:00",
    preferred_maintenance_window="mon:04:00-mon:05:00",
    availability_zones=["af-south-1a", "af-south-1b", "af-south-1c"])

# Writer instance
aurora_instance = aws.rds.ClusterInstance("aurora-instance",
    cluster_identifier=aurora_cluster.id,
    instance_class="db.serverless",
    engine=aurora_cluster.engine,
    engine_version=aurora_cluster.engine_version)
