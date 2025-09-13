# Builder Space - Modular EKS Development Environment

A cost-optimized, modular Terraform setup for AWS EKS development environments with separated backend management and comprehensive cost-saving features.

## 🎯 Overview

This infrastructure creates:
- **Modular Architecture**: Separated modules for vpc, iam, eks, addons
- **Backend Bootstrap**: Separate S3 + DynamoDB backend management
- **Cost Optimization**: Spot instances, scaling options, and resource optimization
- **Safe Migration**: Import existing resources without recreation
- **EKS Cluster**: Managed Kubernetes control plane
- **Node Group**: ARM-based instances with cost optimization options
- **VPC**: Public subnets configuration optimized for development
- **Add-ons**: metrics-server, test deployments, optional load balancer controller

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 installed  
- kubectl installed

### 1. Bootstrap Backend (First Time Only)
The backend infrastructure (S3 bucket + DynamoDB table) must be created before deploying the main infrastructure.

**Via GitHub Actions (Recommended):**
1. Go to Actions → "Bootstrap Terraform Backend" → Run workflow
2. Choose "apply" to create the backend
3. Record the bucket and table names from the output
4. Add them to repository secrets: `BACKEND_BUCKET` and `BACKEND_DYNAMODB_TABLE`

**Locally:**
```bash
cd bootstrap
terraform init
terraform apply
# Record the output values
```

### 2. Deploy Main Infrastructure
**Via GitHub Actions:**
1. Go to Actions → "Deploy EKS Infrastructure" → Run workflow  
2. Ensure "Use S3 backend" is true
3. Choose "apply" to deploy

**Locally:**
```bash
# Configure backend first (using values from step 1)
cat > backend.tf << EOF
terraform {
  backend "s3" {
    bucket         = "your-bucket-name"
    key            = "terraform.tfstate"
    region         = "af-south-1"
    dynamodb_table = "your-table-name"
    encrypt        = true
  }
}
EOF

terraform init
terraform plan
terraform apply
```

### 3. Configure kubectl
```bash
aws eks --region af-south-1 update-kubeconfig --name funda
kubectl get nodes
```

## 📁 Architecture

### Modular Structure
```
modules/
├── backend-bootstrap/    # S3 + DynamoDB for Terraform state
├── vpc/                 # VPC, subnets, security groups  
├── iam/                 # IAM roles and policies
├── eks/                 # EKS cluster and node groups
└── addons/              # Kubernetes add-ons and applications
```

### Workflows
- **Backend Bootstrap** (`.github/workflows/backend-bootstrap.yml`): Creates state storage infrastructure
- **Main Infrastructure** (`.github/workflows/deploy.yml`): Deploys EKS and supporting resources

## 💰 Cost Optimization

### Baseline Cost (~$109/month)
- **EKS Cluster**: $72.00/month ($0.10/hour)
- **Node Group**: $28.80/month (2x t4g.small on-demand)
- **EBS Storage**: $8.00/month (40GB total)

### Cost-Saving Features (Disabled by Default)
```hcl
# Enable spot instances for ~70% savings on nodes
enable_spot_instances = true

# Enable scheduled scaling for dev environments  
enable_scheduled_scaling = true
scheduled_scale_down_time = "0 18 * * 1-5"  # 6 PM weekdays
scheduled_scale_up_time = "0 8 * * 1-5"     # 8 AM weekdays

# Enable cluster autoscaler
enable_cluster_autoscaler = true
```

**With Spot Instances**: ~$88/month (~$21/month savings)

## 🔄 Migration from Previous Setup

If you have an existing deployment, see [MIGRATION.md](MIGRATION.md) for detailed migration instructions including:
- How to import existing resources safely
- Step-by-step backend migration process  
- Cost optimization configuration
- Troubleshooting guide

## 🔧 Configuration Options

### Using Existing Resources
To avoid recreating existing AWS resources:

