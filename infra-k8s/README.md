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

- **Namespace:** `argocd`
- **Service Type:** LoadBalancer (AWS NLB)
- **Chart:** `argo-cd` v7.7.9 from ArgProj Helm repository
- **Access:** HTTP (insecure mode for simplicity)

## Pipeline Integration

The new `pulumi-k8s.yml` workflow:
- Uses same Pulumi credentials as main infrastructure
- Connects to EKS via kubeconfig
- Deploys ArgoCD Helm chart
- Exports access endpoints and credentials

## Next Steps

1. Change default admin password
2. Configure ArgoCD applications
3. Set up Git repositories for GitOps
4. Enable HTTPS/TLS (optional)

---
**Note:** This setup is optimized for development. Consider security hardening for production use.