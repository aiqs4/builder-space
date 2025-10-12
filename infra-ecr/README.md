# ECR Container Registry - Cost-Effective Pull-Through Cache

## Overview

This Pulumi stack sets up AWS ECR (Elastic Container Registry) with **pull-through cache** functionality, providing:

✅ **Cost-Effective**: Cache public images locally, pay only for what you use  
✅ **Rate Limit Bypass**: Avoid Docker Hub rate limits (200 pulls/6hrs unauthenticated)  
✅ **Fast Pulls**: Images cached in your region = faster deployments  
✅ **No Configuration Needed**: EKS nodes already have ECR read permissions  
✅ **Free Tier**: 500MB storage free forever, then $0.10/GB/month  

---

## 💰 Cost Analysis

### AWS ECR Pricing (af-south-1)
| Item | Cost | Notes |
|------|------|-------|
| Storage | **$0.10/GB/month** | First 500MB free |
| Data transfer OUT | **$0.09/GB** | To internet |
| Data transfer IN | **FREE** | From internet |
| API calls | **FREE** | All ECR API calls |

### Expected Monthly Cost
- **Light usage** (2-3 apps, ~2GB storage): **$0.20-0.50/month**
- **Medium usage** (5-10 apps, ~5GB storage): **$0.50-1.50/month**
- **Heavy usage** (20+ apps, ~10GB storage): **$1-3/month**

### Comparison: Docker Hub Rate Limits
| Plan | Pulls/6hrs | Cost |
|------|------------|------|
| Anonymous | 100 | Free (but limited) |
| Free Account | 200 | Free (but limited) |
| Pro | Unlimited | **$5/month** |
| ECR Pull-Through | Unlimited | **~$1/month** |

**Verdict**: ECR is cheaper and more reliable for production workloads.

---

## 🏗️ Architecture

### Pull-Through Cache Rules
This stack creates pull-through cache rules for major public registries:

```
┌─────────────────────────────────────────────────────────────┐
│ Public Registries                                           │
│  • registry-1.docker.io (Docker Hub)                        │
│  • quay.io (Red Hat Quay)                                   │
│  • ghcr.io (GitHub Container Registry)                      │
│  • registry.k8s.io (Kubernetes)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │ First pull
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS ECR (Your Account)                                      │
│  • <account-id>.dkr.ecr.af-south-1.amazonaws.com/docker-hub │
│  • <account-id>.dkr.ecr.af-south-1.amazonaws.com/quay       │
│  • <account-id>.dkr.ecr.af-south-1.amazonaws.com/github     │
│  • <account-id>.dkr.ecr.af-south-1.amazonaws.com/k8s        │
│                                                              │
│  Subsequent pulls = INSTANT (cached locally)                │
└──────────────────────┬──────────────────────────────────────┘
                       │ No authentication needed
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ EKS Nodes (t4g.medium)                                      │
│  • Have AmazonEC2ContainerRegistryReadOnly policy           │
│  • Can pull from ECR without image pull secrets             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment

### Prerequisites
1. AWS account with ECR permissions
2. Pulumi CLI installed
3. AWS credentials configured

### Deploy

```bash
cd /home/alex/work/src/Amano/src/builder-space/infra-ecr

# Install dependencies
pip install -r requirements.txt

# Set Pulumi passphrase
export PULUMI_CONFIG_PASSPHRASE="your-passphrase"

# Create/select stack
pulumi stack select ecr --create

# Preview changes
pulumi preview

# Deploy
pulumi up
```

### With Docker Hub Authentication (Optional)

To get higher rate limits from Docker Hub, add your credentials:

```bash
# Set Docker Hub credentials (for authenticated pulls - 200 pulls/6hrs instead of 100)
pulumi config set dockerhub_username your-dockerhub-username
pulumi config set --secret dockerhub_password your-dockerhub-token