```hcl
# Use existing IAM roles
use_existing_cluster_role = true
existing_cluster_role_name = "your-cluster-role-name"

use_existing_node_role = true  
existing_node_role_name = "your-node-role-name"

# Use existing CloudWatch log group
existing_cloudwatch_log_group_name = "/aws/eks/your-cluster/cluster"

# Use existing KMS key
use_existing_kms_key = true
existing_kms_key_arn = "arn:aws:kms:region:account:key/key-id"
```

### Cost Optimization Variables
```hcl
# Spot instances (disabled by default)
enable_spot_instances = false

# Scheduled scaling (disabled by default)
enable_scheduled_scaling = false
scheduled_scale_down_time = "0 18 * * 1-5"
scheduled_scale_up_time = "0 8 * * 1-5"

# Cluster autoscaler (disabled by default)
enable_cluster_autoscaler = false

# Cost monitoring
enable_cost_monitoring = true
cost_alert_threshold = 100
```

## 📋 Verification

After deployment, verify your cluster:

```bash
# Check cluster status
kubectl cluster-info
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system

# Test internet connectivity  
kubectl logs -n test deployment/test-internet-app

# Check resource usage
kubectl top nodes
kubectl top pods -A
```

## 🗑️ Cleanup

To avoid ongoing charges, destroy resources when finished:

```bash
# Via GitHub Actions
# Actions → "Deploy EKS Infrastructure" → Run workflow → Destroy

# Or locally
terraform destroy

# Optionally destroy backend (WARNING: This will delete state storage)
# Actions → "Bootstrap Terraform Backend" → Run workflow → Destroy
```

## 📖 Documentation

- [Migration Guide](MIGRATION.md) - Migrating from previous setup
- [Cost Optimization](COST_OPTIMIZATION.md) - Detailed cost optimization strategies  
- [GitHub Actions Setup](GITHUB_ACTIONS.md) - OIDC configuration
- [Quick Start](QUICKSTART.md) - Step-by-step deployment guide

## 🔍 Monitoring & Troubleshooting

### Cost Monitoring
Set up AWS billing alerts:
- Warning at $50/month
- Critical at $75/month
- Emergency shutdown at $100/month

### Common Issues
1. **Backend not found**: Run backend bootstrap workflow first
2. **Resource conflicts**: Use `use_existing_*` variables or import resources
3. **Permission errors**: Check IAM permissions for GitHub OIDC role
4. **Nodes not ready**: Wait 5-10 minutes for initialization

### Getting Help
- Check workflow logs in GitHub Actions
- Use `terraform output migration_info` for import commands
- Review `terraform output configuration_summary` for current setup
- See troubleshooting section in [MIGRATION.md](MIGRATION.md)

## 🏗️ Architecture Benefits

### Modular Design
- **Separation of Concerns**: Each module has a specific responsibility
- **Reusability**: Modules can be used independently or in other projects
- **Maintainability**: Easier to understand, modify, and troubleshoot
- **Testing**: Each module can be tested independently

### Backend Separation  
- **Safe State Management**: Backend infrastructure managed separately
- **Conflict Prevention**: No circular dependencies between state storage and infrastructure
- **Migration Safety**: Clear path for migrating existing resources
- **Recovery**: State storage persists even if main infrastructure is destroyed

### Cost Optimization
- **Flexible Options**: Multiple cost-saving features available but disabled by default
- **Free Tier Friendly**: Designed to work within AWS free tier limitations
- **Transparent Costs**: Clear cost breakdown and optimization recommendations
- **Gradual Adoption**: Enable optimizations as you become comfortable with the setup

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with appropriate tests
4. Update documentation as needed
5. Submit a pull request

## ⚠️ Important Notes

- **Free Tier**: This setup is designed for development and may not fit within AWS free tier limits
- **Production Use**: Additional security and reliability measures needed for production
- **Cost Monitoring**: Always monitor AWS costs and set up billing alerts
- **Resource Cleanup**: Remember to destroy resources when not in use to avoid charges
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