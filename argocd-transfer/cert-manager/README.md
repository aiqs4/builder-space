# Cert-Manager Configuration for ArgoCD

This directory contains the configuration for deploying Cert-Manager and ClusterIssuers via ArgoCD.

## Overview

Cert-Manager automates the management and issuance of TLS certificates from various sources, including Let's Encrypt.

## Files

- `application.yaml` - ArgoCD Application manifest (optional, for separate app)
- `values.yaml` - Helm chart values
- `cluster-issuers.yaml` - ClusterIssuer resources for Let's Encrypt
- `README.md` - This file

## Prerequisites

- Kubernetes cluster with internet access
- DNS configured (for HTTP-01 or DNS-01 challenges)
- Nginx Ingress Controller (for HTTP-01 challenges)

## Configuration

### Update cluster-issuers.yaml

Update the email address in both ClusterIssuers:

```yaml
spec:
  acme:
    email: your-email@example.com  # UPDATE: Your email for Let's Encrypt notifications
```

### Staging vs Production

**Staging ClusterIssuer:**
- Use for testing
- Higher rate limits
- Certificates not trusted by browsers
- Use for development

**Production ClusterIssuer:**
- Use for production
- Lower rate limits (50 certificates per week per domain)
- Certificates trusted by browsers
- Use after testing with staging

## Deployment

### With infrastructure-bootstrap Application

The infrastructure-bootstrap app will automatically sync this configuration when you push it to the builder-space-argocd repository.

### As Separate Application

Use the `application.yaml` file to create a dedicated ArgoCD Application.

## Verification

After deployment, verify Cert-Manager is working:

```bash
# Check Cert-Manager pods
kubectl get pods -n cert-manager

# Check ClusterIssuers
kubectl get clusterissuers

# Verify ClusterIssuers are ready
kubectl get clusterissuers -o wide

# Check Cert-Manager logs
kubectl logs -n cert-manager deployment/cert-manager --tail=50

# Check webhook
kubectl get validatingwebhookconfigurations | grep cert-manager
kubectl get mutatingwebhookconfigurations | grep cert-manager
```

Expected output for ClusterIssuers:
```
NAME                     READY   AGE
letsencrypt-production   True    5m
letsencrypt-staging      True    5m
```

## Usage

### Create a Certificate (Declarative)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-tls
  namespace: default
spec:
  secretName: example-com-tls
  issuerRef:
    name: letsencrypt-staging  # Use letsencrypt-production for prod
    kind: ClusterIssuer
  dnsNames:
    - example.com
    - www.example.com
```

### Use with Ingress (Automatic)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging  # or letsencrypt-production
    kubernetes.io/ingress.class: nginx
spec:
  tls:
  - hosts:
    - example.com
    secretName: example-com-tls  # Cert-Manager will create this secret
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

## Testing

### Test with Staging

1. Create a test Certificate with staging issuer:

```bash
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: test-certificate
  namespace: default
spec:
  secretName: test-tls
  issuerRef:
    name: letsencrypt-staging
    kind: ClusterIssuer
  dnsNames:
    - test.your-domain.com
EOF
```

2. Watch certificate issuance:

```bash
# Watch certificate status
kubectl get certificate test-certificate -w

# Check CertificateRequest
kubectl get certificaterequest

# Check Order (ACME challenge)
kubectl get orders

# Check Challenge
kubectl get challenges

# Check logs
kubectl logs -n cert-manager deployment/cert-manager --tail=100
```

3. Verify certificate:

```bash
# Check secret
kubectl get secret test-tls -o yaml

# View certificate details
kubectl get certificate test-certificate -o yaml

# Check certificate expiry
kubectl get certificate test-certificate -o jsonpath='{.status.renewalTime}'
```

4. Cleanup:

```bash
kubectl delete certificate test-certificate
kubectl delete secret test-tls
```

### Switch to Production

After testing with staging, switch to production:

1. Update your Certificate or Ingress to use `letsencrypt-production`
2. Delete the old staging certificate secret
3. Apply the updated manifest
4. Verify the new certificate is issued

## Troubleshooting

### Issue: ClusterIssuer Not Ready

**Check status:**
```bash
kubectl describe clusterissuer letsencrypt-staging
kubectl describe clusterissuer letsencrypt-production
```

**Common causes:**
1. Cert-Manager pods not running
2. Invalid ACME email
3. Network issues

**Solution:**
```bash
# Check Cert-Manager pods
kubectl get pods -n cert-manager

