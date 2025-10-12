# ECR Pull-Through Cache - Quick Start

## TL;DR - Why ECR?

Your deployments pull images from public registries:
- ❌ Docker Hub: 100-200 pulls/6hrs rate limit
- ❌ Slow pulls from public registries in South Africa
- ❌ No cost control or visibility
- ❌ External dependencies for production

**Solution**: AWS ECR Pull-Through Cache
- ✅ **$1-3/month** vs Docker Hub Pro $5/month
- ✅ Unlimited pulls from cached images
- ✅ Fast local cache in af-south-1 region
- ✅ No configuration needed (EKS nodes already have access)
- ✅ Automatic - first pull caches, subsequent pulls instant

---

## 5-Minute Setup

```bash
cd /home/alex/work/src/Amano/src/builder-space/infra-ecr

# Run automated setup
./setup-ecr.sh
```

That's it! The script will:
1. ✅ Install dependencies
2. ✅ Create Pulumi stack
3. ✅ Deploy ECR with pull-through cache rules
4. ✅ Show you your registry URL

---

## How It Works

### Before (Public Registries)
```yaml
# Your current WordPress values.yaml
image:
  registry: docker.io
  repository: bitnami/wordpress
  tag: latest
```

Every pod pull hits Docker Hub → Rate limits → Slow pulls

### After (ECR Pull-Through Cache)
```yaml
# Updated WordPress values.yaml
image:
  registry: 123456789012.dkr.ecr.af-south-1.amazonaws.com
  repository: docker-hub/bitnami/wordpress
  tag: latest
```

**First pull**: ECR pulls from Docker Hub → Caches locally  
**All subsequent pulls**: Instant from ECR cache → No rate limits → Fast

---

## Update Your Applications

### Get Your Registry URL

```bash
cd /home/alex/work/src/Amano/src/builder-space/infra-ecr
pulumi stack output ecr_registry_url

# Output: 123456789012.dkr.ecr.af-south-1.amazonaws.com
```

### Convert Image URLs

Use the helper script:

```bash
./convert-image-url.sh

# Or for a specific image:
./convert-image-url.sh bitnami/wordpress:latest
```

### Update Helm Values

#### WordPress (`builder-space-argocd/environments/prod/spruch/values.yaml`)

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
  registry: 123456789012.dkr.ecr.af-south-1.amazonaws.com
  repository: docker-hub/bitnami/wordpress
  tag: latest
```

#### Rocket.Chat (`builder-space-argocd/environments/prod/rocketchat/values.yaml`)

**Before**:
```yaml
image:
  repository: registry.rocket.chat/rocketchat/rocket.chat
  tag: latest

mongodb:
  image:
    registry: docker.io
    repository: bitnami/mongodb
```

**After**:
```yaml
image:
  repository: 123456789012.dkr.ecr.af-south-1.amazonaws.com/docker-hub/rocketchat/rocket.chat
  tag: latest

mongodb:
  image:
    registry: 123456789012.dkr.ecr.af-south-1.amazonaws.com
    repository: docker-hub/bitnami/mongodb
```

#### ERPNext (`builder-space-argocd/environments/prod/erpnext/values.yaml`)

**Before**:
```yaml
image:
  registry: docker.io
  repository: frappe/erpnext
  tag: latest
```

**After**:
```yaml
image:
  registry: 123456789012.dkr.ecr.af-south-1.amazonaws.com
  repository: docker-hub/frappe/erpnext
  tag: latest
```

---

## Test Before Deploying

```bash
# Login to ECR
REGISTRY=$(cd /home/alex/work/src/Amano/src/builder-space/infra-ecr && pulumi stack output ecr_registry_url)
aws ecr get-login-password --region af-south-1 | \
  docker login --username AWS --password-stdin $REGISTRY

# Test pull (creates cache automatically)
docker pull $REGISTRY/docker-hub/bitnami/wordpress:latest

# Pull again (should be instant from cache)
time docker pull $REGISTRY/docker-hub/bitnami/wordpress:latest
```

---

## Deploy to Kubernetes

After updating your Helm values:

```bash
cd /home/alex/work/src/Amano/src/builder-space-argocd

