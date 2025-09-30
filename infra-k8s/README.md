# ArgoCD Bootstrap - TL;DR

## Quick Start

1. **Deploy ArgoCD to EKS:**
   ```bash
   # Via GitHub Actions (Recommended)
   Go to Actions → "Deploy Kubernetes Resources (ArgoCD)" → Run workflow → Choose "up"
   
   # Or locally
   cd infra-k8s
   pip install -r requirements.txt
   pulumi login $PULUMI_BACKEND_URL
   pulumi stack select k8s --create
   pulumi up
   ```

2. **Access ArgoCD:**
   ```bash
   # Get LoadBalancer URL
   kubectl get svc argocd-server -n argocd
   
   # Get admin password
   kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d
   
   # Access via browser: http://LOADBALANCER_URL
   # Username: admin
   # Password: (output from above command)
   ```

3. **Port Forward (Alternative):**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   # Access: http://localhost:8080
   ```

## Architecture

This stack deploys ArgoCD and creates IAM roles for Kubernetes ServiceAccounts (IRSA).

### What's Deployed by This Stack

**ArgoCD Components:**
- **Namespace:** `argocd`
- **Service Type:** LoadBalancer (AWS NLB)
- **Chart:** `argo-cd` v7.8.2 from ArgoProj Helm repository
- **Access:** HTTP (insecure mode for simplicity)
- **Bootstrap App:** References `builder-space-argocd` repository

**IAM Roles (for ServiceAccounts):**
- External-DNS role with Route53 permissions
- Cluster-Autoscaler role with Auto Scaling permissions
- Referenced by Kubernetes pods via IRSA (IAM Roles for Service Accounts)

**Other Components:**
- Cert-Manager for TLS certificate management
- ClusterIssuers for Let's Encrypt (staging and production)
- Kubernetes namespaces: `argocd`, `external-dns`, `cert-manager`

### GitOps Integration

After ArgoCD is deployed, it automatically syncs resources from the `builder-space-argocd` repository:

```
builder-space/infra-k8s (Pulumi)
  ├── ArgoCD installation
  ├── IAM roles
  └── ArgoCD Application (points to builder-space-argocd)
          │
          ▼
builder-space-argocd (Git)
  └── environments/prod/infrastructure/
      ├── external-dns/
      ├── cluster-autoscaler/
      ├── cert-manager/
      └── applications/
```

The ArgoCD Application resource is configured to automatically sync with the Git repository, enabling GitOps for all Kubernetes resources.

### Migration Path

For migrating Kubernetes resources from Pulumi to ArgoCD management, see the comprehensive guide:
- [`../argocd-transfer/README.md`](../argocd-transfer/README.md) - Overall strategy
- [`../argocd-transfer/TRANSFER-GUIDE.md`](../argocd-transfer/TRANSFER-GUIDE.md) - Step-by-step instructions
- [`../argocd-transfer/IAM-ROLES.md`](../argocd-transfer/IAM-ROLES.md) - IAM roles management

## Pipeline Integration

The new `pulumi-k8s.yml` workflow:
- Uses same Pulumi credentials as main infrastructure
- Connects to EKS via kubeconfig
- Deploys ArgoCD Helm chart
- Exports access endpoints and credentials

## Next Steps

### 1. Change Default Admin Password

```bash
# Login to ArgoCD CLI
argocd login LOADBALANCER_URL --username admin --password $(kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d)

# Change password
argocd account update-password
```

### 2. Get IAM Role ARNs for GitOps

```bash
# Get IAM role ARNs needed for ArgoCD manifests
pulumi stack output iam_roles

# Output will show:
# {
#   "external_dns_role_arn": "arn:aws:iam::123456789012:role/external-dns-role-...",
#   "cluster_autoscaler_role_arn": "arn:aws:iam::123456789012:role/cluster-autoscaler-role-..."
# }
```

### 3. Setup GitOps Repository

Follow the comprehensive guide in [`../argocd-transfer/`](../argocd-transfer/) to:
1. Set up the `builder-space-argocd` repository structure
2. Copy pre-configured manifests for infrastructure components
3. Update manifests with your IAM role ARNs
4. Push to Git and let ArgoCD sync

### 4. Verify ArgoCD Sync

```bash
# Check ArgoCD Application status
kubectl get application infrastructure-bootstrap -n argocd

# Or use ArgoCD CLI
argocd app list
argocd app get infrastructure-bootstrap

# Watch sync progress
kubectl get application infrastructure-bootstrap -n argocd -w
```

### 5. Enable HTTPS/TLS (Optional)

For production use, configure TLS:
1. Obtain a TLS certificate (Let's Encrypt via Cert-Manager or AWS ACM)
2. Update ArgoCD server configuration to enable TLS
3. Update LoadBalancer to use HTTPS

### 6. Configure SSO (Optional)

For team access, configure SSO with:
- GitHub OAuth
- Google OAuth
- SAML
- OIDC

See [ArgoCD Documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/) for details.

---
**Note:** This setup is optimized for development. Consider security hardening for production use.