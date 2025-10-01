# ArgoCD Integration - Quick Reference

This is a quick reference card for common operations when working with the ArgoCD integration.

## 🚀 Quick Commands

### Get IAM Role ARNs

```bash
cd infra-k8s
pulumi stack output iam_roles
```

### Check ArgoCD Application Status

```bash
# Via kubectl
kubectl get application infrastructure-bootstrap -n argocd
kubectl describe application infrastructure-bootstrap -n argocd

# Via ArgoCD CLI
argocd app list
argocd app get infrastructure-bootstrap
```

### Sync ArgoCD Application

```bash
# Manual sync
argocd app sync infrastructure-bootstrap

# Force sync (refresh from Git)
argocd app sync infrastructure-bootstrap --force

# Sync with prune
argocd app sync infrastructure-bootstrap --prune
```

### View ArgoCD Logs

```bash
# Application controller
kubectl logs -n argocd deployment/argocd-application-controller --tail=100 -f

# Repo server
kubectl logs -n argocd deployment/argocd-repo-server --tail=100 -f

# Server
kubectl logs -n argocd deployment/argocd-server --tail=100 -f
```

### Verify Components

```bash
# Check all ArgoCD pods
kubectl get pods -n argocd

# Check synced resources
kubectl get all -n external-dns
kubectl get all -n kube-system | grep cluster-autoscaler
kubectl get all -n cert-manager

# Check ClusterIssuers
kubectl get clusterissuers
```

## 📋 Pre-Migration Checklist

- [ ] EKS cluster is deployed and accessible
- [ ] ArgoCD is installed and running
- [ ] `builder-space-argocd` repository is created
- [ ] IAM role ARNs are retrieved from Pulumi
- [ ] You have write access to `builder-space-argocd` repository

## 📝 Migration Steps Summary

### 1. Setup GitOps Repository

```bash
git clone https://github.com/aiqs4/builder-space-argocd.git
cd builder-space-argocd
mkdir -p environments/prod/infrastructure/{external-dns,cluster-autoscaler,cert-manager}
```

### 2. Copy Configurations

```bash
# Copy from builder-space/argocd-transfer/ to builder-space-argocd/
cp builder-space/argocd-transfer/external-dns/* \
   builder-space-argocd/environments/prod/infrastructure/external-dns/

cp builder-space/argocd-transfer/cluster-autoscaler/* \
   builder-space-argocd/environments/prod/infrastructure/cluster-autoscaler/

cp builder-space/argocd-transfer/cert-manager/* \
   builder-space-argocd/environments/prod/infrastructure/cert-manager/
```

### 3. Update Configurations

Edit the following files with your values:
- `external-dns/values.yaml` - IAM role ARN, domain, region
- `cluster-autoscaler/values.yaml` - IAM role ARN, cluster name, region
- `cert-manager/cluster-issuers.yaml` - Email address

### 4. Push to Git

```bash
cd builder-space-argocd
git add environments/
git commit -m "Add infrastructure manifests"
git push origin main
```

### 5. Verify ArgoCD Sync

```bash
kubectl get application infrastructure-bootstrap -n argocd -w
argocd app sync infrastructure-bootstrap
```

### 6. Remove from Pulumi

After verifying everything works:

```bash
cd builder-space/infra-k8s
# Edit __main__.py to remove Helm charts
pulumi up
```

## 🔍 Troubleshooting Quick Fixes

### ArgoCD Not Syncing

```bash
# Check Application status
kubectl describe application infrastructure-bootstrap -n argocd

# Check repo-server logs
kubectl logs -n argocd deployment/argocd-repo-server --tail=50

# Force refresh
argocd app sync infrastructure-bootstrap --force
```

### External-DNS Not Working

```bash
# Check pods
kubectl get pods -n external-dns

# Check logs
kubectl logs -n external-dns deployment/external-dns --tail=50

# Verify IAM role
kubectl get serviceaccount external-dns -n external-dns -o yaml | grep role-arn
```

### Cluster-Autoscaler Not Working

