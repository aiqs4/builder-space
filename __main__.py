"""
Production EKS Cluster - KISS Architecture
Organized by concern, minimal config, production-ready
"""
import pulumi
from src.network import create_network
from src.cluster import create_cluster
from src.addons import install_addons
from src.database import create_database
from src.external_dns import setup_external_dns
from src.karpenter import setup_karpenter

# Configuration
config = pulumi.Config()
github_role = config.get("github_actions_role_arn")
db_password = config.require_secret("db_password")

# Domains for External DNS
DOMAINS = [
    "amano.services",
    "tekanya.services",
    "lightsphere.space",
    "sosolola.cloud"
]

# 1. Network infrastructure
network = create_network()

# 2. EKS Cluster
cluster_info = create_cluster(network, github_role)

# 3. Essential EKS Add-ons (auto-configured by AWS)
addons = install_addons(cluster_info)

# 4. Database
database = create_database(network)

# 5. External DNS for automatic DNS management
external_dns = setup_external_dns(cluster_info, DOMAINS)

# 6. Karpenter for efficient autoscaling
karpenter = setup_karpenter(cluster_info, network)

# Exports
pulumi.export("cluster_name", cluster_info["cluster_name"])
pulumi.export("cluster_endpoint", cluster_info["cluster"].endpoint)
pulumi.export("vpc_id", network["vpc"].id)
pulumi.export("database_endpoint", database["endpoint"])
pulumi.export("kubeconfig_command", 
    pulumi.Output.concat(
        "aws eks update-kubeconfig --region af-south-1 --name ",
        cluster_info["cluster_name"]
    ))
pulumi.export("addons_installed", list(addons.keys()))
pulumi.export("external_dns_domains", DOMAINS)