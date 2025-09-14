# Builder Space - Modular EKS Development Environment (Pulumi Python)

**🚀 MIGRATED TO PULUMI: Now powered by Python for improved modularity and developer experience!**

A cost-optimized, modular Pulumi Python setup for AWS EKS development environments with separated backend management and comprehensive cost-saving features.

## 🎯 Overview

This infrastructure creates:
- **Modular Python Architecture**: Separated modules for vpc, iam, eks, addons using Pulumi Python
- **State Storage Bootstrap**: Separate S3 + DynamoDB state management  
- **Cost Optimization**: Spot instances, scaling options, and resource optimization
- **Safe Migration**: Import existing resources without recreation
- **EKS Cluster**: Managed Kubernetes control plane
- **Node Group**: ARM-based instances with cost optimization options
- **VPC**: Public subnets configuration optimized for development
- **Add-ons**: metrics-server, test deployments, optional load balancer controller

## 🔄 Migration Status

✅ **Migration Complete**: Terraform code has been migrated to Pulumi Python
- **Legacy Code**: Original Terraform code archived in `terraform-legacy/`
- **New Implementation**: Python-based Pulumi modules in `modules/`
- **Preserved Functionality**: All features and cost optimizations maintained
- **Enhanced Developer Experience**: Python modularity and type hints

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11+ installed
- Pulumi CLI installed
- kubectl installed

### 1. Bootstrap State Storage (First Time Only)
The state storage infrastructure (S3 bucket + DynamoDB table) must be created before deploying the main infrastructure.

**Via GitHub Actions (Recommended):**
1. Go to Actions → "Bootstrap State Storage (Pulumi)" → Run workflow
2. Choose "up" to create the state storage
3. Record the bucket and table names from the output
4. Add them to repository secrets: `BACKEND_BUCKET` and `BACKEND_DYNAMODB_TABLE`

**Locally:**
```bash
cd bootstrap
pip install -r requirements.txt
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
pulumi stack select dev --create
pulumi up
# Record the output values
```

### 2. Deploy Main Infrastructure
**Via GitHub Actions:**
1. Go to Actions → "Deploy EKS Infrastructure (Pulumi)" → Run workflow  
2. Choose "up" to deploy

**Locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Pulumi
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
pulumi stack select dev --create

# Deploy infrastructure
pulumi up
```

### 3. Configure kubectl
```bash
aws eks --region af-south-1 update-kubeconfig --name builder-space
kubectl get nodes
```

## 📁 Architecture

### Modular Structure
```
modules/
├── vpc/                 # VPC, subnets, security groups  
├── iam/                 # IAM roles and policies
├── eks/                 # EKS cluster and node groups
├── addons/              # Kubernetes add-ons and applications
└── state_storage/       # S3 + DynamoDB for state storage
```

### Workflows
- **State Storage Bootstrap** (`.github/workflows/backend-bootstrap.yml`): Creates state storage infrastructure
- **Main Infrastructure** (`.github/workflows/deploy.yml`): Deploys EKS and supporting resources

## 💰 Cost Optimization

Cost optimization features (disabled by default for safety):

### Available Options
- **Spot Instances**: Enable `enable_spot_instances` for ~70% cost reduction
- **Reserved Instances**: For long-term deployments  
- **Cluster Autoscaler**: Automatic scaling based on demand
- **Scheduled Scaling**: Scale down during off-hours
- **Cost Monitoring**: Billing alerts and cost tracking

### Current Estimated Costs
- EKS Cluster: ~$72/month ($0.10/hour)
- Node Group (2x t4g.small): ~$29/month
- EBS Storage (40GB): ~$8/month  
- **Total: ~$109/month**

### Cost Savings Potential
- **Spot instances**: Save ~$20/month (70% reduction on nodes)
- **Single node dev**: Save ~$14/month  
- **Scheduled shutdown**: Save ~65% during off-hours

## 🔧 Configuration Options

### Core Configuration
All configuration is managed through `Pulumi.dev.yaml`:

```yaml
config:
  aws:region: af-south-1
  builder-space-eks:cluster_name: builder-space
  builder-space-eks:cluster_version: "1.32"
  builder-space-eks:node_instance_types:
    - t4g.small
    - t3.small
  builder-space-eks:enable_spot_instances: false  # Enable for cost savings
