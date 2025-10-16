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

# Get the hosted zone ID for k8s.lightsphere.space (if domain_name is configured)
hosted_zone_id = None
if domain_name:
    # Look up the hosted zone for the domain
    hosted_zone = aws.route53.get_zone(name=domain_name, private_zone=False)
    hosted_zone_id = hosted_zone.zone_id
    
    # Create DNS record for cluster API endpoint: api.k8s.lightsphere.space -> EKS endpoint
    # Extract the hostname from the cluster endpoint (remove https://)
    cluster_endpoint_hostname = cluster_info.endpoint.replace("https://", "")
    
    api_dns_record = aws.route53.Record("cluster-api-dns",
        zone_id=hosted_zone_id,
        name=f"api.{domain_name}",
        type="CNAME",
        ttl=300,
        records=[cluster_endpoint_hostname]
    )


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
# - Cluster Autoscaler, External DNS, EBS CSI Driver, etc.
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

# Namespaces
namespaces = {
    "argocd": "argocd",
    "external-dns": "external-dns",
    "cert-manager": "cert-manager"
}

for name, ns in namespaces.items():
    k8s.core.v1.Namespace(f"{name}-namespace",
        metadata=k8s.meta.v1.ObjectMetaArgs(name=ns),
        opts=pulumi.ResourceOptions(provider=k8s_provider)
    )

