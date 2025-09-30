# Step-by-Step Transfer Guide

This guide provides detailed step-by-step instructions for transferring Kubernetes resources from Pulumi management to ArgoCD (GitOps) management.

## Prerequisites

1. ✅ EKS cluster deployed and accessible
2. ✅ ArgoCD installed in the cluster
3. ✅ `kubectl` configured for the cluster
4. ✅ Access to both `builder-space` and `builder-space-argocd` repositories

## Phase 1: Prepare ArgoCD Repository

### Step 1.1: Clone and Setup builder-space-argocd

```bash
# Clone the ArgoCD repository
git clone https://github.com/aiqs4/builder-space-argocd.git
cd builder-space-argocd

# Create directory structure following GitOps best practices
mkdir -p environments/prod/infrastructure/external-dns
mkdir -p environments/prod/infrastructure/cluster-autoscaler
mkdir -p environments/prod/infrastructure/cert-manager
mkdir -p environments/prod/applications
```

### Step 1.2: Copy Configuration Files

Copy the configuration files from `builder-space/argocd-transfer/` to `builder-space-argocd`:

```bash
# Assuming both repos are cloned in the same parent directory
cd /path/to/repositories

# Copy External-DNS configuration
cp builder-space/argocd-transfer/external-dns/* \
   builder-space-argocd/environments/prod/infrastructure/external-dns/

# Copy Cluster-Autoscaler configuration
cp builder-space/argocd-transfer/cluster-autoscaler/* \
   builder-space-argocd/environments/prod/infrastructure/cluster-autoscaler/

# Copy Cert-Manager configuration
cp builder-space/argocd-transfer/cert-manager/* \
   builder-space-argocd/environments/prod/infrastructure/cert-manager/
```

### Step 1.3: Update Configurations with Your Values

Edit the following files with your specific values:

1. **External-DNS** (`external-dns/values.yaml`):
   ```yaml
   # Update with your IAM role ARN (from Pulumi output)
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT:role/external-dns-role-XXXXX
   
   # Update with your domain
   domainFilters:
     - your-domain.com
   
   # Update with your cluster name
   txtOwnerId: builder-space
   ```

2. **Cluster-Autoscaler** (`cluster-autoscaler/values.yaml`):
   ```yaml
   # Update with your IAM role ARN (from Pulumi output)
   rbac:
     serviceAccount:
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT:role/cluster-autoscaler-role-XXXXX
   
   # Update with your cluster name
   autoDiscovery:
     clusterName: builder-space
   
   # Update with your AWS region
   awsRegion: af-south-1
   ```

3. **Cert-Manager ClusterIssuers** (`cert-manager/cluster-issuers.yaml`):
   ```yaml
   # Update with your email
   email: your-email@example.com
   ```

### Step 1.4: Get IAM Role ARNs from Pulumi

```bash
cd builder-space/infra-k8s

# Get External-DNS IAM role ARN
pulumi stack output | grep external_dns_role

# Get Cluster-Autoscaler IAM role ARN
pulumi stack output | grep cluster_autoscaler_role
```

If these aren't exported, you can export them by adding to `infra-k8s/__main__.py`:

```python
# Add these exports
pulumi.export("external_dns_role_arn", external_dns_role.arn)
pulumi.export("cluster_autoscaler_role_arn", cluster_autoscaler_role.arn)
```

Then run `pulumi up` to update exports.

### Step 1.5: Commit and Push to ArgoCD Repository

```bash
cd builder-space-argocd

git add environments/
git commit -m "Add infrastructure manifests for ArgoCD management

- Add External-DNS configuration
- Add Cluster-Autoscaler configuration
- Add Cert-Manager and ClusterIssuers configuration"

git push origin main
```

## Phase 2: Transition to ArgoCD Management

### Step 2.1: Verify ArgoCD is Running

```bash
# Check ArgoCD pods
kubectl get pods -n argocd

# Check ArgoCD Application
kubectl get application infrastructure-bootstrap -n argocd

# If the Application doesn't exist yet, it will be created by Pulumi
```

