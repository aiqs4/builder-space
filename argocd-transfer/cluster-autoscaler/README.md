# Cluster-Autoscaler Configuration for ArgoCD

This directory contains the configuration for deploying Cluster-Autoscaler via ArgoCD.

## Overview

Cluster-Autoscaler automatically adjusts the size of the Kubernetes cluster based on pod resource requests and node utilization.

## Files

- `application.yaml` - ArgoCD Application manifest (optional, for separate app)
- `values.yaml` - Helm chart values
- `README.md` - This file

## Prerequisites

- IAM role created by Pulumi with Auto Scaling permissions
- OIDC provider configured for the EKS cluster
- Service Account annotation with IAM role ARN
- EKS node groups with proper tags

## Configuration

### Get IAM Role ARN

The IAM role is created by Pulumi in `builder-space/infra-k8s/__main__.py`:

```bash
cd builder-space/infra-k8s
pulumi stack output cluster_autoscaler_role_arn
```

Or manually find it:

```bash
aws iam list-roles | grep cluster-autoscaler-role
```

### Update values.yaml

Update the following values in `values.yaml`:

1. **IAM Role ARN** (from Pulumi output):
   ```yaml
   rbac:
     serviceAccount:
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT_ID:role/cluster-autoscaler-role-XXXXX
   ```

2. **Cluster Name**:
   ```yaml
   autoDiscovery:
     clusterName: builder-space  # Your EKS cluster name
   ```

3. **AWS Region**:
   ```yaml
   awsRegion: af-south-1  # Your AWS region
   ```

## Node Group Requirements

Cluster-Autoscaler requires node groups to have specific tags:

```
k8s.io/cluster-autoscaler/<cluster-name>: owned
k8s.io/cluster-autoscaler/enabled: true
```

These tags should be added by the EKS cluster creation (in Pulumi or via AWS Console).

## Deployment

### With infrastructure-bootstrap Application

The infrastructure-bootstrap app will automatically sync this configuration when you push it to the builder-space-argocd repository.

### As Separate Application

Use the `application.yaml` file to create a dedicated ArgoCD Application.

## Verification

After deployment, verify Cluster-Autoscaler is working:

```bash
# Check pods
kubectl get pods -n kube-system | grep cluster-autoscaler

# Check logs
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=50

# Check ServiceAccount
kubectl get serviceaccount cluster-autoscaler -n kube-system -o yaml

# Check if it's monitoring the cluster
kubectl logs -n kube-system deployment/cluster-autoscaler | grep "Cluster-autoscaler status"

# View scaling events
kubectl get events -n kube-system | grep -i "scale"

# View node group info
kubectl logs -n kube-system deployment/cluster-autoscaler | grep "node group"
```

## Testing Auto-Scaling

### Test Scale Up

```bash
# Create a deployment that requires more resources than available
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autoscaler-test
  namespace: default
spec:
  replicas: 10
  selector:
    matchLabels:
      app: autoscaler-test
  template:
    metadata:
      labels:
        app: autoscaler-test
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
EOF

# Watch nodes being added
kubectl get nodes -w

# Check autoscaler logs
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=50 | grep "Scale-up"

# Cleanup
kubectl delete deployment autoscaler-test
```

### Test Scale Down

After deleting the test deployment, wait 10-15 minutes and watch nodes being removed:

```bash
# Watch nodes
kubectl get nodes -w

# Check autoscaler logs for scale-down
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=50 | grep "Scale-down"
```

## Configuration Options

### Scale Down Settings

Adjust these in `values.yaml`:

```yaml
extraArgs:
  scale-down-delay-after-add: 10m        # Wait time after scale-up
  scale-down-unneeded-time: 10m          # Time before marking node as unneeded
  scale-down-delay-after-delete: 10s     # Wait time after node deletion
  scale-down-delay-after-failure: 3m     # Wait time after failed scale-down
```

### Resource Limits

```yaml
resources:
  limits:
    cpu: 100m
    memory: 300Mi
  requests:
    cpu: 100m
    memory: 300Mi
```