# Deploy
pulumi up
```

**Note**: Even without Docker Hub credentials, pull-through cache still works, just with anonymous rate limits.

---

## 📝 Usage

### How Pull-Through Cache Works

When you pull an image with the ECR prefix for the first time:
1. ECR pulls the image from the public registry (Docker Hub, etc.)
2. ECR caches the image in your account
3. Subsequent pulls use the cached image (instant, no external bandwidth)

### Image URL Conversion

| Original Image | ECR Pull-Through Cache URL |
|----------------|----------------------------|
| `nginx:latest` | `<account>.dkr.ecr.af-south-1.amazonaws.com/docker-hub/library/nginx:latest` |
| `bitnami/wordpress:latest` | `<account>.dkr.ecr.af-south-1.amazonaws.com/docker-hub/bitnami/wordpress:latest` |
| `rocketchat/rocket.chat:latest` | `<account>.dkr.ecr.af-south-1.amazonaws.com/docker-hub/rocketchat/rocket.chat:latest` |
| `quay.io/prometheus/prometheus:latest` | `<account>.dkr.ecr.af-south-1.amazonaws.com/quay/prometheus/prometheus:latest` |
| `ghcr.io/example/app:v1.0` | `<account>.dkr.ecr.af-south-1.amazonaws.com/github/example/app:v1.0` |

**Get your account ID**:
```bash
pulumi stack output ecr_registry_url
# Or: aws sts get-caller-identity --query Account --output text
```

### Update Helm Values

Example for WordPress:

**Before**:
```yaml
image:
  registry: docker.io
  repository: bitnami/wordpress
  tag: latest
```

**After**:
```yaml
image:
  registry: <account-id>.dkr.ecr.af-south-1.amazonaws.com
  repository: docker-hub/bitnami/wordpress
  tag: latest
```

Example for Rocket.Chat:

**Before**:
```yaml
image:
  repository: registry.rocket.chat/rocketchat/rocket.chat
  tag: latest
```

**After**:
```yaml
image:
  repository: <account-id>.dkr.ecr.af-south-1.amazonaws.com/docker-hub/rocketchat/rocket.chat
  tag: latest
```

---

## 🔐 Authentication

### For EKS Pods (No Action Needed)

EKS nodes already have the `AmazonEC2ContainerRegistryReadOnly` policy attached (see `cluster.py` line 88-90). No image pull secrets needed.

### For Local Docker

```bash
# Get Docker login command from Pulumi
pulumi stack output docker_login_command

# Or manually
aws ecr get-login-password --region af-south-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.af-south-1.amazonaws.com
```

### For CI/CD (GitHub Actions, etc.)

Use the IAM policy created by this stack:

```bash
# Get the policy ARN
pulumi stack output iam_policy_arn_for_cicd

# Attach to your CI/CD role
aws iam attach-role-policy \
  --role-name your-cicd-role \
  --policy-arn <policy-arn>
```

---

## 🧪 Testing

### Test Pull-Through Cache

```bash
# Login to ECR
aws ecr get-login-password --region af-south-1 | \
  docker login --username AWS --password-stdin \
  $(pulumi stack output ecr_registry_url)

# Pull an image (first pull caches it)
REGISTRY=$(pulumi stack output ecr_registry_url)
docker pull $REGISTRY/docker-hub/library/nginx:latest

# Check ECR repository (should be auto-created)
aws ecr describe-repositories --region af-south-1 | grep docker-hub/library/nginx

# Pull again (should be instant from cache)
docker pull $REGISTRY/docker-hub/library/nginx:latest
```

### Test with Kubernetes

```bash
# Create a test pod
kubectl run test-nginx \
  --image=$(pulumi stack output ecr_registry_url)/docker-hub/library/nginx:latest \
  --rm -it --restart=Never -- /bin/sh

# If successful, ECR pull-through cache is working!
```

---

## 📊 Monitoring

### Check ECR Repositories

```bash
# List all repositories
aws ecr describe-repositories --region af-south-1

# Get repository size
aws ecr describe-repositories --region af-south-1 \
  --query 'repositories[*].[repositoryName,imageScanningConfiguration.scanOnPush]' \
  --output table
```

### Check Image Details

```bash
# List images in a repository
aws ecr list-images \
  --repository-name docker-hub/bitnami/wordpress \
  --region af-south-1

