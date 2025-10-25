# 🚀 Deployment Checklist

## Pre-Deployment

### 1. Environment Setup
- [ ] AWS CLI configured
  ```bash
  aws sts get-caller-identity
  ```
- [ ] Python environment ready
  ```bash
  python --version  # Should be 3.9+
  ```
- [ ] Pulumi installed
  ```bash
  pulumi version
  ```
- [ ] kubectl installed
  ```bash
  kubectl version --client
  ```

### 2. Install Dependencies
```bash
cd /home/alex/work/src/Amano/src/builder-space
pip install -r requirements.txt
```

### 3. Configuration
- [ ] Set database password
  ```bash
  pulumi config set --secret db_password "$(openssl rand -base64 32)"
  ```
- [ ] Verify all config values
  ```bash
  pulumi config --show-secrets
  ```
- [ ] Check GitHub Actions role ARN
  ```bash
  aws iam get-role --role-name github-deploy-eks
  ```

### 4. Pre-flight Checks
- [ ] AWS account has sufficient quotas
  - VPCs: 5+ available
  - Elastic IPs: 2+ available
  - EKS clusters: 1+ available
  - RDS instances: 1+ available
  
- [ ] Region is correct (af-south-1)
  ```bash
  pulumi config get aws:region
  ```

## Deployment

### 5. Syntax Check
```bash
python -m py_compile __main__.py src/*.py
```
- [ ] No syntax errors

### 6. Dry Run
```bash
pulumi preview --stack eks
```
- [ ] Review all resources to be created
- [ ] Verify no unexpected deletions
- [ ] Check estimated costs

### 7. Deploy Infrastructure
```bash
pulumi up --stack eks --yes
```
- [ ] Monitor deployment progress
- [ ] Wait for completion (~15-20 minutes)
- [ ] No errors in output

## Post-Deployment

### 8. Verify Cluster Access
```bash
# Update kubeconfig
aws eks update-kubeconfig --region af-south-1 --name builder-space

# Test access
kubectl get nodes
kubectl cluster-info
```
- [ ] Nodes are Ready
- [ ] Cluster endpoint accessible

### 9. Verify Add-ons
```bash
# List add-ons
aws eks list-addons --cluster-name builder-space

# Check pods
kubectl -n kube-system get pods
```
- [ ] vpc-cni pods running
- [ ] coredns pods running
- [ ] ebs-csi-controller running
- [ ] ebs-csi-node running

### 10. Verify External DNS
```bash
kubectl -n kube-system get pods -l app=external-dns
kubectl -n kube-system logs -l app=external-dns --tail=50
```
- [ ] External DNS pod running
- [ ] No error logs
- [ ] Successfully watching for services

### 11. Verify Karpenter
```bash
kubectl -n kube-system get pods -l app.kubernetes.io/name=karpenter
kubectl get nodepools
kubectl get ec2nodeclasses
```
- [ ] Karpenter pod running
- [ ] NodePool created
- [ ] EC2NodeClass created

### 12. Verify Database
```bash
# Get endpoint
pulumi stack output database_endpoint

# Test connection (from within VPC or bastion)
aws rds describe-db-clusters --db-cluster-identifier builder-space-postgres
```
- [ ] Cluster status: available
- [ ] Serverless scaling configured (0.5-2.0 ACU)

### 13. Test Autoscaling
```bash
# Deploy test workload
kubectl create deployment test --image=nginx --replicas=10

# Watch Karpenter logs
kubectl -n kube-system logs -l app.kubernetes.io/name=karpenter -f
```
- [ ] Karpenter provisions new nodes if needed
- [ ] Pods get scheduled

### 14. Test External DNS
```bash
# Create test service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: test-dns
  annotations:
    external-dns.alpha.kubernetes.io/hostname: test.amano.services
spec:
  type: LoadBalancer
  ports:
    - port: 80
  selector:
    app: test
EOF

# Wait 2-3 minutes, then check DNS
dig test.amano.services
```
- [ ] DNS record created in Route53
- [ ] Record points to LoadBalancer

### 15. Security Checks
```bash
# Verify OIDC provider
aws iam list-open-id-connect-providers

# Check Pod Identity associations
aws eks list-pod-identity-associations --cluster-name builder-space

# Verify encryption
aws rds describe-db-clusters \
  --db-cluster-identifier builder-space-postgres \
  --query 'DBClusters[0].StorageEncrypted'
```
- [ ] OIDC provider exists
- [ ] Pod Identity associations created (external-dns, karpenter)
- [ ] Database encryption enabled

### 16. Cost Validation
```bash
# Check Karpenter is using spot
kubectl get nodes -o json | \
  jq '.items[] | {name: .metadata.name, capacity: .metadata.labels["karpenter.sh/capacity-type"]}'

# Check database scaling
aws rds describe-db-clusters \
  --db-cluster-identifier builder-space-postgres \
  --query 'DBClusters[0].ServerlessV2ScalingConfiguration'
```
- [ ] Some nodes using SPOT capacity
- [ ] Database scaling is 0.5-2.0 ACU

## Documentation

### 17. Save Outputs
```bash
pulumi stack output --json > outputs.json
pulumi stack export > stack-export.json
```
- [ ] Outputs saved
- [ ] Stack state exported (backup)

### 18. Update Documentation
- [ ] Document any custom configurations
- [ ] Note any issues encountered
- [ ] Update team wiki/docs

## Monitoring Setup

### 19. Enable Monitoring
```bash
# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/eks/builder-space

# Set up alarms (optional)
# Create CloudWatch alarms for:
# - Node CPU/Memory usage
# - Pod failures
# - Database CPU/Memory
```
- [ ] Control plane logs flowing to CloudWatch
- [ ] Consider setting up alarms

### 20. Backup Verification
```bash
# Verify database backup
aws rds describe-db-clusters \
  --db-cluster-identifier builder-space-postgres \
  --query 'DBClusters[0].BackupRetentionPeriod'
```
- [ ] Backup retention is 7 days
- [ ] Automated backups enabled

## Cleanup Test Resources

### 21. Remove Test Workloads
```bash
kubectl delete deployment test
kubectl delete service test-dns
```
- [ ] Test resources removed
- [ ] Karpenter consolidates unused nodes

## Final Validation

### 22. Full System Check
```bash
# Run comprehensive check
kubectl get all -A
kubectl top nodes
kubectl get events -A --sort-by='.lastTimestamp' | tail -20
```
- [ ] All system pods running
- [ ] No error events
- [ ] Resource usage normal

### 23. Smoke Test
- [ ] Deploy a simple application
- [ ] Verify it gets scheduled
- [ ] Verify it can access database (from pod)
- [ ] Verify external DNS creates record
- [ ] Verify LoadBalancer is accessible

## Sign-off

- [ ] Infrastructure deployed successfully
- [ ] All verification tests passed
- [ ] Documentation updated
- [ ] Team notified
- [ ] Monitoring enabled

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Cluster Name:** builder-space
**Region:** af-south-1
**EKS Version:** 1.31

## Rollback Procedure (If Needed)

If deployment fails:

```bash
# Restore old cluster.py
mv cluster.py.old cluster.py
rm -rf src/

# Restore old __main__.py
git checkout __main__.py

# Deploy old configuration
pulumi up --stack eks
```

Or complete cleanup:
```bash
pulumi destroy --stack eks
```

---

**Status:** ⬜ Not Started | 🔄 In Progress | ✅ Complete | ❌ Failed
