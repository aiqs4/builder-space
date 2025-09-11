# Quick Start Deployment Guide

## Prerequisites

Before starting, ensure you have:
- ✅ AWS CLI configured with appropriate permissions
- ✅ Terraform >= 1.0 installed
- ✅ kubectl installed

## Deployment Steps

### 1. Quick Deploy (Automated)
```bash
# Make scripts executable
chmod +x *.sh

# Deploy everything automatically
./deploy.sh
```

### 2. Manual Deploy (Step by step)
```bash
# 1. Initialize Terraform
terraform init

# 2. (Optional) Customize configuration
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your preferences

# 3. Plan deployment
terraform plan

# 4. Deploy infrastructure
terraform apply

# 5. Configure kubectl
aws eks --region af-south-1 update-kubeconfig --name builder-space-dev
```

## Verification

### Test the deployment:
```bash
# Run comprehensive tests
./test.sh

# Or manually:
kubectl get nodes
kubectl get pods -A
kubectl logs -n test deployment/test-internet-app
kubectl top nodes
```

## Expected Results

✅ **2 ARM-based nodes** (t4g.small) ready and schedulable  
✅ **System pods** running in kube-system namespace  
✅ **Internet connectivity** verified via test deployment  
✅ **Metrics server** operational for resource monitoring  
✅ **Cost target** ~$111/month (see COST_OPTIMIZATION.md for savings)

## Troubleshooting

### Common issues:
1. **Nodes not ready**: Wait 5-10 minutes for full initialization
2. **kubectl access denied**: Run the kubeconfig command from outputs
3. **Test pod failing**: Check internet gateway and security groups

### Get help:
```bash
# Cluster info
terraform output cluster_info

# Next steps
terraform output next_steps

# Test commands
terraform output test_commands
```

## Cleanup

When finished, destroy resources to avoid charges:
```bash
./cleanup.sh
# or
terraform destroy
```

## Next Steps

1. **Optimize costs**: See [COST_OPTIMIZATION.md](COST_OPTIMIZATION.md)
2. **Deploy applications**: Use kubectl to deploy your workloads
3. **Monitor resources**: Set up AWS billing alerts
4. **Scale as needed**: Adjust node count in variables.tf

## Cost Monitoring

Set up billing alerts in AWS Console:
- Warning at $50/month
- Critical at $75/month  
- Emergency shutdown at $100/month