# Get image details
aws ecr describe-images \
  --repository-name docker-hub/bitnami/wordpress \
  --region af-south-1
```

### Monitor Costs

```bash
# AWS Cost Explorer (requires AWS Console)
# Go to: AWS Console → Cost Management → Cost Explorer
# Filter by Service: EC2 Container Registry (ECR)
```

---

## 🧹 Cost Optimization

### Lifecycle Policies

This stack automatically applies lifecycle policies to custom repositories:
- Keep last 10 images
- Automatically delete older images

For pull-through cache repositories, you can add policies:

```bash
# Create lifecycle policy JSON
cat > lifecycle-policy.json <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 5 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 5
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF

# Apply to repository
aws ecr put-lifecycle-policy \
  --repository-name docker-hub/bitnami/wordpress \
  --lifecycle-policy-text file://lifecycle-policy.json \
  --region af-south-1
```

### Clean Up Unused Images

```bash
# List all ECR repositories
aws ecr describe-repositories --region af-south-1 \
  --query 'repositories[*].repositoryName' --output text

# Delete a repository (careful!)
aws ecr delete-repository \
  --repository-name docker-hub/old-image \
  --force \
  --region af-south-1
```

---

## 🔧 Troubleshooting

### Error: "repository does not exist"

**Solution**: Pull-through cache repositories are created automatically on first pull. Just pull the image once:

```bash
REGISTRY=$(pulumi stack output ecr_registry_url)
docker pull $REGISTRY/docker-hub/library/nginx:latest
```

### Error: "no basic auth credentials"

**Solution**: Login to ECR:

```bash
aws ecr get-login-password --region af-south-1 | \
  docker login --username AWS --password-stdin \
  $(pulumi stack output ecr_registry_url)
```

### Error: "pull access denied"

**Solution**: Check IAM permissions. EKS nodes need `AmazonEC2ContainerRegistryReadOnly` policy.

```bash
# Check node IAM role
aws iam list-attached-role-policies --role-name <node-role-name>

# Should include: AmazonEC2ContainerRegistryReadOnly
```

### Pull-Through Cache Not Working

**Check if rules are created**:
```bash
aws ecr describe-pull-through-cache-rules --region af-south-1
```

**Check if Docker Hub credentials are valid** (if using):
```bash
aws secretsmanager get-secret-value \
  --secret-id builder-space-dockerhub-credentials \
  --region af-south-1
```

---

## 📚 Resources

- [AWS ECR Pull-Through Cache](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html)
- [AWS ECR Pricing](https://aws.amazon.com/ecr/pricing/)
- [Docker Hub Rate Limits](https://docs.docker.com/docker-hub/download-rate-limit/)
- [ECR Lifecycle Policies](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html)

---

## 🎯 Next Steps

1. **Deploy the stack**: `cd infra-ecr && pulumi up`
2. **Get your registry URL**: `pulumi stack output ecr_registry_url`
3. **Update Helm values**: Replace Docker Hub images with ECR pull-through cache URLs
4. **Test a deployment**: Deploy WordPress or Rocket.Chat with new image URLs
5. **Monitor costs**: Check AWS Cost Explorer after 24 hours

---

## 💡 Best Practices

1. **Use pull-through cache for all public images** - Saves bandwidth and avoids rate limits
2. **Add lifecycle policies** - Automatically clean up old images
3. **Enable image scanning** - Detect vulnerabilities in cached images
4. **Monitor storage** - Set up CloudWatch alarms for ECR storage usage
5. **Use Docker Hub authentication** - Get 200 pulls/6hrs instead of 100 (optional)
6. **Tag images properly** - Use semantic versioning for custom images
7. **Separate repositories** - One repository per application for better organization

---

## 🆘 Support

For issues:
1. Check Pulumi outputs: `pulumi stack output`
2. Check ECR repositories: `aws ecr describe-repositories --region af-south-1`
3. Check pull-through cache rules: `aws ecr describe-pull-through-cache-rules --region af-south-1`
4. Test local Docker pull before updating Kubernetes manifests