# Check Cert-Manager logs
kubectl logs -n cert-manager deployment/cert-manager --tail=100
```

### Issue: Certificate Not Issued

**Check certificate status:**
```bash
kubectl describe certificate YOUR_CERTIFICATE_NAME

# Check CertificateRequest
kubectl get certificaterequest -o wide

# Check Order
kubectl describe order YOUR_ORDER_NAME

# Check Challenge
kubectl describe challenge YOUR_CHALLENGE_NAME
```

**Common causes:**
1. DNS not configured correctly
2. HTTP-01 challenge failed (no ingress controller or wrong configuration)
3. Rate limit exceeded
4. Domain validation failed

**Solution for HTTP-01:**
```bash
# Ensure ingress controller is running
kubectl get pods -n ingress-nginx

# Check ingress
kubectl get ingress -A

# Test challenge endpoint
curl http://your-domain.com/.well-known/acme-challenge/test
```

### Issue: Rate Limit Exceeded

Let's Encrypt has rate limits:
- **50 certificates per registered domain per week**
- **5 duplicate certificates per week**

**Solution:**
1. Use staging issuer for testing
2. Wait for rate limit to reset (weekly)
3. Use different subdomains

### Issue: Webhook Connection Refused

**Check webhook:**
```bash
kubectl get validatingwebhookconfigurations cert-manager-webhook
kubectl describe validatingwebhookconfigurations cert-manager-webhook

# Check service
kubectl get service cert-manager-webhook -n cert-manager

# Check endpoint
kubectl get endpoints cert-manager-webhook -n cert-manager
```

**Solution:**
```bash
# Restart cert-manager pods
kubectl rollout restart deployment/cert-manager -n cert-manager
kubectl rollout restart deployment/cert-manager-webhook -n cert-manager
```

## Migration from Pulumi

When migrating from Pulumi-managed Cert-Manager:

1. Deploy via ArgoCD first
2. Verify it's working
3. Migrate existing certificates (if any)
4. Remove from Pulumi

### Step-by-Step Migration

```bash
# 1. Update cluster-issuers.yaml with your email

# 2. Push to builder-space-argocd repository
cd builder-space-argocd
git add environments/prod/infrastructure/cert-manager/
git commit -m "Add Cert-Manager configuration"
git push origin main

# 3. Wait for ArgoCD to sync
kubectl get application infrastructure-bootstrap -n argocd -w

# 4. Verify Cert-Manager is working
kubectl get pods -n cert-manager
kubectl get clusterissuers

# 5. Migrate existing certificates (if any)
kubectl get certificates -A

# 6. Remove from Pulumi
cd builder-space/infra-k8s
# Edit __main__.py to remove cert_manager_chart and cluster issuers
pulumi up
```

## Best Practices

1. **Use Staging First**: Always test with staging issuer before production
2. **Monitor Rate Limits**: Keep track of certificate issuance
3. **Set Renewal Time**: Certificates auto-renew at 2/3 of their lifetime
4. **Use Namespaced Issuers**: For team/environment isolation
5. **Configure Notifications**: Set up alerts for certificate expiry
6. **Backup Certificates**: Store important certificates externally

## Advanced Configuration

### DNS-01 Challenge

For wildcard certificates or when HTTP-01 is not available:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-dns
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-dns
    solvers:
    - dns01:
        route53:
          region: af-south-1
          # IAM role for Route53 access
          # Similar to External-DNS, needs IAM role via ServiceAccount
```

### Certificate Renewal

Cert-Manager automatically renews certificates at 2/3 of their lifetime (60 days for Let's Encrypt 90-day certs).

Monitor renewal:
```bash
# Check renewal time
kubectl get certificates -A -o custom-columns=NAME:.metadata.name,RENEWAL:.status.renewalTime

# Force renewal (for testing)
kubectl annotate certificate YOUR_CERT cert-manager.io/issue-temporary-certificate="true" --overwrite
```

## References

- [Cert-Manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Cert-Manager Tutorials](https://cert-manager.io/docs/tutorials/)
- [Helm Chart](https://github.com/cert-manager/cert-manager/tree/master/deploy/charts/cert-manager)
- [Rate Limits](https://letsencrypt.org/docs/rate-limits/)
