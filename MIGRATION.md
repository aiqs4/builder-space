# Terraform Backend Migration Guide

This guide provides step-by-step instructions for migrating from the old monolithic infrastructure setup to the new modular approach with separated backend.

## Overview

The infrastructure has been refactored to:
- **Separate backend bootstrap** from main infrastructure
- **Modularize components** (vpc, iam, eks, addons) for better organization
- **Add cost-saving features** (spot instances, scaling options)
- **Improve state management** with proper backend separation

## Migration Steps

### Step 1: Bootstrap the Backend Infrastructure

Before deploying the main infrastructure, you need to create the S3 bucket and DynamoDB table for state storage.

1. **Run the backend bootstrap workflow**:
   - Go to Actions → "Bootstrap Terraform Backend" → Run workflow
   - Choose "apply" to create the backend infrastructure
   - Record the bucket name and DynamoDB table name from the output

2. **Configure GitHub secrets** (if not already done):
   ```
   BACKEND_BUCKET=<bucket-name-from-output>
   BACKEND_DYNAMODB_TABLE=<table-name-from-output>
   ```

### Step 2: Handle Existing Resources

If you have existing AWS resources that might conflict, use these options:

#### Option A: Import Existing Resources
```bash
# Import existing IAM roles
terraform import module.iam.aws_iam_role.cluster[0] funda-cluster-role
terraform import module.iam.aws_iam_role.node_group[0] funda-ng-role

# Import existing CloudWatch log group
terraform import module.eks.aws_cloudwatch_log_group.cluster[0] /aws/eks/funda/cluster

# Import existing KMS key (if managed by Terraform)
# terraform import module.eks.aws_kms_key.eks[0] <key-id>
```

#### Option B: Use Existing Resources (Recommended)
Configure variables to use existing resources instead of creating new ones:

```hcl
# In terraform.tfvars or as workflow inputs
use_existing_cluster_role = true
existing_cluster_role_name = "funda-cluster-role"

use_existing_node_role = true
existing_node_role_name = "funda-ng-role"

existing_cloudwatch_log_group_name = "/aws/eks/funda/cluster"

use_existing_kms_key = true
existing_kms_key_arn = "arn:aws:kms:region:account:key/key-id"
```

### Step 3: Migrate State to S3 Backend

1. **Run the main infrastructure workflow**:
   - Go to Actions → "Deploy EKS Infrastructure" → Run workflow
   - Ensure "Use S3 backend" is set to "true"
   - Choose "plan" first to verify configuration

2. **Verify the plan** looks correct with no unexpected resource changes

3. **Apply the infrastructure**:
   - Run the workflow again with "apply"

### Step 4: Verify Migration

After migration, verify that:
- [ ] No existing resources were recreated
- [ ] State is stored in S3 bucket
- [ ] DynamoDB table is used for locking
- [ ] Cluster is accessible with kubectl
- [ ] All modules are working correctly

```bash
# Verify cluster access
aws eks --region af-south-1 update-kubeconfig --name funda
kubectl get nodes

# Check state location
terraform show | head -10
```

## Cost Optimization Features

The new setup includes several cost-saving options (disabled by default):

### Spot Instances (70% savings)
```hcl
enable_spot_instances = true
```

### Scheduled Scaling (65% savings during off-hours)
```hcl
enable_scheduled_scaling = true
scheduled_scale_down_time = "0 18 * * 1-5"  # 6 PM weekdays
scheduled_scale_up_time = "0 8 * * 1-5"     # 8 AM weekdays
```

### Cluster Autoscaler
```hcl
enable_cluster_autoscaler = true
```

## Module Structure

The new modular structure:

```
modules/
├── backend-bootstrap/    # S3 + DynamoDB for state storage
├── vpc/                 # VPC, subnets, security groups
├── iam/                 # IAM roles and policies
├── eks/                 # EKS cluster and node groups
└── addons/              # Kubernetes add-ons and applications
```

## Rollback Plan

If migration fails:

1. **Restore original files**:
   ```bash
   mv backend.tf.old backend.tf
   mv old_files/* .
   ```

2. **Use local backend temporarily**:
   - Remove backend configuration
   - Run `terraform init -migrate-state` to move state back to local

3. **Import resources if needed** using the commands from the migration_info output

## Troubleshooting

### Common Issues

1. **"Resource already exists" errors**:
   - Use `use_existing_*` variables instead of importing
   - Or import the resources using the commands above

2. **"Backend bucket not found"**:
   - Ensure backend bootstrap workflow was run successfully
   - Check GitHub secrets are configured correctly

3. **"Access denied" errors**:
   - Verify IAM permissions for GitHub OIDC role
   - Check AWS credentials configuration

4. **State conflicts**:
   - Use `terraform state list` to see current state
   - Use `terraform state rm` to remove conflicting resources if needed

### Getting Help

1. Check workflow logs in GitHub Actions
2. Use `terraform output migration_info` for import commands
3. Verify configuration with `terraform output configuration_summary`

## Verification Checklist

After migration is complete:

- [ ] Backend bootstrap workflow completed successfully
- [ ] Main infrastructure workflow deploys without errors
- [ ] No existing resources were recreated (check plan output)
- [ ] State is stored in S3 bucket
- [ ] kubectl can access the cluster
- [ ] All pods are running: `kubectl get pods -A`
- [ ] Test deployment is working: `kubectl logs -n test deployment/test-internet-app`
- [ ] Cost optimization flags are configured as desired
- [ ] Documentation is updated with new procedures

## Next Steps

1. **Enable cost optimizations** based on your usage patterns
2. **Set up monitoring** for costs and resource usage
3. **Configure backup and recovery** procedures
4. **Update CI/CD processes** to use the new workflows
5. **Train team members** on the new modular structure