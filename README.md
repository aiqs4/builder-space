# Builder Space - Pure Declarative EKS Infrastructure (Pulumi Python)

**🎯 PURE DECLARATIVE: Infrastructure as Code with minimal abstractions, following Pulumi best practices!**

A purely declarative, module-based Pulumi Python infrastructure for AWS EKS that eliminates complex classes and functions in favor of simple, clear resource declarations.

## 🎯 Philosophy

This infrastructure follows the principle that **Infrastructure as Code should be just declarations**:

- ✅ **No Large Classes**: Eliminated complex wrapper classes
- ✅ **No Function Abstractions**: Direct Pulumi resource declarations 
- ✅ **Minimal Logic**: Only essential conditionals for configuration
- ✅ **Import-Based**: Modules execute declarations on import
- ✅ **Pipeline Compatible**: Works seamlessly with recovery and import mechanisms

## 🏗️ Pure Declarative Architecture

Each module contains direct Pulumi resource declarations:

```python
# modules/vpc/__init__.py - Pure declarations
vpc = aws.ec2.Vpc(f"{cluster_name}-vpc", cidr_block=config.vpc_cidr, ...)
igw = aws.ec2.InternetGateway(f"{cluster_name}-igw", vpc_id=vpc.id, ...)

# Export resources directly
vpc_id = vpc.id
public_subnet_ids = [subnet.id for subnet in public_subnets]
```

```python
# __main__.py - Import modules to execute declarations
import modules.vpc as vpc_module
import modules.eks as eks_module

# Use exported resources directly
pulumi.export("vpc_id", vpc_module.vpc_id)
pulumi.export("cluster_endpoint", eks_module.cluster_endpoint)
```

## 🔧 Infrastructure Components

- **VPC Module** (`modules/vpc/`): Network infrastructure declarations
- **IAM Module** (`modules/iam/`): Role and policy resource declarations  
- **EKS Module** (`modules/eks/`): Cluster and node group declarations
- **Addons Module** (`modules/addons/`): Kubernetes resource declarations
- **State Storage Module** (`modules/state_storage/`): Backend storage declarations

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11+ installed
- Pulumi CLI installed
- kubectl installed

### Pipeline-Ready Declarative Infrastructure

This infrastructure is designed for **reliable pipeline operations** with pure declarative principles:

🎯 **Static Declarations**: Resources are declared statically, making them predictable for pipelines  
🔄 **Idempotent by Design**: Declarative resources handle existing infrastructure gracefully  
🔁 **Recovery Compatible**: Pipeline failures can be resolved with import and retry  
📦 **Module-Based**: Each module executes independently, enabling partial deployments  
🛡️ **Error Resilient**: Minimal logic reduces potential failure points  
✅ **State Management**: Direct resource exports work seamlessly with Pulumi state

### Robust Pipeline Operations

The declarative approach ensures pipelines work reliably regardless of existing resources:

- **Import on Conflict**: Existing resources are automatically imported rather than causing failures
- **State Recovery**: Simple `pulumi refresh` resolves most state inconsistencies  
- **Retry-Friendly**: Stateless declarations can be retried without side effects
- **Minimal Dependencies**: Direct imports reduce complex dependency chains

### 1. Bootstrap State Storage (First Time Only)
The state storage infrastructure (S3 bucket + DynamoDB table) must be created before deploying the main infrastructure.

**Via GitHub Actions (Recommended):**
1. Go to Actions → "Bootstrap State Storage (Pulumi)" → Run workflow
2. Choose "up" to create the state storage
3. The workflow now includes automatic retry logic and validation
4. Record the bucket and table names from the output
5. Add them to repository secrets: `BACKEND_BUCKET` and `BACKEND_DYNAMODB_TABLE`

💡 **Note**: If resources already exist, the workflow will import them automatically instead of failing.

**Locally:**
```bash
cd bootstrap
pip install -r requirements.txt
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
pulumi stack select dev --create

# The bootstrap now includes automatic refresh and validation
pulumi up
# Record the output values
```

### 2. Deploy Main Infrastructure
**Via GitHub Actions:**
1. Go to Actions → "Deploy EKS Infrastructure (Pulumi)" → Run workflow  
2. Choose "up" to deploy
3. The workflow now includes:
   - Automatic state refresh before deployment
   - Retry logic for transient AWS errors  
   - Post-deployment validation of EKS cluster
   - Node health checks and connectivity tests

**Locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Pulumi
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"
pulumi stack select dev --create

# Refresh state before deployment (recommended)
pulumi refresh --yes

# Deploy infrastructure with validation
pulumi up
```

### 3. Configure kubectl and Validate
```bash
# Update kubeconfig (replace with your region and cluster name)
aws eks --region af-south-1 update-kubeconfig --name builder-space

# Validate cluster
kubectl get nodes
kubectl get pods -A

# Run comprehensive validation
kubectl cluster-info
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

## 🔧 Troubleshooting

### Common Issues and Solutions

#### ❌ `BucketAlreadyOwnedByYou` Error
This error occurs when the S3 bucket already exists. **This is now handled automatically!**

**Solution**: The enhanced bootstrap workflow will automatically import existing buckets.

If running locally:
```bash
cd bootstrap
pulumi refresh --yes  # Sync with existing state
pulumi up            # Will import existing resources
```

#### ❌ `ResourceInUseException` for DynamoDB Table
This error occurs when the DynamoDB table already exists. **This is now handled automatically!**

