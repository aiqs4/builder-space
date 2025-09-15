"""
EKS Module Functions
Creates EKS cluster and managed node groups
Refactored to function-based style following Pulumi best practices
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List, Optional


def create_cloudwatch_log_group(name: str, retention_days: int = 30, tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create CloudWatch log group for EKS cluster
    
    Args:
        name: Cluster name
        retention_days: Log retention in days
        tags: Additional tags
        
    Returns:
        Dict with log group resource and outputs
    """
    tags = tags or {}
    
    log_group = aws.cloudwatch.LogGroup(
        f"{name}-eks-log-group",
        name=f"/aws/eks/{name}/cluster",
        retention_in_days=retention_days,
        tags={
            **tags,
            "Name": f"{name}-eks-log-group",
            "Module": "eks"
        }
    )
    
    return {
        "log_group": log_group,
        "log_group_name": log_group.name
    }


def create_kms_key(name: str, existing_key_arn: str = "", tags: Dict[str, str] = None) -> str:
    """
    Create or use existing KMS key for EKS encryption
    
    Args:
        name: Cluster name
        existing_key_arn: ARN of existing KMS key
        tags: Additional tags
        
    Returns:
        KMS key ARN
    """
    if existing_key_arn:
        return existing_key_arn
    
    tags = tags or {}
    
    kms_key = aws.kms.Key(
        f"{name}-eks-kms-key",
        description=f"EKS Secret Encryption Key for {name}",
        tags={
            **tags,
            "Name": f"{name}-eks-kms-key",
            "Module": "eks"
        }
    )
    
    kms_alias = aws.kms.Alias(
        f"{name}-eks-kms-alias",
        name=f"alias/{name}-eks",
        target_key_id=kms_key.key_id
    )
    
    return kms_key.arn


