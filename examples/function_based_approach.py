#!/usr/bin/env python3
"""
Example: Using the new function-based Pulumi modules
This shows how to use the refactored modules in a declarative style
"""

import pulumi
from config import get_config
from modules.vpc.functions import create_vpc_resources
from modules.iam.functions import create_iam_resources
from modules.eks.functions import create_eks_resources
from modules.addons.functions import create_addons_resources
from modules.state_storage.functions import create_state_storage_resources


def main():
    """Example of using function-based modules"""
    
    # Get configuration
    config = get_config()
    
    # Create VPC infrastructure using function-based approach
    vpc_resources = create_vpc_resources(
        cluster_name=config.cluster_name,
        vpc_cidr=config.vpc_cidr,
        public_subnet_cidrs=config.public_subnet_cidrs,
        enable_dns_hostnames=config.enable_dns_hostnames,
        enable_dns_support=config.enable_dns_support,
        map_public_ip_on_launch=config.map_public_ip_on_launch,
        tags=config.common_tags
    )
    
    # Create IAM resources using function-based approach
    iam_resources = create_iam_resources(
        cluster_name=config.cluster_name,
        use_existing_cluster_role=config.use_existing_cluster_role,
        existing_cluster_role_name=config.existing_cluster_role_name,
        use_existing_node_role=config.use_existing_node_role,
        existing_node_role_name=config.existing_node_role_name,
        tags=config.common_tags
    )
    
    # Create EKS cluster and node groups using function-based approach
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
    
    # Create Kubernetes addons using function-based approach
    addons_resources = create_addons_resources(
        cluster_name=config.cluster_name,
        cluster_endpoint=eks_resources["cluster_endpoint"],
        cluster_ca_data=eks_resources["cluster_certificate_authority_data"],
        enable_metrics_server=True,
        enable_aws_load_balancer_controller=False,
        enable_test_deployment=True,
        tags=config.common_tags
    )
    
    # Create state storage resources using function-based approach (optional)
    # state_storage_resources = create_state_storage_resources(
    #     cluster_name=config.cluster_name,
    #     aws_region=config.aws_region,
    #     tags=config.common_tags
    # )
    
    # Export stack outputs
    pulumi.export("cluster_info", {
        "cluster_name": config.cluster_name,
        "cluster_endpoint": eks_resources["cluster_endpoint"],
        "cluster_arn": eks_resources["cluster_arn"],
        "cluster_version": eks_resources["cluster_version_output"],
    })
    
    pulumi.export("vpc_info", {
        "vpc_id": vpc_resources["vpc_id"],
        "vpc_cidr_block": vpc_resources["vpc_cidr_block"],
        "public_subnet_ids": vpc_resources["public_subnet_ids"],
        "availability_zones": vpc_resources["availability_zones"]
    })
    
    pulumi.export("iam_info", {
        "cluster_role_arn": iam_resources["cluster_role_arn"],
        "node_group_role_arn": iam_resources["node_group_role_arn"]
    })
    
    # Show the cleaner, more declarative approach
    print("✅ Function-based modules provide:")
    print("  - Clear separation of concerns")
    print("  - Simple function calls vs complex class instantiation")
    print("  - Explicit input/output contracts")
    print("  - Easy testing and mocking")
    print("  - Better code reusability")


if __name__ == "__main__":
    main()