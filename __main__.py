"""
Production EKS Cluster - KISS Architecture
Pure declarative Pulumi - no functions, just imports
"""
import pulumi
from src import network, cluster, addons, database, external_dns, karpenter

# Exports
pulumi.export("cluster_name", cluster.cluster_name)
pulumi.export("cluster_endpoint", cluster.cluster.endpoint)
pulumi.export("vpc_id", network.vpc.id)
pulumi.export("database_endpoint", database.aurora_cluster.endpoint)
pulumi.export("kubeconfig_command", 
    pulumi.Output.concat(
        "aws eks update-kubeconfig --region af-south-1 --name ",
        cluster.cluster_name
    ))