```bash
# Check pods
kubectl get pods -n kube-system | grep cluster-autoscaler

# Check logs
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=50

# Verify IAM role
kubectl get serviceaccount cluster-autoscaler -n kube-system -o yaml | grep role-arn
```

### Cert-Manager Not Working

```bash
# Check pods
kubectl get pods -n cert-manager

# Check ClusterIssuers
kubectl get clusterissuers

# Check logs
kubectl logs -n cert-manager deployment/cert-manager --tail=50
```

## 🔄 Common Workflows

### Add New Application to ArgoCD

```bash
cd builder-space-argocd
mkdir -p environments/prod/applications/myapp
# Add Kubernetes manifests
git add environments/prod/applications/myapp/
git commit -m "Add myapp"
git push origin main
# ArgoCD will automatically detect and sync
```

### Update Application Configuration

```bash
cd builder-space-argocd
# Edit manifest
git add .
git commit -m "Update myapp configuration"
git push origin main
# ArgoCD will automatically sync (if automated sync is enabled)
```

### Rollback Application

```bash
# Via ArgoCD CLI
argocd app rollback infrastructure-bootstrap <REVISION>

# Via Git
cd builder-space-argocd
git revert <commit-hash>
git push origin main
```

### View Sync History

```bash
# Via ArgoCD CLI
argocd app history infrastructure-bootstrap

# Via kubectl
kubectl get application infrastructure-bootstrap -n argocd -o yaml | grep -A 20 history
```

## 📚 Documentation Links

- **Main Strategy**: [`README.md`](README.md)
- **Step-by-Step Guide**: [`TRANSFER-GUIDE.md`](TRANSFER-GUIDE.md)
- **IAM Roles Guide**: [`IAM-ROLES.md`](IAM-ROLES.md)
- **External-DNS**: [`external-dns/README.md`](external-dns/README.md)
- **Cluster-Autoscaler**: [`cluster-autoscaler/README.md`](cluster-autoscaler/README.md)
- **Cert-Manager**: [`cert-manager/README.md`](cert-manager/README.md)

## 🆘 Getting Help

1. Check the component-specific README in each subdirectory
2. Review ArgoCD logs: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller`
3. Check component logs: `kubectl logs -n <namespace> <component>`
4. Review the troubleshooting sections in each guide
5. Check ArgoCD UI for visual status: http://LOADBALANCER_URL

## 🎯 Key Points to Remember

1. **IAM roles stay in Pulumi** - They're AWS resources, not K8s resources
2. **ArgoCD manages K8s resources** - Deployments, Services, ConfigMaps, etc.
3. **Use staging first** - Test changes in staging ClusterIssuer before production
4. **Monitor closely** - Watch logs during initial migration
5. **Backup state** - Always backup Pulumi state before major changes
6. **Git is source of truth** - All K8s changes should go through Git
7. **Automated sync** - ArgoCD automatically syncs changes from Git
8. **Manual intervention** - You can disable auto-sync for critical apps

## 🔐 Security Best Practices

1. Use separate IAM roles for each service
2. Follow principle of least privilege
3. Store secrets in AWS Secrets Manager or Sealed Secrets
4. Enable RBAC in ArgoCD
5. Configure SSO for team access
6. Use Git commit signing
7. Enable branch protection in GitHub
8. Review all changes before merging to main

## 📊 Monitoring

### Key Metrics to Watch

- ArgoCD sync status
- Pod health in all namespaces
- IAM role assumption errors
- DNS record creation/updates
- Cluster autoscaling events
- Certificate issuance/renewal

### Setup Alerts

```bash
# Example: Alert on sync failures
kubectl create -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-sync-failed: |
    - send: [slack]
EOF
```

## 🔄 Regular Maintenance

### Weekly

- [ ] Review ArgoCD sync status
- [ ] Check for failed syncs
- [ ] Review pod health
- [ ] Check certificate expiry

### Monthly

- [ ] Update Helm chart versions
- [ ] Review IAM policies
- [ ] Audit access logs
- [ ] Review and clean up unused resources

### Quarterly

- [ ] Review overall architecture
- [ ] Update documentation
- [ ] Train team on new features
- [ ] Disaster recovery drill
