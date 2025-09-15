"""
EKS Module
Creates EKS cluster and managed node groups
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, List, Optional

class EKSResources:
    """EKS cluster and node group resources"""
    
    def __init__(self,
                 cluster_name: str,
                 cluster_version: str,
                 cluster_role_arn: pulumi.Output[str],
                 node_group_role_arn: pulumi.Output[str],
                 subnet_ids: List[pulumi.Output[str]],
                 cluster_security_group_id: pulumi.Output[str],
                 node_security_group_id: pulumi.Output[str],
                 node_instance_types: List[str],
                 node_desired_size: int,
                 node_max_size: int,
                 node_min_size: int,
                 node_disk_size: int,
                 capacity_type: str = "ON_DEMAND",
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
                 tags: Dict[str, str] = None):
        
        self.cluster_name = cluster_name
        self.tags = tags or {}
        
        if cluster_enabled_log_types is None:
            cluster_enabled_log_types = ["api", "audit", "authenticator"]
        
        if public_access_cidrs is None:
            public_access_cidrs = ["0.0.0.0/0"]
        
        # CloudWatch Log Group for EKS cluster
        self.log_group = aws.cloudwatch.LogGroup(
            f"{cluster_name}-eks-log-group",
            name=f"/aws/eks/{cluster_name}/cluster",
            retention_in_days=cloudwatch_log_group_retention_in_days,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-eks-log-group",
                "Module": "eks"
            }
        )
        
        # KMS Key for EKS encryption (optional)
        if use_existing_kms_key and existing_kms_key_arn:
            self.kms_key_arn = existing_kms_key_arn
        else:
            self.kms_key = aws.kms.Key(
                f"{cluster_name}-eks-kms-key",
                description=f"EKS Secret Encryption Key for {cluster_name}",
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-eks-kms-key",
                    "Module": "eks"
                }
            )
            
            self.kms_alias = aws.kms.Alias(
                f"{cluster_name}-eks-kms-alias",
                name=f"alias/{cluster_name}-eks",
                target_key_id=self.kms_key.key_id
            )
            
            self.kms_key_arn = self.kms_key.arn
        
        # EKS Cluster
        self.cluster = aws.eks.Cluster(
            f"{cluster_name}-cluster",
            name=cluster_name,
            version=cluster_version,
            role_arn=cluster_role_arn,
            vpc_config=aws.eks.ClusterVpcConfigArgs(
                subnet_ids=subnet_ids,
                endpoint_private_access=endpoint_private_access,
                endpoint_public_access=endpoint_public_access,
                public_access_cidrs=public_access_cidrs,
                security_group_ids=[cluster_security_group_id]
            ),
            enabled_cluster_log_types=cluster_enabled_log_types,
            encryption_config=aws.eks.ClusterEncryptionConfigArgs(
                provider=aws.eks.ClusterEncryptionConfigProviderArgs(
                    key_arn=self.kms_key_arn
                ),
                resources=["secrets"]
            ),
            tags={
                **self.tags,
                "Name": f"{cluster_name}-cluster",
                "Module": "eks"
            },
            opts=pulumi.ResourceOptions(depends_on=[self.log_group])
        )
        
        # EKS Node Group
        self.node_group = aws.eks.NodeGroup(
            f"{cluster_name}-node-group",
            cluster_name=self.cluster.name,
            node_group_name=f"{cluster_name}-nodes",
            node_role_arn=node_group_role_arn,
            subnet_ids=subnet_ids,
            capacity_type=capacity_type,
            instance_types=node_instance_types,
            disk_size=node_disk_size,
            scaling_config=aws.eks.NodeGroupScalingConfigArgs(
                desired_size=node_desired_size,
                max_size=node_max_size,
                min_size=node_min_size
            ),
            update_config=aws.eks.NodeGroupUpdateConfigArgs(
                max_unavailable_percentage=25
            ),
            remote_access=aws.eks.NodeGroupRemoteAccessArgs(
                ec2_ssh_key=None,  # No SSH key for better security
                source_security_group_ids=[node_security_group_id]
            ) if node_security_group_id else None,
            tags={
                **self.tags,
                "Name": f"{cluster_name}-node-group",
                "Module": "eks"
            },
            opts=pulumi.ResourceOptions(depends_on=[self.cluster])
        )
        
        # EKS Add-ons
        self.addons = {}
        
        if enable_vpc_cni_addon:
            self.addons["vpc_cni"] = aws.eks.Addon(
                f"{cluster_name}-vpc-cni-addon",
                cluster_name=self.cluster.name,
                addon_name="vpc-cni",
                resolve_conflicts_on_create="OVERWRITE",
                resolve_conflicts_on_update="OVERWRITE",
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-vpc-cni-addon",
                    "Module": "eks"
                }
            )
        
        if enable_coredns_addon:
            self.addons["coredns"] = aws.eks.Addon(
                f"{cluster_name}-coredns-addon",
                cluster_name=self.cluster.name,
                addon_name="coredns",
                resolve_conflicts_on_create="OVERWRITE",
                resolve_conflicts_on_update="OVERWRITE",
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-coredns-addon",
                    "Module": "eks"
                },
                opts=pulumi.ResourceOptions(depends_on=[self.node_group])
            )
        
        if enable_kube_proxy_addon:
            self.addons["kube_proxy"] = aws.eks.Addon(
                f"{cluster_name}-kube-proxy-addon",
                cluster_name=self.cluster.name,
                addon_name="kube-proxy",
                resolve_conflicts_on_create="OVERWRITE",
                resolve_conflicts_on_update="OVERWRITE",
                tags={
                    **self.tags,
                    "Name": f"{cluster_name}-kube-proxy-addon",
                    "Module": "eks"
                }
            )
    
    @property
    def cluster_id(self) -> pulumi.Output[str]:
        """Get cluster ID"""
        return self.cluster.id
    
    @property
    def cluster_arn(self) -> pulumi.Output[str]:
        """Get cluster ARN"""
        return self.cluster.arn
    
    @property
    def cluster_endpoint(self) -> pulumi.Output[str]:
        """Get cluster endpoint"""
        return self.cluster.endpoint
    
    @property
    def cluster_version_output(self) -> pulumi.Output[str]:
        """Get cluster version"""
        return self.cluster.version
    
    @property
    def cluster_certificate_authority_data(self) -> pulumi.Output[str]:
        """Get cluster certificate authority data"""
        return self.cluster.certificate_authority.data
    
    @property
    def node_group_arn(self) -> pulumi.Output[str]:
        """Get node group ARN"""
        return self.node_group.arn
    
    @property
    def node_group_status(self) -> pulumi.Output[str]:
        """Get node group status"""
        return self.node_group.status