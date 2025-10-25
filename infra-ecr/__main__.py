"""
ECR Container Registry with Pull-Through Cache
Best practice: Low-cost registry with Docker Hub rate limit bypass
"""

import pulumi
import pulumi_aws as aws
import json

config = pulumi.Config()
cluster_name = config.get("cluster_name") or "builder-space"
aws_region = config.get("aws:region") or "af-south-1"

# Optional Docker Hub credentials for authenticated pulls (higher rate limits)
dockerhub_username = config.get("dockerhub_username")
dockerhub_password = config.get_secret("dockerhub_password")

current = aws.get_caller_identity()
account_id = current.account_id

# Tags
tags = {
    "Project": "builder-space-eks",
    "Environment": "production",
    "ManagedBy": "pulumi",
    "Purpose": "container-registry"
}

# =============================================================================
# 1. ECR PULL-THROUGH CACHE (Most Cost-Effective)
# =============================================================================
# This allows ECR to automatically cache images from Docker Hub, Quay.io, etc.
# Images are pulled once and cached, avoiding rate limits and reducing data transfer costs

# Docker Hub Pull-Through Cache Secret (optional, for higher rate limits)
dockerhub_secret = None
if dockerhub_username and dockerhub_password:
    dockerhub_secret = aws.secretsmanager.Secret("dockerhub-credentials",
        name=f"ecr-pullthroughcache/{cluster_name}-dockerhub",
        description="Docker Hub credentials for ECR pull-through cache",
        tags=tags
    )
    
    aws.secretsmanager.SecretVersion("dockerhub-credentials-version",
        secret_id=dockerhub_secret.id,
        secret_string=pulumi.Output.all(dockerhub_username, dockerhub_password).apply(
            lambda args: json.dumps({
                "username": args[0],
                "password": args[1]
            })
        )
    )

# Docker Hub Pull-Through Cache Rule
dockerhub_cache = aws.ecr.PullThroughCacheRule("dockerhub-cache",
    ecr_repository_prefix="docker-hub",
    upstream_registry_url="registry-1.docker.io",
    credential_arn=dockerhub_secret.arn,
    opts=pulumi.ResourceOptions(depends_on=[dockerhub_secret])
)

# Quay.io Pull-Through Cache Rule
# Requires credentials for private images - uncomment when ready
# quay_cache = aws.ecr.PullThroughCacheRule("quay-cache",
#     ecr_repository_prefix="quay",
#     upstream_registry_url="quay.io"
# )

# GitHub Container Registry Pull-Through Cache Rule
# Requires credentials - uncomment when ready
# ghcr_cache = aws.ecr.PullThroughCacheRule("ghcr-cache",
#     ecr_repository_prefix="github",
#     upstream_registry_url="ghcr.io"
# )

# Kubernetes Registry Pull-Through Cache Rule
# Public, no auth needed
k8s_cache = aws.ecr.PullThroughCacheRule("k8s-cache",
    ecr_repository_prefix="k8s",
    upstream_registry_url="registry.k8s.io"
)

# =============================================================================
# 2. PRIVATE ECR REPOSITORIES (For custom images)
# =============================================================================
# Create dedicated repositories for your own custom images

# KMS key for ECR encryption ($1/month)
ecr_kms_key = aws.kms.Key("ecr-kms-key",
    description=f"KMS key for {cluster_name} ECR encryption",
    deletion_window_in_days=7,
    tags=tags
)

aws.kms.Alias("ecr-kms-alias",
    name=f"alias/{cluster_name}-ecr",
    target_key_id=ecr_kms_key.key_id
)

# Example: Repository for custom applications
custom_apps_repo = aws.ecr.Repository("custom-apps",
    name=f"{cluster_name}/custom-apps",
    image_tag_mutability="MUTABLE",
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
        scan_on_push=True
    ),
    encryption_configurations=[aws.ecr.RepositoryEncryptionConfigurationArgs(
        encryption_type="KMS",
        kms_key=ecr_kms_key.arn
    )],
    tags=tags
)

