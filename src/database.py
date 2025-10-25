"""
Database Infrastructure
Aurora PostgreSQL Serverless v2 for production
"""
import pulumi
import pulumi_aws as aws

def create_database(network):
    """Create Aurora PostgreSQL Serverless v2 cluster"""
    
    # Security group for database
    db_sg = aws.ec2.SecurityGroup("db-sg",
        vpc_id=network["vpc"].id,
        description="Aurora PostgreSQL security group",
        ingress=[aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=5432,
            to_port=5432,
            cidr_blocks=["10.0.0.0/16"],  # VPC CIDR only
        )],
        egress=[aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        )])

    # Subnet group
    db_subnet_group = aws.rds.SubnetGroup("aurora-subnet-group",
        subnet_ids=network["subnet_ids"],
        tags={"Name": "aurora-subnet-group"})

    # Aurora Serverless v2 cluster
    cluster = aws.rds.Cluster("aurora-postgres",
        cluster_identifier="builder-space-postgres",
        engine="aurora-postgresql",
        engine_mode="provisioned",
        engine_version="16.4",
        database_name="builderspace",
        master_username="postgres",
        master_password=pulumi.Config().require_secret("db_password"),
        db_subnet_group_name=db_subnet_group.name,
        vpc_security_group_ids=[db_sg.id],
        skip_final_snapshot=True,
        serverlessv2_scaling_configuration=aws.rds.ClusterServerlessv2ScalingConfigurationArgs(
            max_capacity=2.0,  # 2 ACUs max
            min_capacity=0.5,  # 0.5 ACUs min (scales to zero)
        ),
        iam_database_authentication_enabled=True,
        storage_encrypted=True,
        backup_retention_period=7,
        preferred_backup_window="03:00-04:00",
        preferred_maintenance_window="mon:04:00-mon:05:00")

    # Single writer instance
    instance = aws.rds.ClusterInstance("aurora-instance",
        cluster_identifier=cluster.id,
        instance_class="db.serverless",
        engine=cluster.engine,
        engine_version=cluster.engine_version)

    return {
        "cluster": cluster,
        "instance": instance,
        "endpoint": cluster.endpoint,
        "database_name": cluster.database_name,
    }
