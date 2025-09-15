"""
Builder Space EKS - Pulumi Python Implementation
A cost-optimized, modular EKS deployment with comprehensive features
"""

import pulumi
import pulumi_aws as aws
from config import get_config
from modules.vpc import VPCResources
from modules.iam import IAMResources
from modules.eks import EKSResources
from modules.addons import AddonsResources
from modules.state_storage import StateStorageResources

def main():
    """Main deployment function"""
    
    # Get configuration
    config = get_config()
    
    # Get current AWS account info
    current = aws.get_caller_identity()
    region = aws.get_region()
    
    # Create VPC resources
    vpc = VPCResources(
        cluster_name=config.cluster_name,
        vpc_cidr=config.vpc_cidr,
        public_subnet_cidrs=config.public_subnet_cidrs,
        enable_dns_hostnames=config.enable_dns_hostnames,
        enable_dns_support=config.enable_dns_support,
        map_public_ip_on_launch=config.map_public_ip_on_launch,
        tags=config.common_tags
    )
    
    # Create IAM resources
    iam = IAMResources(
        cluster_name=config.cluster_name,
        use_existing_cluster_role=config.use_existing_cluster_role,
        existing_cluster_role_name=config.existing_cluster_role_name,
        use_existing_node_role=config.use_existing_node_role,
        existing_node_role_name=config.existing_node_role_name,
        tags=config.common_tags
    )
    
    # Create EKS resources
    eks = EKSResources(
        cluster_name=config.cluster_name,
        cluster_version=config.cluster_version,
        cluster_role_arn=iam.cluster_role_arn,
        node_group_role_arn=iam.node_group_role_arn,
        subnet_ids=vpc.public_subnet_ids,
        cluster_security_group_id=vpc.cluster_security_group_id,
        node_security_group_id=vpc.node_group_security_group_id,
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
    addons = AddonsResources(
        cluster_name=config.cluster_name,
        cluster_endpoint=eks.cluster_endpoint,
        cluster_ca_data=eks.cluster_certificate_authority_data,
        enable_metrics_server=True,
        enable_aws_load_balancer_controller=False,  # Requires additional IAM setup
        enable_test_deployment=True,
        tags=config.common_tags
    )
    
    # Export outputs for compatibility with Terraform
    
    # Individual resource outputs
    pulumi.export("cluster_id", eks.cluster_id)
    pulumi.export("cluster_arn", eks.cluster_arn)
    pulumi.export("cluster_name", pulumi.Output.from_input(config.cluster_name))
    pulumi.export("cluster_endpoint", eks.cluster_endpoint)
    pulumi.export("cluster_version", eks.cluster_version_output)
    pulumi.export("cluster_certificate_authority_data", eks.cluster_certificate_authority_data)
    
    # Grouped outputs for better organization
    pulumi.export("cluster_info", {
        "cluster_name": config.cluster_name,
        "cluster_endpoint": eks.cluster_endpoint,
        "cluster_arn": eks.cluster_arn,
        "cluster_version": eks.cluster_version_output,
        "region": region.id,
        "account_id": current.account_id
    })
    
    pulumi.export("vpc_info", {
        "vpc_id": vpc.vpc_id,
        "vpc_cidr_block": vpc.vpc_cidr_block,
        "public_subnet_ids": vpc.public_subnet_ids,
        "availability_zones": vpc.availability_zones
    })
    
    pulumi.export("iam_info", {
        "cluster_role_arn": iam.cluster_role_arn,
        "cluster_role_name": iam.cluster_role_name,
        "node_group_role_arn": iam.node_group_role_arn,
        "node_group_role_name": iam.node_group_role_name
    })
    
    # Compatibility outputs for existing scripts
    pulumi.export("vpc_id", vpc.vpc_id)
    pulumi.export("vpc_cidr_block", vpc.vpc_cidr_block)
    pulumi.export("public_subnet_ids", vpc.public_subnet_ids)
    pulumi.export("cluster_security_group_id", vpc.cluster_security_group_id)
    pulumi.export("node_security_group_id", vpc.node_group_security_group_id)
    pulumi.export("cluster_iam_role_arn", iam.cluster_role_arn)
    pulumi.export("node_group_iam_role_arn", iam.node_group_role_arn)
    pulumi.export("region", config.aws_region)
    
    # kubectl configuration command
    pulumi.export("kubectl_config_command", 
                  f"aws eks --region {config.aws_region} update-kubeconfig --name {config.cluster_name}")
    
    # Next steps and commands
    pulumi.export("next_steps", [
        f"1. Configure kubectl: aws eks --region {config.aws_region} update-kubeconfig --name {config.cluster_name}",
        "2. Verify nodes: kubectl get nodes",
        "3. Check system pods: kubectl get pods -n kube-system",
        "4. Test internet connectivity: kubectl logs -n test deployment/test-internet-app",
        "5. Verify metrics server: kubectl top nodes",
        "6. View estimated costs below"
    ])
    
    pulumi.export("test_commands", [
        "# Check cluster status",
        "kubectl cluster-info",
        "",
        "# Check nodes",
        "kubectl get nodes -o wide",
        "",
        "# Check system pods",
        "kubectl get pods -n kube-system",
        "",
        "# Test internet connectivity",
        "kubectl logs -n test deployment/test-internet-app --tail=10",
        "",
        "# Check resource usage",
        "kubectl top nodes",
        "kubectl top pods -A"
    ])
    
    # Cost estimation with optimization info
    node_cost = "~$8.64" if config.enable_spot_instances else "~$28.80"
    capacity_info = f"({config.node_desired_size}x {', '.join(config.optimized_instance_types)} {'spot' if config.enable_spot_instances else 'on-demand'} instances)"
    total_cost = "~$88-95/month (with spot instances)" if config.enable_spot_instances else "~$108-115/month (on-demand instances)"
    savings_info = "Current: Using spot instances" if config.enable_spot_instances else "Potential: Enable spot instances to save ~$20/month"
    
    pulumi.export("estimated_monthly_cost", {
        "eks_cluster_cost": "$72.00",
        "node_group_cost": f"{node_cost} {capacity_info}",
        "storage_cost": f"~${config.node_desired_size * config.node_disk_size * 0.10}",
        "total_estimated": total_cost,
        "savings_potential": savings_info
    })
    
    # Configuration summary
    pulumi.export("configuration_summary", {
        "cluster_name": config.cluster_name,
        "cluster_version": config.cluster_version,
        "node_instance_types": config.optimized_instance_types,
        "capacity_type": config.capacity_type,
        "node_count": f"{config.node_min_size}-{config.node_max_size} (desired: {config.node_desired_size})",
        "cost_optimizations": {
            "spot_instances": "✅ Enabled" if config.enable_spot_instances else "❌ Disabled (enable for ~70% savings)",
            "reserved_instances": "✅ Enabled" if config.enable_reserved_instances else "❌ Disabled",
            "cluster_autoscaler": "✅ Enabled" if config.enable_cluster_autoscaler else "❌ Disabled",
            "scheduled_scaling": "✅ Enabled" if config.enable_scheduled_scaling else "❌ Disabled"
        },
        "addons_status": {
            "metrics_server": addons.metrics_server_status,
            "aws_load_balancer_controller": addons.aws_load_balancer_controller_status,
            "test_deployment": "✅ Deployed" if addons.test_deployment_name else "❌ Not deployed"
        }
    })

if __name__ == "__main__":
    main()