# Lifecycle policy to clean up old images (cost optimization)
aws.ecr.LifecyclePolicy("custom-apps-lifecycle",
    repository=custom_apps_repo.name,
    policy=json.dumps({
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    })
)

# =============================================================================
# 3. IAM PERMISSIONS FOR EKS NODES
# =============================================================================
# EKS nodes already have AmazonEC2ContainerRegistryReadOnly policy attached
# (see cluster.py line 88-90). This allows pulling from ECR.

# Optional: Create a role for CI/CD to push images
ecr_push_policy = aws.iam.Policy("ecr-push-policy",
    name=f"{cluster_name}-ecr-push-policy",
    description="Allows pushing images to ECR repositories",
    policy=custom_apps_repo.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:PutImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload"
                ],
                "Resource": arn
            }
        ]
    })),
    tags=tags
)

# =============================================================================
# 4. REPLICATION (Optional, for disaster recovery)
# =============================================================================
# Uncomment if you want cross-region replication for high availability
# This adds cost: $0.02/GB replicated + storage in destination region

replication_config = aws.ecr.ReplicationConfiguration("ecr-replication",
    replication_configuration=aws.ecr.ReplicationConfigurationReplicationConfigurationArgs(
        rules=[
            aws.ecr.ReplicationConfigurationReplicationConfigurationRuleArgs(
                destinations=[
                    aws.ecr.ReplicationConfigurationReplicationConfigurationRuleDestinationArgs(
                        region="eu-west-1",
                        registry_id=account_id
                    )
                ]
            )
        ]
    )
)

# =============================================================================
# OUTPUTS
# =============================================================================

pulumi.export("ecr_registry_url", f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com")
pulumi.export("ecr_registry_id", account_id)

pulumi.export("pull_through_cache_rules", {
    "k8s": f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com/k8s",
    "active": "Only K8s registry enabled (no auth required)",
    "disabled": "Docker Hub, Quay, and GHCR require authentication",
    "note": "Uncomment rules in __main__.py after adding credentials via Secrets Manager"
})

pulumi.export("custom_repositories", {
    "custom_apps": custom_apps_repo.repository_url,
})

pulumi.export("cost_estimate", {
    "storage": "$0.10/GB/month (first 500MB free)",
    "data_transfer": "$0.09/GB out to internet",
    "pull_through_cache": "Only stores what you pull, saves bandwidth",
    "expected_monthly_cost": "$1-5/month for typical usage",
    "free_tier": "500MB storage free forever"
})

pulumi.export("docker_login_command", 
    f"aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{aws_region}.amazonaws.com"
)

pulumi.export("usage_examples", {
    "pull_k8s_image": f"docker pull {account_id}.dkr.ecr.{aws_region}.amazonaws.com/k8s/coredns/coredns:latest",
    "push_custom_image": f"docker push {account_id}.dkr.ecr.{aws_region}.amazonaws.com/{cluster_name}/custom-apps:v1.0.0",
    "note": "For Docker Hub images, you'll need to add credentials and enable the pull-through cache rule"
})

pulumi.export("kubernetes_image_pull_secret", {
    "not_needed": "EKS nodes already have ECR read permissions via AmazonEC2ContainerRegistryReadOnly policy",
    "verify": "Check cluster.py line 88-90"
})

pulumi.export("next_steps", [
    "1. Deploy this stack: cd infra-ecr && pulumi up",
    "2. K8s registry pull-through cache is ready (no auth needed)",
    "3. For Docker Hub: Add credentials and uncomment pull-through cache rule in __main__.py",
    "4. Or: Use private ECR repositories for frequently used Docker Hub images",
    "5. Monitor usage: aws ecr describe-repositories --region " + aws_region,
    "6. Check costs: AWS Console → Cost Explorer → ECR"
])

pulumi.export("encryption", {
    "type": "KMS",
    "cost": "$1/month for KMS key",
    "note": "Better security than default AES256 encryption"
})

pulumi.export("iam_policy_arn_for_cicd", ecr_push_policy.arn)