def create_eks_cluster(name: str, version: str, role_arn: pulumi.Output[str],
                      subnet_ids: List[pulumi.Output[str]], security_group_ids: List[pulumi.Output[str]],
                      kms_key_arn: str, log_group_name: pulumi.Output[str],
                      enabled_log_types: List[str] = None,
                      endpoint_private_access: bool = False,
                      endpoint_public_access: bool = True,
                      public_access_cidrs: List[str] = None,
                      tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create EKS cluster
    
    Args:
        name: Cluster name
        version: Kubernetes version
        role_arn: IAM role ARN for cluster
        subnet_ids: List of subnet IDs
        security_group_ids: List of security group IDs
        kms_key_arn: KMS key ARN for encryption
        log_group_name: CloudWatch log group name
        enabled_log_types: List of enabled log types
        endpoint_private_access: Enable private API endpoint
        endpoint_public_access: Enable public API endpoint
        public_access_cidrs: List of CIDRs for public access
        tags: Additional tags
        
    Returns:
        Dict with cluster resource and outputs
    """
    tags = tags or {}
    enabled_log_types = enabled_log_types or ["api", "audit", "authenticator"]
    public_access_cidrs = public_access_cidrs or ["0.0.0.0/0"]
    
    cluster = aws.eks.Cluster(
        f"{name}-cluster",
        name=name,
        version=version,
        role_arn=role_arn,
        vpc_config=aws.eks.ClusterVpcConfigArgs(
            subnet_ids=subnet_ids,
            endpoint_private_access=endpoint_private_access,
            endpoint_public_access=endpoint_public_access,
            public_access_cidrs=public_access_cidrs,
            security_group_ids=security_group_ids
        ),
        enabled_cluster_log_types=enabled_log_types,
        encryption_config=aws.eks.ClusterEncryptionConfigArgs(
            provider=aws.eks.ClusterEncryptionConfigProviderArgs(
                key_arn=kms_key_arn
            ),
            resources=["secrets"]
        ),
        tags={
            **tags,
            "Name": f"{name}-cluster",
            "Module": "eks"
        }
    )
    
    return {
        "cluster": cluster,
        "cluster_id": cluster.id,
        "cluster_arn": cluster.arn,
        "cluster_endpoint": cluster.endpoint,
        "cluster_version": cluster.version,
        "cluster_certificate_authority_data": cluster.certificate_authority.data
    }


def create_node_group(name: str, cluster_name: pulumi.Output[str], role_arn: pulumi.Output[str],
                     subnet_ids: List[pulumi.Output[str]], node_security_group_id: pulumi.Output[str],
                     instance_types: List[str], desired_size: int, max_size: int, min_size: int,
                     disk_size: int, capacity_type: str = "ON_DEMAND",
                     tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create EKS managed node group
    
    Args:
        name: Node group name prefix
        cluster_name: EKS cluster name
        role_arn: IAM role ARN for node group
        subnet_ids: List of subnet IDs
        node_security_group_id: Security group ID for nodes
        instance_types: List of EC2 instance types
        desired_size: Desired number of nodes
        max_size: Maximum number of nodes
        min_size: Minimum number of nodes
        disk_size: EBS volume size in GB
        capacity_type: Capacity type (ON_DEMAND or SPOT)
        tags: Additional tags
        
    Returns:
        Dict with node group resource and outputs
    """
    tags = tags or {}
    
    node_group = aws.eks.NodeGroup(
        f"{name}-node-group",
        cluster_name=cluster_name,
        node_group_name=f"{name}-nodes",
        node_role_arn=role_arn,
        subnet_ids=subnet_ids,
        capacity_type=capacity_type,
        instance_types=instance_types,
        disk_size=disk_size,
        scaling_config=aws.eks.NodeGroupScalingConfigArgs(
            desired_size=desired_size,
            max_size=max_size,
            min_size=min_size
        ),
        update_config=aws.eks.NodeGroupUpdateConfigArgs(
            max_unavailable_percentage=25
        ),
        remote_access=aws.eks.NodeGroupRemoteAccessArgs(
            ec2_ssh_key=None,  # No SSH key for better security
            source_security_group_ids=[node_security_group_id]
        ),
        tags={
            **tags,
            "Name": f"{name}-node-group",
            "Module": "eks"
        }
    )
    
    return {
        "node_group": node_group,
        "node_group_arn": node_group.arn,
        "node_group_status": node_group.status
    }


def create_eks_addons(name: str, cluster_name: pulumi.Output[str],
                     enable_vpc_cni: bool = True,
                     enable_coredns: bool = True,
                     enable_kube_proxy: bool = True,
                     node_group=None,
                     tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create EKS add-ons
    
    Args:
        name: Cluster name
        cluster_name: EKS cluster name
        enable_vpc_cni: Enable VPC CNI addon
        enable_coredns: Enable CoreDNS addon
        enable_kube_proxy: Enable kube-proxy addon
        node_group: Node group dependency (for CoreDNS)
        tags: Additional tags
        
    Returns:
        Dict with addon resources
    """
    tags = tags or {}
    addons = {}
    
    if enable_vpc_cni:
        addons["vpc_cni"] = aws.eks.Addon(
            f"{name}-vpc-cni-addon",
            cluster_name=cluster_name,
            addon_name="vpc-cni",
            resolve_conflicts_on_create="OVERWRITE",
            resolve_conflicts_on_update="OVERWRITE",
            tags={
                **tags,
                "Name": f"{name}-vpc-cni-addon",
                "Module": "eks"
            }
        )
    
    if enable_coredns:
        opts = pulumi.ResourceOptions()
        if node_group:
            opts = pulumi.ResourceOptions(depends_on=[node_group])
            
        addons["coredns"] = aws.eks.Addon(
            f"{name}-coredns-addon",
            cluster_name=cluster_name,
            addon_name="coredns",
            resolve_conflicts_on_create="OVERWRITE",
            resolve_conflicts_on_update="OVERWRITE",
            tags={
                **tags,
                "Name": f"{name}-coredns-addon",
                "Module": "eks"
            },
            opts=opts
        )
    
    if enable_kube_proxy:
        addons["kube_proxy"] = aws.eks.Addon(
            f"{name}-kube-proxy-addon",
            cluster_name=cluster_name,
            addon_name="kube-proxy",
            resolve_conflicts_on_create="OVERWRITE",
            resolve_conflicts_on_update="OVERWRITE",
            tags={
                **tags,
                "Name": f"{name}-kube-proxy-addon",
                "Module": "eks"
            }
        )
    
    return {"addons": addons}


def create_eks_resources(cluster_name: str, cluster_version: str,
                        cluster_role_arn: pulumi.Output[str], node_group_role_arn: pulumi.Output[str],
                        subnet_ids: List[pulumi.Output[str]],
                        cluster_security_group_id: pulumi.Output[str],
                        node_security_group_id: pulumi.Output[str],
                        node_instance_types: List[str],
                        node_desired_size: int, node_max_size: int, node_min_size: int,
                        node_disk_size: int, capacity_type: str = "ON_DEMAND",
                        cluster_enabled_log_types: List[str] = None,
                        cloudwatch_log_group_retention_in_days: int = 30,
                        use_existing_kms_key: bool = False,
                        existing_kms_key_arn: str = "",
                        enable_vpc_cni_addon: bool = True,
                        enable_coredns_addon: bool = True,
                        enable_kube_proxy_addon: bool = True,
                        endpoint_private_access: bool = False,
                        endpoint_public_access: bool = True,
                        public_access_cidrs: List[str] = None,
                        tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create complete EKS infrastructure
    
    Args:
        cluster_name: EKS cluster name
        cluster_version: Kubernetes version
        cluster_role_arn: IAM role ARN for cluster
        node_group_role_arn: IAM role ARN for node group
        subnet_ids: List of subnet IDs
        cluster_security_group_id: Cluster security group ID
        node_security_group_id: Node security group ID
        node_instance_types: List of EC2 instance types
        node_desired_size: Desired number of nodes
        node_max_size: Maximum number of nodes
        node_min_size: Minimum number of nodes
        node_disk_size: EBS volume size in GB
        capacity_type: Capacity type (ON_DEMAND or SPOT)
        cluster_enabled_log_types: List of enabled log types
        cloudwatch_log_group_retention_in_days: Log retention in days
        use_existing_kms_key: Use existing KMS key
        existing_kms_key_arn: ARN of existing KMS key
        enable_vpc_cni_addon: Enable VPC CNI addon
        enable_coredns_addon: Enable CoreDNS addon
        enable_kube_proxy_addon: Enable kube-proxy addon
        endpoint_private_access: Enable private API endpoint
        endpoint_public_access: Enable public API endpoint
        public_access_cidrs: List of CIDRs for public access
        tags: Additional tags
        
    Returns:
        Dict with all EKS resources and outputs
    """
    tags = tags or {}
    
    # Create CloudWatch log group
    log_group_result = create_cloudwatch_log_group(
        cluster_name, 
        cloudwatch_log_group_retention_in_days, 
        tags
    )
    
    # Create or get KMS key
    kms_key_arn = create_kms_key(
        cluster_name,
        existing_kms_key_arn if use_existing_kms_key else "",
        tags
    )
    
    # Create EKS cluster
    cluster_result = create_eks_cluster(
        name=cluster_name,
        version=cluster_version,
        role_arn=cluster_role_arn,
        subnet_ids=subnet_ids,
        security_group_ids=[cluster_security_group_id],
        kms_key_arn=kms_key_arn,
        log_group_name=log_group_result["log_group_name"],
        enabled_log_types=cluster_enabled_log_types,
        endpoint_private_access=endpoint_private_access,
        endpoint_public_access=endpoint_public_access,
        public_access_cidrs=public_access_cidrs,
        tags=tags
    )
    
    # Create node group
    node_group_result = create_node_group(
        name=cluster_name,
        cluster_name=cluster_result["cluster"].name,
        role_arn=node_group_role_arn,
        subnet_ids=subnet_ids,
        node_security_group_id=node_security_group_id,
        instance_types=node_instance_types,
        desired_size=node_desired_size,
        max_size=node_max_size,
        min_size=node_min_size,
        disk_size=node_disk_size,
        capacity_type=capacity_type,
        tags=tags
    )
    
    # Create EKS addons
    addons_result = create_eks_addons(
        name=cluster_name,
        cluster_name=cluster_result["cluster"].name,
        enable_vpc_cni=enable_vpc_cni_addon,
        enable_coredns=enable_coredns_addon,
        enable_kube_proxy=enable_kube_proxy_addon,
        node_group=node_group_result["node_group"],
        tags=tags
    )
    
    return {
        "cluster_id": cluster_result["cluster_id"],
        "cluster_arn": cluster_result["cluster_arn"],
        "cluster_endpoint": cluster_result["cluster_endpoint"],
        "cluster_version_output": cluster_result["cluster_version"],
        "cluster_certificate_authority_data": cluster_result["cluster_certificate_authority_data"],
        "node_group_arn": node_group_result["node_group_arn"],
        "node_group_status": node_group_result["node_group_status"],
        # Keep references to resources for dependencies
        "_log_group": log_group_result["log_group"],
        "_cluster": cluster_result["cluster"],
        "_node_group": node_group_result["node_group"],
        "_addons": addons_result["addons"]
    }