# Quick Reference

## Common Commands

### Cluster Access
```bash
# Update kubeconfig
aws eks update-kubeconfig --region af-south-1 --name builder-space

# Verify access
kubectl get nodes
kubectl cluster-info
```

### Add-on Management
```bash
# List all add-ons
aws eks list-addons --cluster-name builder-space

# Describe specific add-on
aws eks describe-addon --cluster-name builder-space --addon-name vpc-cni

# Update add-on (if needed)
aws eks update-addon --cluster-name builder-space --addon-name vpc-cni
```

### Karpenter Operations
```bash
# Check Karpenter status
kubectl -n kube-system get pods -l app.kubernetes.io/name=karpenter

# View Karpenter logs
kubectl -n kube-system logs -l app.kubernetes.io/name=karpenter -f

# List NodePools
kubectl get nodepools

# List provisioned nodes
kubectl get nodes -l karpenter.sh/nodepool

# Force node refresh
kubectl delete node <node-name>
```

### External DNS Operations
```bash
# Check External DNS status
kubectl -n kube-system get pods -l app=external-dns

# View External DNS logs
kubectl -n kube-system logs -l app=external-dns -f

# List managed DNS records
aws route53 list-resource-record-sets --hosted-zone-id <zone-id>
```

### Database Operations
```bash
# Get database endpoint
pulumi stack output database_endpoint

# Connect to database (with IAM auth)
export PGPASSWORD=$(aws rds generate-db-auth-token \
  --hostname <endpoint> \
  --port 5432 \
  --username postgres \
  --region af-south-1)
psql -h <endpoint> -U postgres -d builderspace

# Check database status
aws rds describe-db-clusters --db-cluster-identifier builder-space-postgres
```

### Scaling Operations
```bash
# Scale initial node group
aws eks update-nodegroup-config \
  --cluster-name builder-space \
  --nodegroup-name primary-nodes \
  --scaling-config desiredSize=5,minSize=3,maxSize=10

# Let Karpenter handle the rest!
```

### Monitoring
```bash
# Watch all pods
kubectl get pods -A -w

# Check pod resources
kubectl top pods -A
kubectl top nodes

# View events
kubectl get events -A --sort-by='.lastTimestamp'

# Check add-on health
kubectl -n kube-system get pods | grep -E 'coredns|ebs|vpc-cni'
```

### Storage Operations
```bash
# List storage classes (EBS)
kubectl get sc

# Create PVC (example)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: gp3
EOF

# Check PVC status
kubectl get pvc
kubectl get pv
```

### DNS Setup (Example)
```yaml
# Service with External DNS annotation
apiVersion: v1
kind: Service
metadata:
  name: myapp
  annotations:
    external-dns.alpha.kubernetes.io/hostname: myapp.amano.services
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
  selector:
    app: myapp
```

### Troubleshooting
```bash
# Check control plane logs
aws logs tail /aws/eks/builder-space/cluster --follow

# Describe node
kubectl describe node <node-name>

# Check IAM roles
aws iam get-role --role-name eks-cluster-role
aws iam get-role --role-name eks-node-role

# Verify OIDC provider
aws iam list-open-id-connect-providers

# Check security groups
aws ec2 describe-security-groups \
  --filters "Name=tag:kubernetes.io/cluster/builder-space,Values=owned"
```

### Cost Optimization
```bash
# View Karpenter provisioning decisions
kubectl -n kube-system logs -l app.kubernetes.io/name=karpenter | grep "launched"

# Check spot vs on-demand usage
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, capacity: .metadata.labels["karpenter.sh/capacity-type"]}'

# Database scaling info
aws rds describe-db-clusters \
  --db-cluster-identifier builder-space-postgres \
  --query 'DBClusters[0].ServerlessV2ScalingConfiguration'
```

### Cleanup
```bash
# Delete test resources
kubectl delete namespace test

# Scale down (let Karpenter consolidate)
kubectl scale deployment myapp --replicas=0

# Full cleanup
pulumi destroy --stack eks
```

## Configuration Values

### Current Settings
- **Region**: af-south-1
- **Cluster Name**: builder-space
- **Node Count**: 3 (initial)
- **Instance Type**: t3.xlarge
- **Kubernetes Version**: 1.31
- **Subnets**: /22 (1,022 IPs each)

### Domains
1. amano.services
2. tekanya.services
3. lightsphere.space
4. sosolola.cloud

### Add-on Versions (EKS 1.31)
- VPC CNI: v1.18.5
- CoreDNS: v1.11.3
- Pod Identity Agent: v1.3.4
- EBS CSI Driver: v1.37.0
- Karpenter: v1.0.6
- External DNS: v0.14.2

## Important ARNs
```bash
# Get from outputs
pulumi stack output

# Or query directly
aws eks describe-cluster --name builder-space --query 'cluster.arn'
```
