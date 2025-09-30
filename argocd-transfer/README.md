# ArgoCD Integration Strategy

## Overview

This directory contains the configuration and guides for transferring infrastructure resources from Pulumi-managed to ArgoCD-managed (GitOps) approach.

## Current Architecture

The `builder-space` repository currently manages infrastructure through Pulumi:

```
builder-space (Pulumi)
├── bootstrap/          # S3 + DynamoDB state storage
├── cluster.py          # EKS cluster with VPC, RDS
└── infra-k8s/         # ArgoCD, External-DNS, Cluster-Autoscaler
```

## Target Architecture

After integration, the architecture will be:

```
builder-space (Pulumi)
├── bootstrap/          # S3 + DynamoDB state storage
├── cluster.py          # EKS cluster with VPC, RDS
└── infra-k8s/         # ONLY ArgoCD bootstrap

builder-space-argocd (GitOps)
└── environments/
    └── prod/
        └── infrastructure/
            ├── external-dns/
            ├── cluster-autoscaler/
            ├── cert-manager/
            └── applications/
```

## Recommended Approach

### Phase 1: Bootstrap Only (Recommended)

**What Stays in Pulumi (`builder-space`):**
- State storage (bootstrap)
- EKS cluster, VPC, networking
- RDS database
- ArgoCD installation ONLY

**What Moves to ArgoCD (`builder-space-argocd`):**
- External-DNS
- Cluster-Autoscaler
- Cert-Manager & ClusterIssuers
- All application deployments

**Why This Approach?**
1. ✅ **Clear Separation**: Infrastructure vs Configuration
2. ✅ **GitOps for K8s**: Kubernetes resources managed via Git
3. ✅ **Pulumi for AWS**: AWS resources managed via Pulumi
4. ✅ **Single Source of Truth**: K8s configs in Git, AWS in Pulumi
5. ✅ **Easier Rollbacks**: Git-based rollbacks for K8s changes

### Phase 2: Migration Steps

1. **Bootstrap ArgoCD** (Already configured in `infra-k8s/__main__.py`)
   - ArgoCD is deployed via Pulumi
   - ArgoCD Application resource points to `builder-space-argocd`
   
2. **Prepare GitOps Repository** (`builder-space-argocd`)
   - Create directory structure
   - Add External-DNS manifests
   - Add Cluster-Autoscaler manifests
   - Add Cert-Manager manifests

3. **Transfer Resources**
   - Remove External-DNS from Pulumi (after ArgoCD takes over)
   - Remove Cluster-Autoscaler from Pulumi (after ArgoCD takes over)
   - Remove Cert-Manager from Pulumi (after ArgoCD takes over)

4. **Verification**
   - ArgoCD syncs resources from Git
   - Resources are healthy
   - Remove Pulumi-managed resources

## Migration Workflow

### Step 1: Setup builder-space-argocd Repository

```bash
# Clone the ArgoCD repository
git clone https://github.com/aiqs4/builder-space-argocd.git
cd builder-space-argocd

# Create directory structure
mkdir -p environments/prod/infrastructure/{external-dns,cluster-autoscaler,cert-manager}
```

### Step 2: Transfer Configurations

Copy the manifests from this directory:
- `external-dns/` → Configuration for External-DNS
- `cluster-autoscaler/` → Configuration for Cluster-Autoscaler
- `cert-manager/` → Configuration for Cert-Manager

See individual directories for detailed manifests and instructions.

### Step 3: Update infra-k8s/__main__.py

Once resources are in ArgoCD, remove the Helm charts from Pulumi:

```python
# REMOVE these sections from infra-k8s/__main__.py:
# - external_dns_chart
# - cluster_autoscaler_chart
# - cert_manager_chart
# - letsencrypt_staging
# - letsencrypt_production

# KEEP only:
# - Namespaces
# - argocd_redis_secret
# - argocd_chart
# - argocd_bootstrap_app (this manages everything else via GitOps)
```

### Step 4: Deploy and Verify

```bash
# In builder-space-argocd
git add environments/
git commit -m "Add infrastructure manifests for ArgoCD"
git push origin main

# ArgoCD will automatically detect and sync the new resources

# Verify in ArgoCD UI or CLI
kubectl get applications -n argocd
argocd app list
argocd app get infrastructure-bootstrap
```

### Step 5: Clean Up Pulumi Resources

```bash
# In builder-space/infra-k8s
# After verifying ArgoCD is managing the resources successfully
pulumi up  # This will remove the old Helm charts
```

## IAM Roles Consideration

**Important**: IAM roles are created by Pulumi and should stay in Pulumi:
- `external_dns_role` - Required by External-DNS pods
- `cluster_autoscaler_role` - Required by Cluster-Autoscaler pods

These IAM roles will be referenced by the Kubernetes ServiceAccounts in ArgoCD manifests.

## Best Practices

1. **Gradual Migration**: Move one component at a time
2. **Test in Dev First**: If possible, test the migration in a dev environment
3. **Monitor Closely**: Watch for any issues during the transition
4. **Backup State**: Always backup Pulumi state before making changes
5. **Document Changes**: Keep track of what was moved and when

## Rollback Strategy

If issues occur during migration:

1. **ArgoCD Issues**: 
   ```bash
   argocd app delete infrastructure-bootstrap
   ```
   
2. **Restore Pulumi Management**:
   ```bash
   # Restore the original infra-k8s/__main__.py from git
   git checkout HEAD~1 -- infra-k8s/__main__.py
   pulumi up
   ```

## Files in This Directory

- `README.md` - This file, overall strategy and workflow
- `external-dns/` - External-DNS Helm values and manifests
- `cluster-autoscaler/` - Cluster-Autoscaler Helm values and manifests
- `cert-manager/` - Cert-Manager Helm values and manifests
- `TRANSFER-GUIDE.md` - Detailed step-by-step transfer instructions
- `IAM-ROLES.md` - Guide for managing IAM roles across Pulumi and ArgoCD

## Next Steps

1. Review the configurations in each subdirectory
2. Set up the `builder-space-argocd` repository with the directory structure
3. Copy manifests to the ArgoCD repository
4. Test ArgoCD sync
5. Remove resources from Pulumi once confirmed working

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [GitOps Principles](https://www.gitops.tech/)
- [Pulumi Kubernetes Provider](https://www.pulumi.com/docs/clouds/kubernetes/)