```

### Cost Optimization Settings
```yaml
config:
  builder-space-eks:enable_spot_instances: true        # 70% cost reduction
  builder-space-eks:enable_cluster_autoscaler: true    # Auto-scaling
  builder-space-eks:enable_scheduled_scaling: true     # Off-hours scaling
  builder-space-eks:cost_alert_threshold: 100          # Monthly alert threshold
```

## 📋 Verification

After deployment, verify your cluster:

```bash
# Check cluster status
kubectl cluster-info

# Check nodes
kubectl get nodes -o wide

# Check system pods  
kubectl get pods -n kube-system

# Test internet connectivity
kubectl logs -n test deployment/test-internet-app --tail=10

# Check resource usage
kubectl top nodes
kubectl top pods -A
```

## 🗑️ Cleanup

### Quick Cleanup
```bash
./cleanup.sh
```

### Manual Cleanup  
```bash
pulumi destroy --yes
```

### Complete Cleanup (including state storage)
```bash
# Destroy main infrastructure
pulumi destroy --yes

# Destroy state storage
cd bootstrap
pulumi destroy --yes
```

## 🔄 Migration from Terraform

### What Changed
- **Architecture**: Terraform → Pulumi Python modules
- **Configuration**: HCL → YAML + Python configuration classes
- **State Management**: Enhanced with type safety and validation
- **Developer Experience**: Python IDE support, type hints, better debugging

### Legacy Code
Original Terraform code is preserved in `terraform-legacy/` for reference and rollback if needed.

### Migration Benefits
- **Type Safety**: Python type hints prevent configuration errors
- **IDE Support**: Better autocompletion and error detection
- **Modularity**: Improved code reuse and testing
- **Extensibility**: Easier to add custom logic and integrations

## 🏗️ Architecture Benefits

### Modular Design
- **Separation of Concerns**: Each module has a specific responsibility
- **Reusability**: Modules can be used independently or in other projects
- **Maintainability**: Easier to understand, modify, and troubleshoot
- **Testing**: Each module can be tested independently

### State Storage Separation  
- **Safe State Management**: State storage infrastructure managed separately
- **Conflict Prevention**: No circular dependencies between state storage and infrastructure
- **Migration Safety**: Clear path for migrating existing resources
- **Recovery**: State storage persists even if main infrastructure is destroyed

### Cost Optimization
- **Flexible Options**: Multiple cost-saving features available but disabled by default
- **Free Tier Friendly**: Designed to work within AWS free tier limitations
- **Transparent Costs**: Clear cost breakdown and optimization recommendations
- **Gradual Adoption**: Enable optimizations as you become comfortable with the setup

## 🔍 Monitoring & Troubleshooting

### Cost Monitoring
Set up AWS billing alerts:
- Warning at $50/month
- Critical at $75/month
- Emergency shutdown at $100/month

### Common Issues
1. **State storage not found**: Run state storage bootstrap workflow first
2. **Resource conflicts**: Use `use_existing_*` variables or import resources
3. **Permission errors**: Check IAM permissions for GitHub OIDC role
4. **Nodes not ready**: Wait 5-10 minutes for initialization

### Getting Help
- Check workflow logs in GitHub Actions
- Use `pulumi stack output` to view configuration summary
- Review troubleshooting section in migration guide
- Check Pulumi logs with `pulumi logs`

## ⚠️ Important Notes

- **Free Tier**: This setup is designed for development and may not fit within AWS free tier limits
- **Production Use**: Additional security and reliability measures needed for production
- **Cost Monitoring**: Always monitor AWS costs and set up billing alerts
- **Resource Cleanup**: Remember to destroy resources when not in use to avoid charges
- **Migration**: Legacy Terraform code is preserved in `terraform-legacy/` directory

## 📖 Documentation

- [Pulumi AWS Documentation](https://www.pulumi.com/docs/clouds/aws/)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

**⚠️ Important**: This infrastructure is designed for development use. Monitor your AWS costs and adjust resources as needed.