# Commit changes
git add environments/prod/*/values.yaml
git commit -m "Switch to ECR pull-through cache for all images"
git push

# ArgoCD will automatically sync and pull from ECR
kubectl get pods -n spruch -w
kubectl get pods -n rocketchat -w
kubectl get pods -n erpnext -w
```

**No image pull secrets needed** - EKS nodes already have ECR read permissions!

---

## Monitoring & Cost

### Check What's Cached

```bash
# List all ECR repositories (created automatically on first pull)
aws ecr describe-repositories --region af-south-1 \
  --query 'repositories[*].[repositoryName]' --output table

# Check storage size
aws ecr describe-repositories --region af-south-1 \
  --query 'repositories[*].[repositoryName]' --output text | \
  while read repo; do
    echo "Repository: $repo"
    aws ecr describe-images --repository-name "$repo" --region af-south-1 \
      --query 'imageDetails[*].[imageSizeInBytes]' --output text | \
      awk '{sum+=$1} END {print "  Size: " sum/1024/1024 " MB"}'
  done
```

### Cost Estimate

| Usage Pattern | Storage | Monthly Cost |
|---------------|---------|--------------|
| Light (WordPress + 2-3 apps) | ~2GB | ~$0.15 |
| Medium (5-10 apps) | ~5GB | ~$0.45 |
| Heavy (All apps + frequent pulls) | ~10GB | ~$0.95 |

**First 500MB free**, then $0.10/GB/month

---

## Lifecycle Management

Images are kept forever by default. To save costs:

```bash
# Create lifecycle policy (keep last 5 images)
cat > /tmp/lifecycle-policy.json <<EOF
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep last 5 images",
    "selection": {
      "tagStatus": "any",
      "countType": "imageCountMoreThan",
      "countNumber": 5
    },
    "action": {"type": "expire"}
  }]
}
EOF

# Apply to all docker-hub repositories
aws ecr describe-repositories --region af-south-1 \
  --query 'repositories[?starts_with(repositoryName, `docker-hub`)].repositoryName' \
  --output text | \
  xargs -I {} aws ecr put-lifecycle-policy \
    --repository-name {} \
    --lifecycle-policy-text file:///tmp/lifecycle-policy.json \
    --region af-south-1
```

---

## Troubleshooting

### "Repository does not exist"

Normal! Pull-through cache creates repositories automatically on first pull:

```bash
docker pull 123456789012.dkr.ecr.af-south-1.amazonaws.com/docker-hub/library/nginx:latest
```

### "Unauthorized: authentication required"

Login to ECR:

```bash
aws ecr get-login-password --region af-south-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.af-south-1.amazonaws.com
```

### Pods can't pull from ECR

Check node IAM role has `AmazonEC2ContainerRegistryReadOnly` policy:

```bash
# Get node role name
kubectl get nodes -o json | jq -r '.items[0].spec.providerID' | cut -d'/' -f2 | \
  xargs aws ec2 describe-instances --instance-ids --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn'

# Check attached policies (should include ECR read)
aws iam list-attached-role-policies --role-name <node-role-name>
```

---

## FAQ

**Q: Do I need image pull secrets?**  
A: No! EKS nodes already have ECR read permissions via IAM role.

**Q: What if I want to use Docker Hub directly sometimes?**  
A: You can! Pull-through cache is optional per image. Mix and match as needed.

**Q: Does this work with private registries?**  
A: No, only public registries (Docker Hub, Quay, GHCR, K8s registry). For private images, use ECR private repositories.

**Q: Can I push images to pull-through cache?**  
A: No, it's read-only. Use ECR private repositories for custom images (see `custom-apps` repo in stack).

**Q: How do I delete cached images?**  
A: Delete the repository or individual images via AWS CLI or Console.

**Q: What about Docker Hub rate limits?**  
A: After first pull, all subsequent pulls use ECR cache → no rate limits!

---

## Next Steps

1. ✅ Deploy ECR: `cd infra-ecr && ./setup-ecr.sh`
2. ✅ Get registry URL: `pulumi stack output ecr_registry_url`
3. ✅ Update Helm values for all applications
4. ✅ Test with one app first (e.g., WordPress)
5. ✅ Roll out to all applications
6. ✅ Monitor costs after 24 hours

---

## Best Practice Architecture

This is the **recommended** approach for production EKS clusters:

```
infra-ecr/          # Shared container registry (this stack)
  └── ECR with pull-through cache
      ├── docker-hub/*
      ├── quay/*
      ├── github/*
      └── k8s/*

cluster.py          # Day-0: EKS cluster (nodes have ECR read access)
infra-k8s/          # Day-1: ArgoCD, cert-manager, etc.
builder-space-argocd/  # Day-2: Applications using ECR images
```

Separate stack = easier to manage, share across multiple clusters, and update independently.

---

## Support

- 📖 Full documentation: `README.md`
- 🔧 Setup script: `./setup-ecr.sh`
- 🔄 Image converter: `./convert-image-url.sh`
- 📊 Outputs: `pulumi stack output`
