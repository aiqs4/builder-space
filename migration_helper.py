#!/usr/bin/env python3
"""
Migration Script: From Class-based to Function-based Pulumi Modules
This script helps migrate existing Pulumi deployments to use the new function-based approach
"""

import pulumi
import pulumi_aws as aws
from typing import Dict, Any
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config

# Import both old and new approaches for comparison
from modules.vpc import VPCResources
from modules.iam import IAMResources
from modules.eks import EKSResources
from modules.addons import AddonsResources
from modules.state_storage import StateStorageResources

from modules.vpc.functions import create_vpc_resources
from modules.iam.functions import create_iam_resources
from modules.eks.functions import create_eks_resources
from modules.addons.functions import create_addons_resources
from modules.state_storage.functions import create_state_storage_resources


def import_existing_resources():
    """
    Utility to help import existing resources into Pulumi state
    This should be run before migrating to ensure resources are properly tracked
    """
    config = get_config()
    
    print("🔧 Resource Import Helper")
    print("========================")
    print("This helper will generate `pulumi import` commands for existing resources.")
    print("Run these commands before migrating to function-based modules.\n")
    
    cluster_name = config.cluster_name
    region = config.aws_region
    
    # Generate import commands based on expected resource names
    import_commands = [
        "# Import existing AWS resources (run these commands in order):",
        "",
        "# VPC Resources:",
        f"pulumi import aws:ec2/vpc:Vpc {cluster_name}-vpc vpc-XXXXXXXX",
        f"pulumi import aws:ec2/internetGateway:InternetGateway {cluster_name}-igw igw-XXXXXXXX",
        f"pulumi import aws:ec2/subnet:Subnet {cluster_name}-public-subnet-1 subnet-XXXXXXXX",
        f"pulumi import aws:ec2/subnet:Subnet {cluster_name}-public-subnet-2 subnet-XXXXXXXX",
        f"pulumi import aws:ec2/routeTable:RouteTable {cluster_name}-public-rt rtb-XXXXXXXX",
        f"pulumi import aws:ec2/securityGroup:SecurityGroup {cluster_name}-cluster-sg sg-XXXXXXXX",
        f"pulumi import aws:ec2/securityGroup:SecurityGroup {cluster_name}-node-sg sg-XXXXXXXX",
        "",
        "# IAM Resources:",
        f"pulumi import aws:iam/role:Role {cluster_name}-cluster-role {cluster_name}-cluster-role",
        f"pulumi import aws:iam/role:Role {cluster_name}-ng-role {cluster_name}-ng-role",
        "",
        "# EKS Resources:",
        f"pulumi import aws:eks/cluster:Cluster {cluster_name}-cluster {cluster_name}",
        f"pulumi import aws:eks/nodeGroup:NodeGroup {cluster_name}-node-group {cluster_name}:{cluster_name}-nodes",
        "",
        "# State Storage Resources (if using):",
        f"pulumi import aws:s3/bucket:Bucket {cluster_name}-pulumi-state-bucket {cluster_name}-pulumi-state-{region}",
        f"pulumi import aws:dynamodb/table:Table {cluster_name}-pulumi-state-lock-table {cluster_name}-pulumi-state-lock",
        "",
        "# Instructions:",
        "1. Replace XXXXXXXX with actual AWS resource IDs",
        "2. Get resource IDs from AWS Console or CLI:",
        "   aws ec2 describe-vpcs --filters Name=tag:Name,Values=<cluster-name>-vpc",
        "   aws eks describe-cluster --name <cluster-name>",
        "3. Run import commands one by one",
        "4. Verify with: pulumi preview (should show no changes)",
    ]
    
    for command in import_commands:
        print(command)
    
    print("\n📝 To get actual resource IDs, run:")
    print(f"aws ec2 describe-vpcs --filters Name=tag:Name,Values={cluster_name}-vpc --query 'Vpcs[0].VpcId'")
    print(f"aws eks describe-cluster --name {cluster_name} --query 'cluster.arn'")


def compare_approaches():
    """
    Compare the old class-based approach with the new function-based approach
    """
    print("📊 Approach Comparison")
    print("=====================")
    
    print("\n🏗️ OLD: Class-based Approach")
    print("-----------------------------")
    print("""
# Heavy, stateful classes
vpc = VPCResources(
    cluster_name="my-cluster",
    vpc_cidr="10.0.0.0/16",
    public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"],
    tags=tags
)

# Access via properties
vpc_id = vpc.vpc_id
subnet_ids = vpc.public_subnet_ids

# Issues:
- Large class constructors with many parameters
- Hidden resource creation logic
- Difficult to test individual components
- Complex state management
- Hard to understand resource dependencies
""")
    
    print("\n✨ NEW: Function-based Approach")
    print("--------------------------------")
    print("""
# Simple function calls
vpc_resources = create_vpc_resources(
    cluster_name="my-cluster",
    vpc_cidr="10.0.0.0/16",
    public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"],
    tags=tags
)

# Access via dictionary keys
vpc_id = vpc_resources["vpc_id"]
subnet_ids = vpc_resources["public_subnet_ids"]

# Benefits:
- Clear input/output contracts
- Small, focused functions
- Easy to test and mock
- Explicit dependencies
- Better composability
- Follows Pulumi best practices
""")
    
    print("\n🔄 Migration Path")
    print("-----------------")
    print("""
1. Import existing resources (if any)
2. Update __main__.py to use function calls
3. Test with pulumi preview
4. Deploy changes
5. Remove legacy class wrappers (optional)

The legacy classes still work during transition!
""")


