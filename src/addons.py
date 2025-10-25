"""
EKS Add-ons
Managed add-ons are auto-configured by AWS - no manual IRSA needed!
"""
import pulumi_aws as aws
from . import cluster

# Amazon VPC CNI - networking (auto-configured)
vpc_cni = aws.eks.Addon("vpc-cni",
    cluster_name=cluster.cluster.name,
    addon_name="vpc-cni",
    addon_version="v1.18.5-eksbuild.1",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="OVERWRITE")

# CoreDNS - DNS resolution (auto-configured)
coredns = aws.eks.Addon("coredns",
    cluster_name=cluster.cluster.name,
    addon_name="coredns",
    addon_version="v1.11.3-eksbuild.2",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="OVERWRITE")

# Amazon EKS Pod Identity Agent - modern IRSA replacement (auto-configured)
pod_identity = aws.eks.Addon("pod-identity-agent",
    cluster_name=cluster.cluster.name,
    addon_name="eks-pod-identity-agent",
    addon_version="v1.3.4-eksbuild.1",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="OVERWRITE")

# Amazon EBS CSI Driver - persistent volumes (auto-configured)
ebs_csi = aws.eks.Addon("ebs-csi-driver",
    cluster_name=cluster.cluster.name,
    addon_name="aws-ebs-csi-driver",
    addon_version="v1.37.0-eksbuild.1",
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="OVERWRITE")