### Step 2.2: Monitor ArgoCD Sync

The ArgoCD Application is already configured to sync from `builder-space-argocd`. Once you push the manifests, ArgoCD will:

1. Detect the new resources
2. Compare with the cluster state
3. Sync the resources (create new or update existing)

```bash
# Watch ArgoCD sync status
kubectl get application infrastructure-bootstrap -n argocd -w

# Or use ArgoCD CLI
argocd app get infrastructure-bootstrap

# Check sync status
argocd app sync infrastructure-bootstrap
```

### Step 2.3: Verify Resources are Synced

```bash
# Check External-DNS
kubectl get pods -n external-dns
kubectl get deployment -n external-dns

# Check Cluster-Autoscaler
kubectl get pods -n kube-system | grep cluster-autoscaler
kubectl get deployment cluster-autoscaler -n kube-system

# Check Cert-Manager
kubectl get pods -n cert-manager
kubectl get clusterissuers
```

### Step 2.4: Verify Services are Working

```bash
# Test External-DNS is creating DNS records
kubectl logs -n external-dns deployment/external-dns --tail=50

# Test Cluster-Autoscaler is monitoring
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=50

# Test Cert-Manager is ready
kubectl get certificates -A
```

## Phase 3: Remove Pulumi-Managed Resources

⚠️ **IMPORTANT**: Only proceed after verifying ArgoCD is successfully managing the resources.

### Step 3.1: Backup Current State

```bash
cd builder-space/infra-k8s

# Backup Pulumi state
pulumi stack export --file backup-before-cleanup-$(date +%Y%m%d).json

# Backup the current __main__.py
cp __main__.py __main__.py.backup-$(date +%Y%m%d)
```

### Step 3.2: Update infra-k8s/__main__.py

Remove the following sections from `infra-k8s/__main__.py`:

```python
# REMOVE: External-DNS chart (lines ~299-326)
external_dns_chart = Chart("external-dns", ...)

# REMOVE: Cluster-Autoscaler chart (lines ~328-363)
cluster_autoscaler_chart = Chart("cluster-autoscaler", ...)

# REMOVE: Cert-Manager chart (lines ~183-198)
cert_manager_chart = Chart("cert-manager", ...)

# REMOVE: ClusterIssuers (lines ~200-233)
letsencrypt_staging = k8s.apiextensions.CustomResource(...)
letsencrypt_production = k8s.apiextensions.CustomResource(...)
```

**KEEP** the following:
```python
# KEEP: IAM roles (external_dns_role, cluster_autoscaler_role)
# These are AWS resources and should stay in Pulumi

# KEEP: Namespaces
namespaces = { ... }

# KEEP: ArgoCD Redis secret
argocd_redis_secret = ...

# KEEP: ArgoCD chart
argocd_chart = Chart("argocd", ...)

# KEEP: ArgoCD bootstrap application
argocd_bootstrap_app = k8s.apiextensions.CustomResource("argocd-bootstrap", ...)
```

### Step 3.3: Apply Changes

```bash
cd builder-space/infra-k8s

# Preview changes
pulumi preview

# Review the plan carefully - it should show:
# - Deletion of Helm releases (external-dns, cluster-autoscaler, cert-manager)
# - No changes to IAM roles
# - No changes to ArgoCD

# Apply if everything looks correct
pulumi up
```

### Step 3.4: Verify Cleanup

```bash
# Check that resources are still running (now managed by ArgoCD)
kubectl get pods -n external-dns
kubectl get pods -n kube-system | grep cluster-autoscaler
kubectl get pods -n cert-manager

# Check Pulumi no longer manages them
pulumi stack --show-urns | grep -E 'external-dns|cluster-autoscaler|cert-manager'
# Should show no results for the Helm charts

# Check ArgoCD is managing them
argocd app get infrastructure-bootstrap
kubectl get application infrastructure-bootstrap -n argocd -o yaml
```

## Phase 4: Commit Changes to builder-space

### Step 4.1: Commit Updated Pulumi Code

