# IAM Roles Management Guide

This guide explains how IAM roles are managed across Pulumi and ArgoCD, and why they should remain in Pulumi.

## Overview

IAM roles for Kubernetes ServiceAccounts use the IAM Roles for Service Accounts (IRSA) feature in EKS. This allows pods to assume AWS IAM roles without needing AWS credentials.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Account                              │
│                                                              │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  IAM Roles       │         │  EKS Cluster            │  │
│  │  (Pulumi)        │◄────────│  OIDC Provider          │  │
│  │                  │         │  (Pulumi)               │  │
│  │  - external-dns  │         └─────────────────────────┘  │
│  │  - autoscaler    │                    ▲                  │
│  └──────────────────┘                    │                  │
│         │                                │                  │
│         │ Trust Policy                   │                  │
│         │ (OIDC)                         │                  │
│         ▼                                │                  │
│  ┌──────────────────────────────────────┴─────────────────┐│
│  │              Kubernetes Pods                            ││
│  │              (ArgoCD-managed)                           ││
│  │                                                         ││
│  │  ServiceAccount → Assumes IAM Role → Access AWS        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Why IAM Roles Stay in Pulumi

### 1. **Separation of Concerns**

- **Pulumi**: Manages AWS resources (IAM, VPC, EKS, etc.)
- **ArgoCD**: Manages Kubernetes resources (Deployments, Services, etc.)

IAM roles are AWS resources, so they belong in Pulumi.

### 2. **OIDC Provider Dependency**

IAM roles for IRSA require:
- EKS cluster OIDC provider endpoint
- Trust policies referencing the OIDC provider

Both are managed by Pulumi, so IAM roles should be too.

### 3. **Cross-Namespace Usage**

IAM roles can be used by ServiceAccounts in different namespaces. Managing them in Pulumi provides a central source of truth.

### 4. **Terraform/Pulumi State**

IAM roles are part of the infrastructure state. Keeping them in Pulumi maintains a complete infrastructure picture.

### 5. **Security Auditing**

IAM policies are security-critical. Keeping them in Pulumi alongside other AWS security resources simplifies auditing.

## Current IAM Roles

### 1. External-DNS Role

**Purpose**: Allows External-DNS pods to manage Route53 DNS records

**Permissions:**
```json
{
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
}
```

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/OIDC_ENDPOINT"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "OIDC_ENDPOINT:sub": "system:serviceaccount:external-dns:external-dns",
        "OIDC_ENDPOINT:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

**Pulumi Code Location:** `builder-space/infra-k8s/__main__.py` (lines 78-113)

### 2. Cluster-Autoscaler Role

**Purpose**: Allows Cluster-Autoscaler pods to manage Auto Scaling groups

**Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeAutoScalingInstances",
      "autoscaling:DescribeLaunchConfigurations",
      "autoscaling:DescribeTags",
      "ec2:DescribeLaunchTemplateVersions",
      "autoscaling:SetDesiredCapacity",
      "autoscaling:TerminateInstanceInAutoScalingGroup"
    ],
    "Resource": "*"
  }]
}
```

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/OIDC_ENDPOINT"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "OIDC_ENDPOINT:sub": "system:serviceaccount:kube-system:cluster-autoscaler",
        "OIDC_ENDPOINT:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

**Pulumi Code Location:** `builder-space/infra-k8s/__main__.py` (lines 116-155)

## How It Works Together

### 1. Pulumi Creates IAM Role

```python
# In builder-space/infra-k8s/__main__.py
external_dns_role = aws.iam.Role("external-dns-role",
    assume_role_policy=pulumi.Output.from_input(oidc_issuer).apply(
        lambda issuer: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{current.account_id}:oidc-provider/{issuer.replace('https://', '')}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{issuer.replace('https://', '')}:sub": "system:serviceaccount:external-dns:external-dns",
                        f"{issuer.replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

pulumi.export("external_dns_role_arn", external_dns_role.arn)
```

### 2. Get Role ARN from Pulumi

```bash
cd builder-space/infra-k8s
pulumi stack output external_dns_role_arn
# Output: arn:aws:iam::123456789012:role/external-dns-role-abc123
```

### 3. Reference in ArgoCD Manifests

```yaml
# In builder-space-argocd/environments/prod/infrastructure/external-dns/values.yaml
serviceAccount:
  create: true
  name: external-dns
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/external-dns-role-abc123
```

### 4. Pod Assumes Role

When the pod starts:
1. Kubernetes creates the ServiceAccount with the annotation
2. The pod's service account token is projected into the pod
3. AWS SDK in the pod detects the annotation and exchanges the token for AWS credentials
4. Pod can now make AWS API calls with the IAM role's permissions

## Exporting IAM Role ARNs

To make it easier to reference IAM roles in ArgoCD manifests, export them from Pulumi:

### Add to infra-k8s/__main__.py

```python
# Add these exports at the end of the file
pulumi.export("iam_roles", {
    "external_dns_role_arn": external_dns_role.arn,
    "cluster_autoscaler_role_arn": cluster_autoscaler_role.arn,
})
```

### Get Exported Values

```bash
cd builder-space/infra-k8s
pulumi stack output iam_roles
```

Output:
```json
{
  "external_dns_role_arn": "arn:aws:iam::123456789012:role/external-dns-role-abc123",
  "cluster_autoscaler_role_arn": "arn:aws:iam::123456789012:role/cluster-autoscaler-role-def456"
}
```

## Best Practices

### 1. Principle of Least Privilege

Grant only the minimum permissions required:

```python
# Good: Specific actions
"Action": [
    "route53:ChangeResourceRecordSets",
    "route53:ListHostedZones"
]

# Bad: Overly broad
"Action": "route53:*"
```

### 2. Resource Constraints

Limit to specific resources when possible:

```python
# Good: Specific hosted zone
"Resource": "arn:aws:route53:::hostedzone/Z1234567890ABC"

# Acceptable: All Route53 resources (some actions don't support resource constraints)
"Resource": "*"
```

### 3. Condition Keys

Use condition keys for additional security:

```python
"Condition": {
    "StringEquals": {
        "oidc:sub": "system:serviceaccount:namespace:serviceaccount-name",
        "oidc:aud": "sts.amazonaws.com"
    }
}
```

### 4. Separate Roles per Service

Create separate IAM roles for each service rather than sharing:

```python
# Good: Separate roles
external_dns_role = aws.iam.Role("external-dns-role", ...)
cluster_autoscaler_role = aws.iam.Role("cluster-autoscaler-role", ...)

# Bad: Shared role
infrastructure_role = aws.iam.Role("infrastructure-role", ...)  # Used by everything
```

### 5. Document Role Purpose

Add tags and descriptions to IAM roles:

```python
external_dns_role = aws.iam.Role("external-dns-role",
    description="Role for External-DNS to manage Route53 records",
    tags={
        "Service": "External-DNS",
        "ManagedBy": "Pulumi",
        "Purpose": "Route53 DNS Management"
    },
    ...
)
```

## Troubleshooting

### Issue: Pod Cannot Assume Role

**Symptoms:**
```
An error occurred (AccessDenied) when calling the AssumeRoleWithWebIdentity operation
```

**Check:**

1. **ServiceAccount annotation:**
   ```bash
   kubectl get serviceaccount external-dns -n external-dns -o yaml
   ```
   Should show:
   ```yaml
   metadata:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/external-dns-role-abc123
   ```

2. **IAM role trust policy:**
   ```bash
   aws iam get-role --role-name external-dns-role-abc123 --query 'Role.AssumeRolePolicyDocument'
   ```

3. **OIDC provider:**
   ```bash
   aws iam list-open-id-connect-providers
   ```

4. **Pod logs:**
   ```bash
   kubectl logs -n external-dns deployment/external-dns --tail=50
   ```

### Issue: Wrong IAM Role ARN

**Symptoms:**
```
The security token included in the request is invalid
```

**Solution:**

1. Get correct ARN from Pulumi:
   ```bash
   cd builder-space/infra-k8s
   pulumi stack output external_dns_role_arn
   ```

2. Update ArgoCD manifest with correct ARN

3. Sync ArgoCD application:
   ```bash
   argocd app sync infrastructure-bootstrap
   ```

### Issue: Insufficient Permissions

**Symptoms:**
```
AccessDenied: User is not authorized to perform: route53:ChangeResourceRecordSets
```

**Solution:**

Update IAM policy in Pulumi:

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
                "route53:ListResourceRecordSets",
                "route53:GetChange"  # Add missing permission
            ],
            "Resource": "*"
        }]
    })
)
```

Then run:
```bash
pulumi up
```

## Adding New IAM Roles

When adding new services that need AWS access:

### 1. Create IAM Role in Pulumi

```python
# In builder-space/infra-k8s/__main__.py

# New IAM Role for MyService
myservice_role = aws.iam.Role("myservice-role",
    assume_role_policy=pulumi.Output.from_input(oidc_issuer).apply(
        lambda issuer: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{current.account_id}:oidc-provider/{issuer.replace('https://', '')}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{issuer.replace('https://', '')}:sub": "system:serviceaccount:myservice:myservice",
                        f"{issuer.replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

aws.iam.RolePolicy("myservice-policy",
    role=myservice_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::my-bucket/*"
        }]
    })
)

pulumi.export("myservice_role_arn", myservice_role.arn)
```

### 2. Deploy with Pulumi

```bash
cd builder-space/infra-k8s
pulumi up
```

### 3. Get Role ARN

```bash
pulumi stack output myservice_role_arn
```

### 4. Use in ArgoCD Manifest

```yaml
# In builder-space-argocd
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myservice
  namespace: myservice
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/myservice-role-xyz789
```

## References

- [EKS IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [IAM Roles Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Pulumi AWS IAM](https://www.pulumi.com/docs/clouds/aws/guides/iam/)
