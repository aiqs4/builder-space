# Builder Space - Production EKS Cluster

**KISS Architecture** - Minimal configuration, production-ready, organized by concern.

## 🏗️ Architecture

### Structure
```
src/
├── network.py       # VPC, subnets (/22), routing
├── cluster.py       # EKS cluster + minimal IAM
├── addons.py        # EKS managed add-ons (auto-configured)
├── database.py      # Aurora PostgreSQL Serverless v2
├── external_dns.py  # Automatic DNS for services
└── karpenter.py     # Efficient autoscaling
```

### What's Included

#### ✅ Auto-Configured (No Manual IRSA)
- **Amazon VPC CNI** - Pod networking
- **CoreDNS** - Cluster DNS
- **Amazon EKS Pod Identity Agent** - Modern IRSA replacement
- **Amazon EBS CSI Driver** - Persistent volumes

#### 🛠️ Configured
- **External DNS** - Automatic Route53 management for 4 domains
- **Karpenter** - Smart autoscaling (spot + on-demand)

### Network Design
- VPC: `10.0.0.0/16`
- Public Subnets: `/22` each (1,022 usable IPs)
  - `10.0.0.0/22` - af-south-1a
  - `10.0.4.0/22` - af-south-1b

### Database
Aurora PostgreSQL Serverless v2
- **Scales to zero** (0.5 - 2.0 ACUs)
- IAM authentication enabled
- Encrypted at rest
- 7-day backup retention

## 🚀 Usage

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set database password
pulumi config set --secret db_password "your-secure-password"
```

### Deploy
```bash
pulumi up --stack eks
```

### Connect to Cluster
```bash
aws eks update-kubeconfig --region af-south-1 --name builder-space
kubectl get nodes
```

### Verify Add-ons
```bash
# Check managed add-ons
aws eks list-addons --cluster-name builder-space

# Check External DNS
kubectl -n kube-system logs -l app=external-dns

# Check Karpenter
kubectl -n kube-system logs -l app.kubernetes.io/name=karpenter
```

## 📋 Configuration

Edit `Pulumi.eks.yaml`:
```yaml
config:
  aws:region: af-south-1
  builder-space-eks:cluster_name: builder-space
  builder-space-eks:node_count: "3"              # Initial node count
  builder-space-eks:instance_type: t3.xlarge     # Node instance type
  builder-space-eks:github_actions_role_arn: arn:aws:iam::207567777877:role/github-deploy-eks
  builder-space-eks:db_password:
    secure: <set-via-cli>
```

## 🎯 Key Features

### KISS Principles Applied
1. **No manual OIDC/IRSA for add-ons** - AWS manages them automatically
2. **Bigger subnets** - /22 provides 1,022 IPs each
3. **Removed redundant configs** - Only production essentials
4. **Organized by concern** - Each file has a single responsibility
5. **Latest stable versions** - EKS 1.31, latest add-on versions

### Autoscaling Strategy
- **Initial nodes**: ON_DEMAND (stable baseline)
- **Karpenter nodes**: SPOT + ON_DEMAND mix
- **Consolidation**: Automatic when underutilized
- **Instance types**: t, c, m families (arm64 + amd64)

### DNS Automation
External DNS automatically creates/updates records for:
- `amano.services`
- `tekanya.services`
- `lightsphere.space`
- `sosolola.cloud`

Just annotate your services:
```yaml
annotations:
  external-dns.alpha.kubernetes.io/hostname: myapp.amano.services
```

## 🔒 Security

- ✅ Pod Identity (modern IRSA)
- ✅ IAM authentication for Aurora
- ✅ Encryption at rest for database
- ✅ VPC isolation
- ✅ Control plane logging enabled
- ✅ SSM Session Manager access to nodes

## 📊 Monitoring

```bash
# Cluster status
aws eks describe-cluster --name builder-space

# Node status
kubectl get nodes -o wide

# Add-on status
aws eks describe-addon --cluster-name builder-space --addon-name vpc-cni
aws eks describe-addon --cluster-name builder-space --addon-name coredns
aws eks describe-addon --cluster-name builder-space --addon-name eks-pod-identity-agent
aws eks describe-addon --cluster-name builder-space --addon-name aws-ebs-csi-driver

# Database status
aws rds describe-db-clusters --db-cluster-identifier builder-space-postgres
```

## 🧹 Cleanup

```bash
# Delete everything
pulumi destroy --stack eks

# Or use the cleanup script
./cleanup.sh
```

## 📝 Notes

- **Spot instances**: Karpenter will use spot when available, falling back to on-demand
- **Database scaling**: Serverless v2 scales automatically based on load
- **Cost optimization**: Karpenter consolidates underutilized nodes
- **No EFS**: Use EBS CSI driver for persistent volumes (faster, cheaper for small volumes)

## 🔗 Resources

- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Karpenter Docs](https://karpenter.sh/)
- [External DNS Docs](https://github.com/kubernetes-sigs/external-dns)