```bash
cd builder-space

git add infra-k8s/__main__.py
git commit -m "Migrate K8s resources to ArgoCD management

- Remove External-DNS, Cluster-Autoscaler, Cert-Manager Helm charts from Pulumi
- Keep IAM roles in Pulumi (required by K8s ServiceAccounts)
- ArgoCD now manages these resources via builder-space-argocd repository"

git push origin main
```

### Step 4.2: Update Documentation

Update `infra-k8s/README.md` to reflect the new architecture:

```markdown
## Architecture

- **Namespace:** `argocd`
- **Management:** Pulumi deploys ArgoCD, which manages other K8s resources via GitOps
- **GitOps Repository:** https://github.com/aiqs4/builder-space-argocd

## Managed by ArgoCD

The following resources are now managed via ArgoCD from the builder-space-argocd repository:
- External-DNS
- Cluster-Autoscaler
- Cert-Manager
- Application deployments

## Managed by Pulumi

The following resources remain managed by Pulumi:
- ArgoCD installation
- IAM roles for service accounts
- AWS infrastructure (EKS, VPC, etc.)
```

## Troubleshooting

### Issue: ArgoCD Not Syncing

```bash
# Check ArgoCD Application status
kubectl get application infrastructure-bootstrap -n argocd -o yaml

# Check ArgoCD logs
kubectl logs -n argocd deployment/argocd-repo-server
kubectl logs -n argocd deployment/argocd-application-controller

# Force sync
argocd app sync infrastructure-bootstrap --force
```

### Issue: Resources Deleted During Pulumi Update

If resources were accidentally deleted:

```bash
# Rollback Pulumi changes
cd builder-space/infra-k8s
pulumi stack import < backup-before-cleanup-YYYYMMDD.json

# Or restore from backup
cp __main__.py.backup-YYYYMMDD __main__.py
pulumi up
```

### Issue: Duplicate Resources

If both Pulumi and ArgoCD try to manage the same resources:

```bash
# Check resource ownership
kubectl get deployment external-dns -n external-dns -o yaml | grep -A 5 labels

# Remove Pulumi-managed resources first
cd builder-space/infra-k8s
# Edit __main__.py to remove the Helm chart
pulumi up
```

### Issue: IAM Role Not Working

If pods can't assume IAM roles:

```bash
# Verify IAM role exists
aws iam get-role --role-name external-dns-role-XXXXX

# Verify ServiceAccount annotation
kubectl get serviceaccount external-dns -n external-dns -o yaml

# Verify OIDC provider
aws eks describe-cluster --name builder-space --region af-south-1 | grep oidc
```

## Verification Checklist

After migration, verify:

- [ ] ArgoCD Application shows "Synced" and "Healthy"
- [ ] External-DNS pods running and creating DNS records
- [ ] Cluster-Autoscaler pods running and monitoring nodes
- [ ] Cert-Manager pods running and ClusterIssuers ready
- [ ] IAM roles working (check pod logs for AWS API calls)
- [ ] Pulumi stack only shows ArgoCD and IAM resources
- [ ] No resource conflicts or duplicate resources
- [ ] All services functioning as before migration

## Rollback Procedure

If you need to rollback completely:

```bash
# 1. Restore Pulumi code
cd builder-space/infra-k8s
cp __main__.py.backup-YYYYMMDD __main__.py
pulumi up

# 2. Delete ArgoCD Application (optional)
kubectl delete application infrastructure-bootstrap -n argocd

# 3. Verify resources are managed by Pulumi again
pulumi stack --show-urns | grep -E 'external-dns|cluster-autoscaler|cert-manager'
```

## Post-Migration

After successful migration:

1. Monitor the cluster for 24-48 hours
2. Update team documentation
3. Train team on GitOps workflow
4. Set up ArgoCD notifications (Slack, email, etc.)
5. Configure ArgoCD SSO if needed
6. Set up RBAC in ArgoCD for team access

## Next Steps

- Add more applications to the builder-space-argocd repository
- Set up separate ArgoCD Projects for different teams/environments
- Configure ArgoCD Image Updater for automatic deployments
- Set up ArgoCD notifications and integrations