## Troubleshooting

### Issue: Pods in CrashLoopBackOff

**Check logs:**
```bash
kubectl logs -n kube-system deployment/cluster-autoscaler
```

**Common causes:**
1. IAM role ARN incorrect or missing
2. OIDC provider not configured
3. Auto Scaling permissions missing
4. Cluster name mismatch

**Solution:**
```bash
# Verify IAM role
aws iam get-role --role-name cluster-autoscaler-role-XXXXX

# Verify trust policy
aws iam get-role --role-name cluster-autoscaler-role-XXXXX --query 'Role.AssumeRolePolicyDocument'

# Verify cluster name
kubectl get deployment cluster-autoscaler -n kube-system -o yaml | grep clusterName
```

### Issue: Not Scaling Up

**Check logs:**
```bash
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=100
```

**Common causes:**
1. Node group tags missing
2. Max size reached
3. Resource constraints
4. Insufficient permissions

**Solution:**
```bash
# Check node group tags
aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?contains(Tags[?Key=='k8s.io/cluster-autoscaler/builder-space'].Key, 'k8s.io/cluster-autoscaler')]"

# Check max size
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names YOUR_ASG_NAME \
  --query "AutoScalingGroups[0].{Min:MinSize,Max:MaxSize,Desired:DesiredCapacity}"

# Check permissions
kubectl logs -n kube-system deployment/cluster-autoscaler | grep -i "access denied\|permission denied"
```

### Issue: Not Scaling Down

**Check logs:**
```bash
kubectl logs -n kube-system deployment/cluster-autoscaler | grep -i "scale-down"
```

**Common causes:**
1. Nodes have pods with local storage
2. Nodes have system pods
3. Scale-down delay not met
4. Pods with PodDisruptionBudget

**Solution:**
Check configuration:
```yaml
extraArgs:
  skip-nodes-with-local-storage: false    # Allow scale-down with local storage
  skip-nodes-with-system-pods: false      # Allow scale-down with system pods
```

## Migration from Pulumi

When migrating from Pulumi-managed Cluster-Autoscaler:

1. **DO NOT** delete the IAM role from Pulumi - it's still needed
2. Deploy via ArgoCD first
3. Verify it's working
4. Then remove the Helm chart from Pulumi

### Step-by-Step Migration

```bash
# 1. Ensure IAM role is exported from Pulumi
cd builder-space/infra-k8s
pulumi stack output cluster_autoscaler_role_arn

# 2. Update values.yaml with the IAM role ARN

# 3. Push to builder-space-argocd repository
cd builder-space-argocd
git add environments/prod/infrastructure/cluster-autoscaler/
git commit -m "Add Cluster-Autoscaler configuration"
git push origin main

# 4. Wait for ArgoCD to sync
kubectl get application infrastructure-bootstrap -n argocd -w

# 5. Verify Cluster-Autoscaler is working
kubectl get pods -n kube-system | grep cluster-autoscaler
kubectl logs -n kube-system deployment/cluster-autoscaler --tail=50

# 6. Remove from Pulumi
cd builder-space/infra-k8s
# Edit __main__.py to remove cluster_autoscaler_chart
pulumi up
```

## Best Practices

1. **Set Appropriate Limits**: Configure min/max node counts based on your needs
2. **Monitor Costs**: Auto-scaling can increase costs if not configured properly
3. **Use Node Affinity**: Guide pod placement for better resource utilization
4. **Configure PDBs**: Use PodDisruptionBudgets for critical applications
5. **Test Thoroughly**: Test scale-up and scale-down scenarios
6. **Monitor Metrics**: Watch cluster-autoscaler metrics and logs

## References

- [Cluster-Autoscaler Documentation](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [AWS EKS Autoscaling](https://docs.aws.amazon.com/eks/latest/userguide/autoscaling.html)
- [Cluster-Autoscaler FAQ](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md)
- [Helm Chart](https://github.com/kubernetes/autoscaler/tree/master/charts/cluster-autoscaler)
