# External-DNS Configuration for ArgoCD

This directory contains the configuration for deploying External-DNS via ArgoCD.

## Overview

External-DNS automatically creates DNS records in Route53 for Kubernetes Ingress and Service resources.

## Files

- `application.yaml` - ArgoCD Application manifest
- `values.yaml` - Helm chart values
- `README.md` - This file

## Prerequisites

- IAM role created by Pulumi with Route53 permissions
- OIDC provider configured for the EKS cluster
- Service Account annotation with IAM role ARN

## Configuration

### Get IAM Role ARN

The IAM role is created by Pulumi in `builder-space/infra-k8s/__main__.py`:

```bash
cd builder-space/infra-k8s
pulumi stack output external_dns_role_arn
```

Or manually find it in AWS Console or CLI:

```bash
aws iam list-roles | grep external-dns-role
```

### Update values.yaml

Update the following values in `values.yaml`:

1. **IAM Role ARN** (from Pulumi output):
   ```yaml
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT_ID:role/external-dns-role-XXXXX
   ```

2. **Domain Filter** (your domain):
   ```yaml
   domainFilters:
     - your-domain.com  # Replace with your domain
   ```

3. **TXT Owner ID** (cluster name):
   ```yaml
   txtOwnerId: builder-space  # Or your cluster name
   ```

4. **AWS Region**:
   ```yaml
   aws:
     region: af-south-1  # Or your region
   ```

## Deployment Options

### Option 1: Single Application (Recommended)

Include as part of the infrastructure-bootstrap Application:

```yaml
# In builder-space-argocd/environments/prod/infrastructure/
# The infrastructure-bootstrap app will sync all subdirectories
```

### Option 2: Separate Application

Create a dedicated ArgoCD Application for External-DNS:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: external-dns
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/aiqs4/builder-space-argocd.git
    targetRevision: HEAD
    path: environments/prod/infrastructure/external-dns
  destination:
    server: https://kubernetes.default.svc
    namespace: external-dns
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## Verification

After deployment, verify External-DNS is working:

```bash
# Check pods
kubectl get pods -n external-dns

# Check logs
kubectl logs -n external-dns deployment/external-dns --tail=50

# Check ServiceAccount
kubectl get serviceaccount external-dns -n external-dns -o yaml

# Test DNS record creation
# Create a test service with annotation
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: test-dns
  namespace: default
  annotations:
    external-dns.alpha.kubernetes.io/hostname: test.your-domain.com
spec:
  type: LoadBalancer
  ports:
  - port: 80
  selector:
    app: test
EOF

# Check External-DNS logs for record creation
kubectl logs -n external-dns deployment/external-dns --tail=50 | grep test.your-domain.com

# Check Route53
aws route53 list-resource-record-sets --hosted-zone-id YOUR_ZONE_ID | grep test.your-domain.com

# Cleanup
kubectl delete service test-dns
```

## Troubleshooting

### Issue: Pods in CrashLoopBackOff

**Check logs:**
```bash
kubectl logs -n external-dns deployment/external-dns
```

**Common causes:**
1. IAM role ARN incorrect or missing
2. OIDC provider not configured
3. Route53 permissions missing

**Solution:**
```bash
# Verify IAM role
aws iam get-role --role-name external-dns-role-XXXXX

# Verify trust policy
aws iam get-role --role-name external-dns-role-XXXXX --query 'Role.AssumeRolePolicyDocument'

# Verify OIDC provider exists
aws iam list-open-id-connect-providers
```

### Issue: DNS Records Not Created

**Check logs:**
```bash
kubectl logs -n external-dns deployment/external-dns --tail=100
```

**Common causes:**
1. Domain filter mismatch
2. Annotation missing on Service/Ingress
3. No hosted zone for domain

**Solution:**
```bash
# Verify hosted zones
aws route53 list-hosted-zones

# Verify domain filter matches
kubectl get deployment external-dns -n external-dns -o yaml | grep domainFilters

# Add annotation to test service
kubectl annotate service test-service external-dns.alpha.kubernetes.io/hostname=test.your-domain.com
```

### Issue: Permission Denied Errors

**Check logs:**
```bash
kubectl logs -n external-dns deployment/external-dns | grep -i "access denied\|permission denied"
```

**Solution:**
Verify IAM role policy in Pulumi code (`builder-space/infra-k8s/__main__.py`):

```python
aws.iam.RolePolicy("external-dns-policy",
    role=external_dns_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "route53:ChangeResourceRecordSets",
                "route53:ListHostedZones",
                "route53:ListResourceRecordSets"
            ],
            "Resource": "*"
        }]
    })
)
```

## Migration from Pulumi

When migrating from Pulumi-managed External-DNS:

1. **DO NOT** delete the IAM role from Pulumi - it's still needed
2. Deploy via ArgoCD first
3. Verify it's working
4. Then remove the Helm chart from Pulumi

### Step-by-Step Migration

```bash
# 1. Ensure IAM role is exported from Pulumi
cd builder-space/infra-k8s
pulumi stack output external_dns_role_arn

# 2. Update values.yaml with the IAM role ARN

# 3. Push to builder-space-argocd repository
cd builder-space-argocd
git add environments/prod/infrastructure/external-dns/
git commit -m "Add External-DNS configuration"
git push origin main

# 4. Wait for ArgoCD to sync
kubectl get application infrastructure-bootstrap -n argocd -w

# 5. Verify External-DNS is working
kubectl get pods -n external-dns
kubectl logs -n external-dns deployment/external-dns --tail=50

# 6. Remove from Pulumi
cd builder-space/infra-k8s
# Edit __main__.py to remove external_dns_chart
pulumi up
```

## References

- [External-DNS Documentation](https://github.com/kubernetes-sigs/external-dns)
- [External-DNS AWS Guide](https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md)
- [Helm Chart](https://github.com/kubernetes-sigs/external-dns/tree/master/charts/external-dns)
