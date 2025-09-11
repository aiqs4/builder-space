# Cost Optimization Guide for Builder Space EKS

## 💰 Current Cost Breakdown (af-south-1)

| Component | Cost/Hour | Hours/Month | Monthly Cost |
|-----------|-----------|-------------|--------------|
| EKS Cluster | $0.10 | 744 | $74.40 |
| t4g.small (2 nodes) | $0.0192 each | 744 | $28.58 |
| EBS gp3 (40GB total) | - | - | $8.00 |
| **Total** | | | **~$111** |

## 🎯 Ways to Reduce Costs

### 1. Use Spot Instances (Save ~70%)
```hcl
# In eks.tf, add to node group configuration:
capacity_type = "SPOT"
instance_types = ["t4g.small", "t3.small", "t3a.small"]
```
**Savings**: ~$20/month (Node costs: $28 → $8)

### 2. Single Node Development (Save ~$14)
```hcl
# In variables.tf or terraform.tfvars
node_desired_size = 1
node_min_size = 1
node_max_size = 2
```
**Savings**: ~$14/month (One less node)

### 3. Scheduled Shutdown (Save ~65% during off-hours)
- Use AWS Instance Scheduler to automatically stop nodes during nights/weekends
- Keep only the EKS control plane running (required)
- **Potential savings**: ~$65/month if stopped 16h/day + weekends

### 4. Optimize EBS Storage
```hcl
# Use smaller disk size for development
node_disk_size = 10 # Instead of 20GB
```
**Savings**: ~$4/month

### 5. Alternative: Fargate for Specific Workloads
- Use Fargate only for critical development tasks
- Pay only for running pods
- Mix with spot instances for cost optimization

## 🏆 Optimized Configuration for < $50/month

**With spot instances + single node + storage optimization:**

| Component | Monthly Cost |
|-----------|--------------|
| EKS Cluster | $74.40 |
| t4g.small spot (1 node) | ~$4.00 |
| EBS gp3 (10GB) | $2.00 |
| **Total** | **~$80** |

**With scheduled shutdown (12h/day, 5 days/week):**
- Total runtime: ~180 hours/month
- Node cost: ~$1.50/month  
- **Final total: ~$78/month**

## 🔧 Implementation Steps

### Quick Win: Enable Spot Instances
```bash
# Edit eks.tf and add to the node group:
capacity_type = "SPOT"

# Then apply changes:
terraform plan
terraform apply
```

### Advanced: Scheduled Shutdown
1. Install AWS Instance Scheduler
2. Create schedule: "Mon-Fri 8AM-6PM"
3. Tag node group with schedule

### Monitor Costs
```bash
# Set up billing alerts in AWS Console
# Use AWS Cost Explorer for tracking
# Monitor via: aws ce get-cost-and-usage
```

## ⚠️ Trade-offs

| Optimization | Savings | Trade-off |
|--------------|---------|-----------|
| Spot instances | 70% | Possible interruptions |
| Single node | $14/month | No redundancy |
| Scheduled shutdown | 65% | Limited availability |
| Smaller storage | $4/month | Less workspace |

## 🎯 Recommended Setup for Development

**Target: $50-60/month**
- ✅ Use spot instances
- ✅ Single node during development
- ✅ 10GB storage per node
- ✅ Schedule shutdown for nights/weekends
- ✅ Scale up to 2 nodes only when needed

**Commands to implement:**
```bash
# 1. Update terraform.tfvars:
echo 'node_desired_size = 1
node_min_size = 1  
node_disk_size = 10' >> terraform.tfvars

# 2. Edit eks.tf to add spot instances
# 3. Apply changes:
terraform apply
```

## 📊 Cost Monitoring

Set up alerts when spending exceeds:
- **$50/month**: Warning
- **$75/month**: Critical
- **$100/month**: Emergency shutdown

Use AWS Budgets and Cost Anomaly Detection for automated monitoring.