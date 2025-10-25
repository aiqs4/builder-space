# Migration Guide

## From Old Structure to New KISS Architecture

### What Changed

#### ✅ Improvements
1. **Organized by concern** - Each component in separate file
2. **Bigger subnets** - /22 instead of /24 (1,022 vs 254 IPs)
3. **Removed manual IRSA for add-ons** - AWS manages automatically
4. **Aurora Serverless v2** - Scales to zero, more cost effective
5. **Latest EKS version** - 1.31 (was 1.33)
6. **Karpenter autoscaling** - More efficient than cluster autoscaler
7. **External DNS** - Automatic DNS management for 4 domains

#### ❌ Removed
- Manual OIDC provider creation (EKS creates automatically)
- Manual EFS CSI driver setup (use EBS CSI instead)
- App-specific RDS IAM roles (moved to app deployment)
- Spot node group (Karpenter handles mixed capacity)
- Redundant IAM policies

### Migration Steps

#### 1. Backup Current State
```bash
# Export current kubeconfig
aws eks update-kubeconfig --region af-south-1 --name builder-space --kubeconfig backup-kubeconfig

# Backup workloads
kubectl get all -A -o yaml > backup-workloads.yaml

# Backup PVCs
kubectl get pvc -A -o yaml > backup-pvcs.yaml
```

#### 2. Set Required Config
```bash
# Set database password
pulumi config set --secret db_password "your-secure-password"
```

#### 3. Deploy New Stack
```bash
# Option A: Fresh deployment (recommended)
pulumi destroy --stack eks  # Delete old
pulumi up --stack eks       # Deploy new

# Option B: In-place upgrade (risky)
pulumi up --stack eks       # Will update existing resources
```

#### 4. Restore Workloads
```bash
# Update kubeconfig
aws eks update-kubeconfig --region af-south-1 --name builder-space

# Restore namespaces and workloads (selectively)
kubectl apply -f backup-workloads.yaml
```

### Key Differences

| Component | Old | New |
|-----------|-----|-----|
| Subnets | /24 (254 IPs) | /22 (1,022 IPs) |
| EKS Version | 1.33 | 1.31 |
| Database | RDS Postgres | Aurora Serverless v2 |
| Autoscaling | Manual node groups | Karpenter |
| DNS | Manual | External DNS |
| Add-ons | Manual IRSA | AWS-managed |
| Structure | Single file | Organized by concern |

### Breaking Changes

1. **Database endpoint changed** - Aurora uses different endpoint format
2. **Node labels** - Karpenter uses different node labels
3. **Add-on versions** - Updated to latest compatible versions

### Rollback Plan

If issues occur:
```bash
# Revert to old cluster.py
mv cluster.py.old cluster.py
rm -rf src/

# Restore old __main__.py
git checkout __main__.py

# Deploy old stack
pulumi up --stack eks
```

### Testing Checklist

- [ ] Cluster accessible: `kubectl get nodes`
- [ ] Add-ons running: `kubectl -n kube-system get pods`
- [ ] External DNS working: Check Route53 for test record
- [ ] Karpenter provisioning: Deploy test workload
- [ ] Database accessible: Test connection
- [ ] PVCs working: Create test PVC with EBS

### Support

If you encounter issues:
1. Check CloudWatch logs for control plane
2. Check pod logs: `kubectl -n kube-system logs <pod>`
3. Verify IAM roles: `aws iam get-role --role-name <role>`
4. Check add-on status: `aws eks describe-addon --cluster-name builder-space --addon-name <addon>`
