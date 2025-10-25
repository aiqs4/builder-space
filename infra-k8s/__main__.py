"""
Production EKS Infrastructure with ArgoCD, External-DNS, and Cluster Autoscaler
Minimal but complete setup with proper IAM roles and GitOps approach
"""

import json
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v4 import Chart, ChartArgs

config = pulumi.Config()
cluster_name = config.get("cluster_name") or "builder-space"
aws_region = config.get("aws:region") or "af-south-1"
acme_email = config.get("acme_email") or "info@lightsphere.space"

# TODO: enable below when DNS stack is ready
# Reference DNS stack providing the hosted zone & DNSSEC outputs
# Accept both formats:
#   1) Pulumi Cloud: <org>/<project>/<stack>
#   2) Self-managed backend (S3/local): <project>/<stack>
# You are using an S3 backend (see `pulumi whoami --verbose`), so omit the org (or migrate to Cloud to use one).
# dns_stack_input = config.require("dns_stack")
# parts = dns_stack_input.split("/")
# if len(parts) == 2:
#     # project/stack form (self-managed backend)
#     dns_stack_fq = dns_stack_input
# elif len(parts) == 3:
#     # org/project/stack form (Pulumi Cloud backend)
#     dns_stack_fq = dns_stack_input
# else:
#     raise Exception("dns_stack config value must be either 'project/stack' (self-managed) or 'org/project/stack' (Pulumi Cloud). Got: %s" % dns_stack_input)

# dns_stack = pulumi.StackReference(dns_stack_fq)

# subdomain_zone_id = dns_stack.get_output("subdomain_zone_id")
# subdomain_nameservers = dns_stack.get_output("subdomain_name_servers")
# dnssec_ds_record = dns_stack.get_output("dnssec_ds_record")
# domain_name_output = dns_stack.get_output("subdomain_zone_name")

# Allow override via config (optional); fallback to referenced zone name
# domain_name = config.get("domain_name") or domain_name_output
domain_name = config.get("domain_name")

# Get cluster info
cluster_info = aws.eks.get_cluster(name=cluster_name)


# Derive OIDC issuer robustly (EKS describeCluster returns identities[0].oidcs list)
oidc_issuer_override = config.get("cluster_oidc_issuer")

def _derive_oidc_issuer(ci: aws.eks.GetClusterResult):
    try:
        if ci.identities and len(ci.identities) > 0:
            ident = ci.identities[0]
            # Newer provider gives ident.oidcs (list). Fallback to ident.oidc if present.
            if hasattr(ident, 'oidcs') and ident.oidcs and len(ident.oidcs) > 0 and hasattr(ident.oidcs[0], 'issuer'):
                return ident.oidcs[0].issuer
            if hasattr(ident, 'oidc') and hasattr(ident.oidc, 'issuer'):
                return ident.oidc.issuer
    except Exception:
        return None
    return None

derived_oidc_issuer = _derive_oidc_issuer(cluster_info)
if oidc_issuer_override:
    oidc_issuer = oidc_issuer_override
elif derived_oidc_issuer:
    oidc_issuer = derived_oidc_issuer
else:
    raise Exception("Unable to determine OIDC issuer automatically. Provide config 'builder-space-k8s:cluster_oidc_issuer'.")
current = aws.get_caller_identity()
current_region = aws.get_region()

# ============================================================================
# OIDC Provider for IRSA (IAM Roles for Service Accounts)
# ============================================================================
# IMPORTANT: EKS creates an OIDC issuer URL, but does NOT register it in IAM
# We must create the IAM OIDC provider to enable IRSA for:
# - Cluster Autoscaler, K DNS, EBS CSI Driver, etc.
#
# Get the OIDC issuer thumbprint from AWS
# For EKS, the thumbprint is the root CA thumbprint (consistent across regions)

# The URL should be the full OIDC issuer path (including /id/XXXXX)
# EKS returns: https://oidc.eks.region.amazonaws.com/id/XXXX
# AWS IAM needs the full path after removing https://
oidc_provider = aws.iam.OpenIdConnectProvider("eks-oidc-provider",
    client_id_lists=["sts.amazonaws.com"],
    thumbprint_lists=["9e99a48a9960b14926bb7f3b02e22da2b0ab7280"],  # AWS EKS root CA thumbprint
    url=oidc_issuer  # Keep the full https:// URL as AWS expects it
)

# Update the oidc_provider_arn to use the created provider
oidc_provider_arn = oidc_provider.arn
# ============================================================================

# Simple k8s provider
k8s_provider = k8s.Provider("k8s-provider")

# IAM Role for External DNS
external_dns_role = aws.iam.Role("external-dns-role",
    assume_role_policy=pulumi.Output.all(oidc_provider_arn, oidc_issuer).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": args[0]  # oidc_provider_arn
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{args[1].replace('https://', '')}:sub": "system:serviceaccount:external-dns:external-dns",
                        f"{args[1].replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

aws.iam.RolePolicy("external-dns-policy",
    role=external_dns_role.id,
    policy=json.dumps({
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
    })
)

# IAM Role for Cluster Autoscaler
cluster_autoscaler_role = aws.iam.Role("cluster-autoscaler-role",
    assume_role_policy=pulumi.Output.all(oidc_provider_arn, oidc_issuer).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": args[0]  # oidc_provider_arn
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{args[1].replace('https://', '')}:sub": "system:serviceaccount:kube-system:cluster-autoscaler",
                        f"{args[1].replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

aws.iam.RolePolicy("cluster-autoscaler-policy",
    role=cluster_autoscaler_role.id,
    policy=json.dumps({
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
    })
)

# ============================================================================
# EBS CSI Driver - Required for EBS volume provisioning
# ============================================================================

# IAM Role for EBS CSI Driver
ebs_csi_role = aws.iam.Role("ebs-csi-driver-role",
    assume_role_policy=pulumi.Output.all(oidc_provider_arn, oidc_issuer).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": args[0]  # oidc_provider_arn
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{args[1].replace('https://', '')}:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa",
                        f"{args[1].replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

# Attach AWS managed policy for EBS CSI Driver
aws.iam.RolePolicyAttachment("ebs-csi-driver-policy",
    role=ebs_csi_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
)

# Install EBS CSI Driver as EKS Addon
ebs_csi_addon = aws.eks.Addon("ebs-csi-driver",
    cluster_name=cluster_name,
    addon_name="aws-ebs-csi-driver",
    addon_version="v1.37.0-eksbuild.1",  # Latest version for EKS 1.33
    service_account_role_arn=ebs_csi_role.arn,
    resolve_conflicts_on_create="OVERWRITE",
    resolve_conflicts_on_update="OVERWRITE"
)

# ============================================================================

# ============================================================================
# External Secrets Operator - IAM Role for AWS Secrets Manager integration
# ============================================================================

# IAM Role for External Secrets Operator
external_secrets_role = aws.iam.Role("external-secrets-operator-role",
    assume_role_policy=pulumi.Output.all(oidc_provider_arn, oidc_issuer).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": args[0]  # oidc_provider_arn
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{args[1].replace('https://', '')}:sub": "system:serviceaccount:external-secrets:external-secrets",
                        f"{args[1].replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

# IAM Policy for External Secrets Operator to access Secrets Manager
external_secrets_policy = aws.iam.RolePolicy("external-secrets-policy",
    role=external_secrets_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": [
                f"arn:aws:secretsmanager:{aws_region}:{current.account_id}:secret:oauth2-proxy-auth0-*"
            ]
        }]
    })
)

# ============================================================================