# ArgoCD Redis secret for authentication
argocd_redis_secret = k8s.core.v1.Secret("argocd-redis-secret",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="argocd-redis",
        namespace="argocd"
    ),
    type="Opaque",
    string_data={
        "auth": config.get("redis_password") or "defaultredispassword123"
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# ArgoCD with production configuration
argocd_chart = Chart("argocd",
    ChartArgs(
        chart="argo-cd",
        version="7.8.2",  # Updated to latest stable
        namespace="argocd",
        repository_opts=k8s.helm.v4.RepositoryOptsArgs(
            repo="https://argoproj.github.io/argo-helm"
        ),
        values={
            "server": {
                "service": {
                    "type": "ClusterIP",  # Changed from LoadBalancer - using Ingress instead
                },
                # Remove ingress from Pulumi - let ArgoCD manage it via GitOps
                "extraArgs": ["--insecure"],  # Allows HTTP backend while ingress handles TLS
                "config": {
                    "application.instanceLabelKey": "argocd.argoproj.io/instance",
                    "server.rbac.policy.default": "role:readonly",
                    "server.rbac.policy.csv": "p, role:admin, applications, *, */*, allow\np, role:admin, certificates, *, *, allow\np, role:admin, clusters, *, *, allow\np, role:admin, repositories, *, *, allow\ng, admin, role:admin"
                }
            },
            "controller": {
                "replicas": 1,
                "resources": {
                    "limits": {"cpu": "500m", "memory": "512Mi"},
                    "requests": {"cpu": "250m", "memory": "256Mi"}
                }
            },
            "dex": {"enabled": False},
            "redis": {
                "enabled": True,
                "auth": {
                    "enabled": True
                }
            },
            "repoServer": {
                "replicas": 1,
                "affinity": {
                    "podAntiAffinity": {
                        "preferredDuringSchedulingIgnoredDuringExecution": [
                            {
                                "weight": 100,
                                "podAffinityTerm": {
                                    "labelSelector": {
                                        "matchLabels": {
                                            "app.kubernetes.io/name": "argocd-repo-server"
                                        }
                                    },
                                    "topologyKey": "kubernetes.io/hostname"
                                }
                            }
                        ]
                    }
                }
            }
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[argocd_redis_secret])
)

# ArgoCD Application to manage infrastructure applications (App-of-Apps pattern)
argocd_infrastructure_apps = k8s.apiextensions.CustomResource("argocd-infrastructure-apps",
    api_version="argoproj.io/v1alpha1",
    kind="Application",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="infrastructure-apps",
        namespace="argocd",
        labels={
            "app": "infrastructure-apps",
            "environment": "prod"
        },
        annotations={
            "argocd.argoproj.io/sync-options": "Prune=true,Delete=true"
        }
    ),
    spec={
        "project": "default",
        "source": {
            "repoURL": "https://github.com/Amano-Software/builder-space-argocd.git",
            "targetRevision": "HEAD",
            "path": "environments/prod/infrastructure",
            "directory": {
                "include": "*/application.yaml",
                "exclude": "README.md"
            }
        },
        "destination": {
            "server": "https://kubernetes.default.svc",
            "namespace": "argocd"
        },
        "syncPolicy": {
            "automated": {
                "prune": True,
                "selfHeal": True,
                "allowEmpty": False
            },
            "syncOptions": [
                "CreateNamespace=true",
                "PrunePropagationPolicy=foreground",
                "PruneLast=true"
            ],
            "retry": {
                "limit": 5,
                "backoff": {
                    "duration": "5s",
                    "factor": 2,
                    "maxDuration": "3m"
                }
            }
        },
        "revisionHistoryLimit": 10
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[argocd_chart],
        custom_timeouts=pulumi.CustomTimeouts(
            create="5m",
            update="5m"
        ),
        # Handle conflicts with ArgoCD controller
        ignore_changes=["spec.project"]  # Let ArgoCD manage the project field
    )
)

# GitHub App Secret for ArgoCD repository access
github_app_secret = k8s.core.v1.Secret("github-app-creds",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="github-app-creds",
        namespace="argocd",
        labels={
            "argocd.argoproj.io/secret-type": "repo-creds"
        }
    ),
    string_data={
        "type": "git",
        "url": "https://github.com",
        "githubAppID": config.require("githubAppID"),  # Set in Pulumi config
        "githubAppInstallationID": config.require("githubAppInstallationID"),  # Set in Pulumi config
        "githubAppPrivateKey": config.require_secret("githubAppPrivateKey")  # Set in Pulumi config (sensitive)
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Get ArgoCD server endpoint
argocd_server_service = k8s.core.v1.Service.get("argocd-server-svc",
    "argocd/argocd-server",
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[argocd_chart])
)

# Exports
pulumi.export("cluster_name", cluster_name)
pulumi.export("aws_region", aws_region)

# ArgoCD is now ClusterIP - access via port-forward initially, then via ingress after ArgoCD syncs
pulumi.export("argocd_endpoint", "Port-forward: kubectl port-forward svc/argocd-server -n argocd 8080:80 (ingress will be available after ArgoCD syncs)")


pulumi.export("setup_commands", {
    "kubeconfig": f"aws eks update-kubeconfig --region {aws_region} --name {cluster_name}",
    "argocd_password": f"kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{{.data.password}}' | base64 -d",
    "port_forward": "kubectl port-forward svc/argocd-server -n argocd 8080:80",
    "verify_components": [
        "kubectl get pods -n argocd",
        "kubectl get pods -n external-dns", 
        "kubectl get pods -n kube-system | grep cluster-autoscaler"
    ]
})

# ============================================================================
# OAuth2 Proxy Secret for Auth0 Authentication (AWS Secrets Manager)
# ============================================================================
# Create namespace for oauth2-proxy
oauth2_proxy_namespace = k8s.core.v1.Namespace("oauth2-proxy",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="oauth2-proxy",
        labels={
            "name": "oauth2-proxy",
            "managed-by": "pulumi",
        },
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Generate a random cookie secret (32 bytes)
import random as py_random
import string
import base64

def generate_cookie_secret(_):
    # Generate 32 random bytes and base64 encode
    random_bytes = ''.join(py_random.choices(string.ascii_letters + string.digits + string.punctuation, k=32))
    return base64.b64encode(random_bytes.encode()).decode()

cookie_secret = pulumi.Output.from_input("generate").apply(generate_cookie_secret)

# # Create AWS Secrets Manager secret for OAuth2 Proxy
# # This will be synced to Kubernetes by External Secrets Operator
# oauth2_proxy_aws_secret = aws.secretsmanager.Secret("oauth2-proxy-auth0",
#     name="oauth2-proxy-auth0",
#     description="OAuth2 Proxy Auth0 credentials (client-id, client-secret, cookie-secret)",
#     tags={
#         "ManagedBy": "Pulumi",
#         "Application": "oauth2-proxy",
#         "Environment": "prod"
#     }
# )

# Reference existing AWS Secrets Manager secret (created by previous run or manually)
oauth2_proxy_aws_secret = aws.secretsmanager.get_secret(name="oauth2-proxy-auth0")

# Update the secret value in AWS Secrets Manager
oauth2_proxy_secret_version = aws.secretsmanager.SecretVersion("oauth2-proxy-auth0-version",
    secret_id=oauth2_proxy_aws_secret.id,
    secret_string=pulumi.Output.all(
        config.require_secret("auth0_client_id"),
        config.require_secret("auth0_client_secret"),
        cookie_secret
    ).apply(lambda args: json.dumps({
        "client-id": args[0],
        "client-secret": args[1],
        "cookie-secret": args[2]
    }))
)

pulumi.export("oauth2_proxy_setup", {
    "namespace": oauth2_proxy_namespace.metadata.name,
    "aws_secret_arn": oauth2_proxy_aws_secret.arn,
    "aws_secret_name": oauth2_proxy_aws_secret.name,
    "note": "Configure secrets with: pulumi config set --secret auth0_client_id YOUR_ID && pulumi config set --secret auth0_client_secret YOUR_SECRET"
})
# ============================================================================

pulumi.export("domain_setup", {
    # "subdomain_zone_id": subdomain_zone_id,
    # "subdomain_nameservers": subdomain_nameservers,
    # "dnssec_ds_record": dnssec_ds_record,
    "note": "Ensure DS record is added at parent; NS delegation already managed in DNS stack"
})

pulumi.export("domain_requirements", {
    "oauth2_proxy": "auth.k8s.lightsphere.space",
    "note": "Let's Encrypt certificate will be auto-issued by cert-manager for all *.k8s.lightsphere.space domains",
    "cert_issuer": "letsencrypt-production (configured in ArgoCD)",
    "dns_validation": "External-DNS automatically creates DNS records for ingresses"
})

# IAM Role ARNs for ArgoCD manifests
pulumi.export("iam_roles", {
    "external_dns_role_arn": external_dns_role.arn,
    "cluster_autoscaler_role_arn": cluster_autoscaler_role.arn,
    "ebs_csi_driver_role_arn": ebs_csi_role.arn,
    "external_secrets_operator_role_arn": external_secrets_role.arn,
    "oauth2_proxy_note": "OAuth2 Proxy uses node IAM role for ECR access (no dedicated role needed)",
})

# GitOps setup instructions
pulumi.export("gitops_next_steps", [
    "1. Get IAM role ARNs: pulumi stack output iam_roles",
    "2. Update ArgoCD manifests with IAM role ARNs",
    "3. Configure OAuth2 Proxy Auth0 credentials:",
    "   pulumi config set --secret auth0_client_id YOUR_CLIENT_ID",
    "   pulumi config set --secret auth0_client_secret YOUR_CLIENT_SECRET",
    "4. Push manifests to builder-space-argocd repository",
    "5. ArgoCD will automatically sync the resources",
    "6. Verify resources are running in the cluster",
    "7. OAuth2 Proxy will be available at: https://auth.k8s.lightsphere.space"
])