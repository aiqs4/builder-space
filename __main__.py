"""
Production EKS Cluster - KISS Architecture
Pure declarative Pulumi - AWS-managed add-ons only
"""
import pulumi
from src import network, cluster, addons

# Exports
pulumi.export("cluster_name", cluster.cluster_name)
pulumi.export("cluster_endpoint", cluster.cluster.endpoint)
pulumi.export("vpc_id", network.vpc.id)
pulumi.export("subnet_1_id", network.subnet_ids[0])
pulumi.export("subnet_2_id", network.subnet_ids[1])
pulumi.export("subnet_3_id", network.subnet_ids[2])
pulumi.export("kubeconfig_command", 
    pulumi.Output.concat(
        "aws eks update-kubeconfig --region af-south-1 --name ",
        cluster.cluster_name
    ))
pulumi.export("add_ons", ["vpc-cni", "coredns", "pod-identity-agent", "ebs-csi-driver", "external-dns", "cert-manager"])