"""
Builder Space EKS - Pulumi Python Implementation
Pure declarative Infrastructure as Code
"""

import pulumi
import pulumi_aws as aws
from config import get_config

# Get configuration
config = get_config()

# Get current AWS account info
current = aws.get_caller_identity()
region = aws.get_region()

# Import all modules - they will execute their resource declarations
import modules.vpc as vpc_module
import modules.iam as iam_module
import modules.eks as eks_module
import modules.addons as addons_module
import modules.state_storage as state_storage_module

# Export outputs for compatibility with Terraform

# Individual resource outputs
pulumi.export("cluster_id", eks_module.cluster_id)
pulumi.export("cluster_arn", eks_module.cluster_arn)
pulumi.export("cluster_name", pulumi.Output.from_input(config.cluster_name))
pulumi.export("cluster_endpoint", eks_module.cluster_endpoint)
pulumi.export("cluster_version", eks_module.cluster_version)
pulumi.export("cluster_certificate_authority_data", eks_module.cluster_certificate_authority_data)

# Grouped outputs for better organization
pulumi.export("cluster_info", {
    "cluster_name": config.cluster_name,
    "cluster_endpoint": eks_module.cluster_endpoint,
    "cluster_arn": eks_module.cluster_arn,
    "cluster_version": eks_module.cluster_version,
    "region": region.id,
    "account_id": current.account_id
})

pulumi.export("vpc_info", {
    "vpc_id": vpc_module.vpc_id,
    "vpc_cidr_block": vpc_module.vpc_cidr_block,
    "public_subnet_ids": vpc_module.public_subnet_ids,
    "availability_zones": vpc_module.availability_zones
})

pulumi.export("iam_info", {
    "cluster_role_arn": iam_module.cluster_role_arn,
    "cluster_role_name": iam_module.cluster_role_name,
    "node_group_role_arn": iam_module.node_group_role_arn,
    "node_group_role_name": iam_module.node_group_role_name
})

# Compatibility outputs for existing scripts
pulumi.export("vpc_id", vpc_module.vpc_id)
pulumi.export("vpc_cidr_block", vpc_module.vpc_cidr_block)
pulumi.export("public_subnet_ids", vpc_module.public_subnet_ids)
pulumi.export("cluster_security_group_id", vpc_module.cluster_security_group_id)
pulumi.export("node_security_group_id", vpc_module.node_group_security_group_id)
pulumi.export("cluster_iam_role_arn", iam_module.cluster_role_arn)
pulumi.export("node_group_iam_role_arn", iam_module.node_group_role_arn)
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
        "metrics_server": addons_module.metrics_server_status,
        "aws_load_balancer_controller": addons_module.aws_load_balancer_controller_status,
        "test_deployment": "✅ Deployed" if addons_module.test_deployment_name else "❌ Not deployed"
    }
})