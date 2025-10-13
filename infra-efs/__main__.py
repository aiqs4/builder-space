"""
EFS File System for Multi-AZ Persistent Storage
"""

import pulumi
import pulumi_aws as aws

config = pulumi.Config()
cluster_name = config.get("cluster_name") or "builder-space"
aws_region = config.get("aws:region") or "af-south-1"

# Get VPC from main stack outputs
main_stack = pulumi.StackReference("organization/builder-space-eks/eks")
vpc_id = main_stack.get_output("vpc_id")
subnet_ids = main_stack.get_output("subnet_ids")

# Tags
tags = {
    "Project": "builder-space-eks",
    "Environment": "production",
    "ManagedBy": "pulumi",
    "Purpose": "efs-storage"
}

# KMS key for EFS encryption
efs_kms_key = aws.kms.Key("efs-kms-key",
    description=f"KMS key for {cluster_name} EFS encryption",
    deletion_window_in_days=7,
    tags=tags
)

aws.kms.Alias("efs-kms-alias",
    name=f"alias/{cluster_name}-efs",
    target_key_id=efs_kms_key.key_id
)

# Security group for EFS
efs_sg = aws.ec2.SecurityGroup("efs-sg",
    name=f"{cluster_name}-efs-sg",
    description="Allow NFS traffic from EKS nodes to EFS",
    vpc_id=vpc_id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=2049,
            to_port=2049,
            cidr_blocks=["10.0.0.0/16"]
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"]
        )
    ],
    tags=tags
)

# EFS File System
efs = aws.efs.FileSystem("efs",
    encrypted=True,
    kms_key_id=efs_kms_key.arn,
    performance_mode="generalPurpose",
    throughput_mode="bursting",
    lifecycle_policies=[
        aws.efs.FileSystemLifecyclePolicyArgs(
            transition_to_ia="AFTER_30_DAYS"
        )
    ],
    tags={**tags, "Name": f"{cluster_name}-efs"}
)

# Mount targets in each subnet
mount_target_1 = aws.efs.MountTarget("efs-mount-1",
    file_system_id=efs.id,
    subnet_id=subnet_ids.apply(lambda subnets: subnets[0]),
    security_groups=[efs_sg.id]
)

mount_target_2 = aws.efs.MountTarget("efs-mount-2",
    file_system_id=efs.id,
    subnet_id=subnet_ids.apply(lambda subnets: subnets[1]),
    security_groups=[efs_sg.id]
)

# Outputs
pulumi.export("efs_id", efs.id)
pulumi.export("efs_dns", pulumi.Output.concat(efs.id, ".efs.", aws_region, ".amazonaws.com"))
pulumi.export("security_group_id", efs_sg.id)