def generate_new_main_py():
    """
    Generate a new __main__.py using the function-based approach
    """
    print("📄 New __main__.py Template")
    print("===========================")
    
    template = '''"""
Builder Space EKS - Pulumi Python Implementation (Function-based)
A cost-optimized, modular EKS deployment with comprehensive features
"""

import pulumi
import pulumi_aws as aws
from config import get_config
from modules.vpc.functions import create_vpc_resources
from modules.iam.functions import create_iam_resources
from modules.eks.functions import create_eks_resources
from modules.addons.functions import create_addons_resources

def main():
    """Main deployment function using function-based modules"""
    
    # Get configuration
    config = get_config()
    
    # Get current AWS account info
    current = aws.get_caller_identity()
    region = aws.get_region()
    
    # Create VPC resources
    vpc_resources = create_vpc_resources(
        cluster_name=config.cluster_name,
        vpc_cidr=config.vpc_cidr,
        public_subnet_cidrs=config.public_subnet_cidrs,
        enable_dns_hostnames=config.enable_dns_hostnames,
        enable_dns_support=config.enable_dns_support,
        map_public_ip_on_launch=config.map_public_ip_on_launch,
        tags=config.common_tags
    )
    
    # Create IAM resources
    iam_resources = create_iam_resources(
        cluster_name=config.cluster_name,
        use_existing_cluster_role=config.use_existing_cluster_role,
        existing_cluster_role_name=config.existing_cluster_role_name,
        use_existing_node_role=config.use_existing_node_role,
        existing_node_role_name=config.existing_node_role_name,
        tags=config.common_tags
    )
    
    # Create EKS resources
    eks_resources = create_eks_resources(
        cluster_name=config.cluster_name,
        cluster_version=config.cluster_version,
        cluster_role_arn=iam_resources["cluster_role_arn"],
        node_group_role_arn=iam_resources["node_group_role_arn"],
        subnet_ids=vpc_resources["public_subnet_ids"],
        cluster_security_group_id=vpc_resources["cluster_security_group_id"],
        node_security_group_id=vpc_resources["node_group_security_group_id"],
        node_instance_types=config.optimized_instance_types,
        node_desired_size=config.node_desired_size,
        node_max_size=config.node_max_size,
        node_min_size=config.node_min_size,
        node_disk_size=config.node_disk_size,
        capacity_type=config.capacity_type,
        cluster_enabled_log_types=config.cluster_enabled_log_types,
        cloudwatch_log_group_retention_in_days=config.cloudwatch_log_group_retention_in_days,
        use_existing_kms_key=config.use_existing_kms_key,
        existing_kms_key_arn=config.existing_kms_key_arn,
        enable_vpc_cni_addon=config.enable_vpc_cni_addon,
        enable_coredns_addon=config.enable_coredns_addon,
        enable_kube_proxy_addon=config.enable_kube_proxy_addon,
        tags=config.common_tags
    )
    
    # Create addons resources
    addons_resources = create_addons_resources(
        cluster_name=config.cluster_name,
        cluster_endpoint=eks_resources["cluster_endpoint"],
        cluster_ca_data=eks_resources["cluster_certificate_authority_data"],
        enable_metrics_server=True,
        enable_aws_load_balancer_controller=False,
        enable_test_deployment=True,
        tags=config.common_tags
    )
    
    # Export outputs (same as before)
    pulumi.export("cluster_info", {
        "cluster_name": config.cluster_name,
        "cluster_endpoint": eks_resources["cluster_endpoint"],
        "cluster_arn": eks_resources["cluster_arn"],
        "cluster_version": eks_resources["cluster_version_output"],
        "region": region.id,
        "account_id": current.account_id
    })
    
    pulumi.export("vpc_info", {
        "vpc_id": vpc_resources["vpc_id"],
        "vpc_cidr_block": vpc_resources["vpc_cidr_block"],
        "public_subnet_ids": vpc_resources["public_subnet_ids"],
        "availability_zones": vpc_resources["availability_zones"]
    })
    
    pulumi.export("iam_info", {
        "cluster_role_arn": iam_resources["cluster_role_arn"],
        "cluster_role_name": iam_resources["cluster_role_name"],
        "node_group_role_arn": iam_resources["node_group_role_arn"],
        "node_group_role_name": iam_resources["node_group_role_name"]
    })

if __name__ == "__main__":
    main()
'''
    
    print(template)
    
    print("\n💾 To use this template:")
    print("1. Save as '__main__.py.new'")
    print("2. Backup current '__main__.py'")
    print("3. Replace '__main__.py' with the new version")
    print("4. Run 'pulumi preview' to verify")


def main():
    """Main migration helper"""
    print("🚀 Pulumi Module Migration Helper")
    print("==================================")
    print("This tool helps migrate from class-based to function-based Pulumi modules.")
    print()
    
    while True:
        print("Choose an option:")
        print("1. Show approach comparison")
        print("2. Generate import commands for existing resources")
        print("3. Generate new __main__.py template")
        print("4. Exit")
        print()
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            compare_approaches()
        elif choice == "2":
            import_existing_resources()
        elif choice == "3":
            generate_new_main_py()
        elif choice == "4":
            print("👋 Happy migrating!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")
        
        print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    main()