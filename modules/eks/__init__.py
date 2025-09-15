"""
EKS Module
Pure declarative infrastructure - no classes or functions
"""

import pulumi
import pulumi_aws as aws
from config import get_config
from modules.vpc import vpc_id, public_subnet_ids, cluster_security_group_id, node_group_security_group_id
from modules.iam import cluster_role_arn, node_group_role_arn

# Get configuration
config = get_config()
cluster_name = config.cluster_name
tags = config.common_tags

# CloudWatch Log Group for EKS cluster
log_group = aws.cloudwatch.LogGroup(
    f"{cluster_name}-eks-log-group",
    name=f"/aws/eks/{cluster_name}/cluster",
    retention_in_days=config.cloudwatch_log_group_retention_in_days,
    tags={
        **tags,
        "Name": f"{cluster_name}-eks-log-group",
        "Module": "eks"
    }
)

# KMS Key for EKS encryption
if config.use_existing_kms_key and config.existing_kms_key_arn:
    kms_key_arn = config.existing_kms_key_arn
else:
    kms_key = aws.kms.Key(
        f"{cluster_name}-eks-kms-key",
        description=f"EKS Secret Encryption Key for {cluster_name}",
        tags={
            **tags,
            "Name": f"{cluster_name}-eks-kms-key",
            "Module": "eks"
        }
    )
    
    kms_alias = aws.kms.Alias(
        f"{cluster_name}-eks-kms-alias",
        name=f"alias/{cluster_name}-eks",
        target_key_id=kms_key.key_id
    )
    
    kms_key_arn = kms_key.arn

# EKS Cluster
cluster = aws.eks.Cluster(
    f"{cluster_name}-cluster",
    name=cluster_name,
    version=config.cluster_version,
    role_arn=cluster_role_arn,
    vpc_config=aws.eks.ClusterVpcConfigArgs(
        subnet_ids=public_subnet_ids,
        endpoint_private_access=False,
        endpoint_public_access=True,
        public_access_cidrs=["0.0.0.0/0"],
        security_group_ids=[cluster_security_group_id]
    ),
    enabled_cluster_log_types=config.cluster_enabled_log_types,
    encryption_config=aws.eks.ClusterEncryptionConfigArgs(
        provider=aws.eks.ClusterEncryptionConfigProviderArgs(
            key_arn=kms_key_arn
        ),
        resources=["secrets"]
    ),
    tags={
        **tags,
        "Name": f"{cluster_name}-cluster",
        "Module": "eks"
    },
    opts=pulumi.ResourceOptions(depends_on=[log_group])
)

# EKS Node Group
node_group = aws.eks.NodeGroup(
    f"{cluster_name}-node-group",
    cluster_name=cluster.name,
    node_group_name=f"{cluster_name}-nodes",
    node_role_arn=node_group_role_arn,
    subnet_ids=public_subnet_ids,
    capacity_type=config.capacity_type,
    instance_types=config.optimized_instance_types,
    disk_size=config.node_disk_size,
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=config.node_desired_size,
        max_size=config.node_max_size,
        min_size=config.node_min_size
    ),
    update_config=aws.eks.NodeGroupUpdateConfigArgs(
        max_unavailable_percentage=25
    ),
    tags={
        **tags,
        "Name": f"{cluster_name}-node-group",
        "Module": "eks"
    },
    opts=pulumi.ResourceOptions(depends_on=[cluster])
)

# EKS Add-ons
if config.enable_vpc_cni_addon:
    vpc_cni_addon = aws.eks.Addon(
        f"{cluster_name}-vpc-cni-addon",
        cluster_name=cluster.name,
        addon_name="vpc-cni",
        resolve_conflicts_on_create="OVERWRITE",
        resolve_conflicts_on_update="OVERWRITE",
        tags={
            **tags,
            "Name": f"{cluster_name}-vpc-cni-addon",
            "Module": "eks"
        }
    )

if config.enable_coredns_addon:
    coredns_addon = aws.eks.Addon(
        f"{cluster_name}-coredns-addon",
        cluster_name=cluster.name,
        addon_name="coredns",
        resolve_conflicts_on_create="OVERWRITE",
        resolve_conflicts_on_update="OVERWRITE",
        tags={
            **tags,
            "Name": f"{cluster_name}-coredns-addon",
            "Module": "eks"
        },
        opts=pulumi.ResourceOptions(depends_on=[node_group])
    )

if config.enable_kube_proxy_addon:
    kube_proxy_addon = aws.eks.Addon(
        f"{cluster_name}-kube-proxy-addon",
        cluster_name=cluster.name,
        addon_name="kube-proxy",
        resolve_conflicts_on_create="OVERWRITE",
        resolve_conflicts_on_update="OVERWRITE",
        tags={
            **tags,
            "Name": f"{cluster_name}-kube-proxy-addon",
            "Module": "eks"
        }
    )

# Export cluster information for other modules
cluster_id = cluster.id
cluster_arn = cluster.arn
cluster_endpoint = cluster.endpoint
cluster_version = cluster.version
cluster_certificate_authority_data = cluster.certificate_authority.data
node_group_arn = node_group.arn
node_group_status = node_group.status