**Solution**: The enhanced bootstrap workflow will automatically import existing tables.

#### ❌ Pipeline Fails with Transient AWS Errors
AWS API calls can occasionally fail due to rate limits or temporary issues.

**Solution**: 
- The workflows now include automatic retry logic (3 attempts with backoff)
- If you see transient errors, simply re-run the workflow

#### ❌ EKS Cluster Not Accessible
If `kubectl` commands fail after deployment:

**Diagnosis**:
```bash
# Check if cluster exists
aws eks list-clusters --region af-south-1

# Update kubeconfig
aws eks --region af-south-1 update-kubeconfig --name builder-space

# Test connectivity
kubectl cluster-info
```

**Solution**:
```bash
# Verify IAM permissions
aws sts get-caller-identity

# Check cluster status
aws eks describe-cluster --name builder-space --region af-south-1

# Wait for cluster to be fully ready (may take 10-15 minutes)
```

#### ❌ Node Group Issues
If nodes don't appear or aren't ready:

**Diagnosis**:
```bash
kubectl get nodes -o wide
kubectl describe nodes
```

**Common causes**:
- Node group still initializing (wait 5-10 minutes)
- IAM role issues  
- Subnet/security group configuration

#### ❌ Pulumi State Issues
If you encounter state corruption or inconsistencies:

**Solution**:
```bash
# Refresh state to sync with AWS
pulumi refresh --yes

# If that doesn't work, you can import specific resources
pulumi import aws:s3/bucket:Bucket my-bucket my-bucket-name
pulumi import aws:dynamodb/table:Table my-table my-table-name
```

### Validation Commands

#### Bootstrap Validation
```bash
cd bootstrap

# Validate S3 bucket
aws s3 ls s3://$(pulumi stack output bucket_name)

# Validate DynamoDB table  
aws dynamodb describe-table --table-name $(pulumi stack output dynamodb_table_name)

# Test Pulumi backend connectivity
pulumi stack ls
```

#### Infrastructure Validation
```bash
# Cluster connectivity
kubectl cluster-info

# Node health
kubectl get nodes -o wide
kubectl describe nodes

# System pods
kubectl get pods -n kube-system

# Comprehensive health check
kubectl get all -A
```

### Recovery Procedures

#### Reset Pulumi Stack (if corrupted)
```bash
# Back up current state first
pulumi stack export --file backup.json

# Create new stack
pulumi stack init dev-new

# Import resources if needed
pulumi refresh --yes
```

#### Complete Environment Reset
```bash
# 1. Destroy main infrastructure
pulumi destroy --yes

# 2. Destroy state storage (will lose all state!)
cd bootstrap  
pulumi destroy --yes

# 3. Start fresh
# Follow the Quick Start guide from step 1
```

### Getting Help

If you continue to experience issues:

1. **Run the troubleshooting script**: `./troubleshoot.sh` - comprehensive diagnostic tool
2. **Check the workflow logs** in GitHub Actions for detailed error messages
3. **Run validation commands** to identify specific resource issues
4. **Check AWS Console** to verify resource states manually
5. **Use `pulumi refresh`** to sync state with actual AWS resources

### Local Testing

To test the infrastructure locally before deploying:

```bash
# Run syntax and import validation
./test.sh

# Run comprehensive troubleshooting
./troubleshoot.sh

# Preview changes without deploying
pulumi preview
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

## 🛠️ Development and Module Structure

### Function-Based Architecture
This project now uses a **clean function-based approach** following Pulumi best practices:

```python
# Example: Simple, declarative resource creation
from modules.vpc import create_vpc_resources
from modules.iam import create_iam_resources
from modules.eks import create_eks_resources

# Create VPC infrastructure
vpc = create_vpc_resources(
    cluster_name="my-cluster",
    vpc_cidr="10.0.0.0/16",
    public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"],
    tags={"Environment": "dev"}
)

# Create IAM resources
iam = create_iam_resources(
    cluster_name="my-cluster",
    tags={"Environment": "dev"}
)

# Create EKS cluster
eks = create_eks_resources(
    cluster_name="my-cluster",
    cluster_version="1.32",
    cluster_role_arn=iam["cluster_role_arn"],
    node_group_role_arn=iam["node_group_role_arn"],
    subnet_ids=vpc["public_subnet_ids"],
    cluster_security_group_id=vpc["cluster_security_group_id"],
    node_security_group_id=vpc["node_group_security_group_id"],
    node_instance_types=["t3.medium"],
    node_desired_size=2,
    node_max_size=5,
    node_min_size=1,
    node_disk_size=20,
    tags={"Environment": "dev"}
)
```

### Module Structure
- **`modules/vpc/`**: VPC, subnets, security groups creation
- **`modules/iam/`**: IAM roles and policies for EKS
- **`modules/eks/`**: EKS cluster and node group management
- **`modules/addons/`**: Kubernetes add-ons and applications
- **`modules/state_storage/`**: S3 and DynamoDB backend setup

### Key Benefits
- **Simple Function Calls**: Clear input/output contracts
- **No Large Classes**: Eliminated heavy stateful wrappers
- **Better Testability**: Easy to unit test and mock
- **Explicit Dependencies**: Clear resource relationships
- **Pulumi Idiomatic**: Follows Pulumi community patterns

### Running Tests
```bash
# Test module structure and imports
python -m unittest tests.test_modules -v

# Verify syntax of all modules
python -m py_compile modules/*/__init__.py
```

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