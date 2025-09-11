# Builder Space - Low-Cost Amazon EKS Cluster

This repository provides Terraform infrastructure for provisioning a cost-optimized Amazon EKS cluster in South Africa (af-south-1) for development purposes.

## 🎯 Overview

This infrastructure creates:
- **EKS Cluster**: Managed Kubernetes control plane
- **Node Group**: 2-node managed node group using ARM-based t4g.small instances
- **VPC**: Public subnets configuration (no NAT Gateway for cost savings)
- **Networking**: Direct internet access for pods
- **Add-ons**: metrics-server, VPC CNI, CoreDNS, kube-proxy, EBS CSI driver
- **Testing**: Sample deployment to verify internet connectivity

## 💰 Cost Optimization

**Target Monthly Cost: < $100 USD**

Estimated breakdown:
- EKS Cluster: ~$72/month ($0.10/hour)
- Node Group (2 x t4g.small): ~$29/month ($0.0192/hour each in af-south-1)
- EBS Storage (40GB total): ~$8/month ($0.20/GB/month)
- **Total: ~$109/month**

Cost-saving features:
- ✅ ARM-based instances (t4g.small) for better price/performance
- ✅ Public subnets only (no NAT Gateway costs)
- ✅ Minimal node count (2 nodes)
- ✅ Small EBS volumes (20GB per node)
- ✅ South Africa region for proximity

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** (>= 1.0)
3. **kubectl** for cluster management

### Deployment Options

#### Option 1: GitHub Actions (Recommended)
See `GITHUB_ACTIONS.md` for OIDC setup, then deploy via Actions workflow.

#### Option 2: Local Deployment

1. **Clone and navigate to the repository**:
```bash
git clone <repository-url>
cd builder-space
```

2. **Configure variables** (optional):
```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your preferred settings
```

3. **Initialize and deploy**:
```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the infrastructure
terraform apply
```

4. **Configure kubectl**:
```bash
# Get the cluster configuration command from output
terraform output kubectl_config_command

# Run the command (example):
aws eks --region af-south-1 update-kubeconfig --name builder-space-dev
```

5. **Verify deployment**:
```bash
# Check nodes
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system

# Test internet connectivity
kubectl logs -n test deployment/test-internet-app

# Verify metrics server
kubectl top nodes
```

## 📋 Infrastructure Components

### VPC and Networking
- **VPC**: 10.0.0.0/16 with DNS support
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24 across 2 AZs
- **Internet Gateway**: Direct internet access (no NAT Gateway)
- **Security Groups**: Configured for EKS cluster and node communication

### EKS Cluster
- **Version**: Kubernetes 1.28
- **Endpoint**: Public access enabled
- **Add-ons**: VPC CNI, CoreDNS, kube-proxy, EBS CSI driver
- **Node Group**: 2 x t4g.small ARM instances

### IAM Roles and Policies
- **Cluster Role**: AmazonEKSClusterPolicy
- **Node Group Role**: 
  - AmazonEKSWorkerNodePolicy
  - AmazonEKS_CNI_Policy
  - AmazonEC2ContainerRegistryReadOnly
  - AmazonSSMManagedInstanceCore
- **EBS CSI Driver Role**: AmazonEBSCSIDriverPolicy

## 🧪 Testing

The infrastructure includes a test deployment that:
- Runs in the `test` namespace
- Periodically checks internet connectivity via httpbin.org
- Demonstrates pod scheduling and network functionality

**Test commands**:
```bash
# View test pod logs
kubectl logs -n test deployment/test-internet-app

# Check cluster status
kubectl cluster-info

# View node status
kubectl get nodes -o wide

# Check resource usage
kubectl top nodes
kubectl top pods -A
```

## 🔧 Configuration

### Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `af-south-1` | AWS region for deployment |
| `cluster_name` | `builder-space-dev` | EKS cluster name |
| `cluster_version` | `1.28` | Kubernetes version |
| `node_instance_types` | `["t4g.small", "t3.small"]` | Instance types (ARM preferred) |
| `node_desired_size` | `2` | Number of nodes |
| `vpc_cidr` | `10.0.0.0/16` | VPC CIDR block |

### Customization

Edit `terraform.tfvars` to customize:
- Instance types and sizes
- Node count (min/max/desired)
- VPC and subnet configurations
- Tags and naming

## 📦 Terraform Outputs

After deployment, Terraform provides:
- Cluster endpoints and configuration
- kubectl configuration commands
- Testing commands
- Cost estimates
- Resource identifiers

**View outputs**:
```bash
terraform output
terraform output cluster_info
terraform output estimated_monthly_cost
terraform output next_steps
```

## 🔍 Monitoring and Maintenance

### Metrics Server
Automatically installed for resource monitoring:
```bash
kubectl top nodes
kubectl top pods -A
```

### Logging
View cluster and application logs:
```bash
# Cluster logs
kubectl logs -n kube-system deployment/coredns

# Application logs  
kubectl logs -n test deployment/test-internet-app

# Node system logs (if needed)
kubectl describe node <node-name>
```

### Updates
Keep the cluster updated:
```bash
# Check for available updates
aws eks describe-cluster --name builder-space-dev --query cluster.version

# Update cluster (modify variables.tf and apply)
terraform plan
terraform apply
```

## 🧹 Cleanup

To destroy the infrastructure:
```bash
# Remove all resources
terraform destroy

# Confirm destruction
# Type 'yes' when prompted
```

**Note**: This will permanently delete all resources including data volumes.

## 🔒 Security Considerations

This setup is optimized for development with public subnets:
- **Nodes have public IPs** for direct internet access
- **Security groups** restrict traffic between cluster components
- **IAM roles** follow least-privilege principles
- **No NAT Gateway** reduces attack surface and costs

For production use, consider:
- Private subnets with NAT Gateway
- VPC endpoints for AWS services
- Enhanced security groups and NACLs
- AWS WAF and GuardDuty

## 🐛 Troubleshooting

### Common Issues

1. **Node not ready**:
```bash
kubectl describe node <node-name>
kubectl get events -A
```

2. **Pod scheduling issues**:
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get nodes -o wide
```

3. **Internet connectivity**:
```bash
# Test from a pod
kubectl run test-curl --image=curlimages/curl -it --rm -- curl -I http://httpbin.org/ip
```

4. **Terraform errors**:
```bash
# Check AWS credentials
aws sts get-caller-identity

# Validate configuration
terraform validate
terraform plan
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

**⚠️ Important**: This infrastructure is designed for development use. Monitor your AWS costs and adjust resources as needed.