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

# Simple k8s provider
k8s_provider = k8s.Provider("k8s-provider")

# IAM Role for External DNS
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
                        f"{issuer.replace('https://', '')}:sub": "system:serviceaccount:kube-system:cluster-autoscaler",
                        f"{issuer.replace('https://', '')}:aud": "sts.amazonaws.com"
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

# cert-manager (CRDs installed via helm flag)
cert_manager_chart = Chart("cert-manager",
    ChartArgs(
        chart="cert-manager",
        version="v1.15.3",
        namespace="cert-manager",
        repository_opts=k8s.helm.v4.RepositoryOptsArgs(
            repo="https://charts.jetstack.io"
        ),
        values={
            "installCRDs": True,
            "prometheus": {"enabled": False}
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# ClusterIssuers for Let's Encrypt (staging & production)
letsencrypt_staging = k8s.apiextensions.CustomResource("letsencrypt-staging-issuer",
    api_version="cert-manager.io/v1",
    kind="ClusterIssuer",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="letsencrypt-staging"),
    spec={
        "acme": {
            "email": acme_email,
            "server": "https://acme-staging-v02.api.letsencrypt.org/directory",
            "privateKeySecretRef": {"name": "letsencrypt-staging"},
            "solvers": [
                {"http01": {"ingress": {"class": "nginx"}}}
            ]
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert_manager_chart])
)

letsencrypt_production = k8s.apiextensions.CustomResource("letsencrypt-production-issuer",
    api_version="cert-manager.io/v1",
    kind="ClusterIssuer",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="letsencrypt-production"),
    spec={
        "acme": {
            "email": acme_email,
            "server": "https://acme-v02.api.letsencrypt.org/directory",
            "privateKeySecretRef": {"name": "letsencrypt-production"},
            "solvers": [
                {"http01": {"ingress": {"class": "nginx"}}}
            ]
        }
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[cert_manager_chart])
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
                    "type": "LoadBalancer",
                    "annotations": {
                        "service.beta.kubernetes.io/aws-load-balancer-type": "nlb",
                        "service.beta.kubernetes.io/aws-load-balancer-scheme": "internet-facing"
                    }
                },
                "extraArgs": ["--insecure"],
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

# External DNS with subdomain
external_dns_chart = Chart("external-dns",
    ChartArgs(
        chart="external-dns",
        version="1.15.0",
        namespace="external-dns",
        repository_opts=k8s.helm.v4.RepositoryOptsArgs(
            repo="https://kubernetes-sigs.github.io/external-dns/"
        ),
        values={
            "provider": "aws",
            "aws": {"region": aws_region},
            "serviceAccount": {
                "create": True,
                "annotations": {"eks.amazonaws.com/role-arn": external_dns_role.arn}
            },
            "domainFilters": [domain_name],
            "policy": "sync",
            "registry": "txt",
            "txtOwnerId": cluster_name,
            "resources": {
                "limits": {"cpu": "100m", "memory": "128Mi"},
                "requests": {"cpu": "50m", "memory": "64Mi"}
            }
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Cluster Autoscaler
cluster_autoscaler_chart = Chart("cluster-autoscaler",
    ChartArgs(
        chart="cluster-autoscaler",
        version="9.37.0",
        namespace="kube-system",
        repository_opts=k8s.helm.v4.RepositoryOptsArgs(
            repo="https://kubernetes.github.io/autoscaler"
        ),
        values={
            "autoDiscovery": {
                "clusterName": cluster_name,
                "enabled": True
            },
            "awsRegion": aws_region,
            "rbac": {"serviceAccount": {
                "create": True,
                "name": "cluster-autoscaler",
                "annotations": {
                    "eks.amazonaws.com/role-arn": cluster_autoscaler_role.arn
                }
            }},
            "extraArgs": {
                "scale-down-delay-after-add": "10m",
                "scale-down-unneeded-time": "10m",
                "skip-nodes-with-local-storage": False,
                "skip-nodes-with-system-pods": False
            },
            "resources": {
                "limits": {"cpu": "100m", "memory": "300Mi"},
                "requests": {"cpu": "100m", "memory": "300Mi"}
            }
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# ArgoCD Application to manage production infrastructure via GitOps
argocd_bootstrap_app = k8s.apiextensions.CustomResource("argocd-bootstrap",
    api_version="argoproj.io/v1alpha1",
    kind="Application",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="infrastructure-bootstrap",
        namespace="argocd",
        labels={
            "app": "infrastructure-bootstrap",
            "environment": "prod"
        },
        annotations={
            "argocd.argoproj.io/sync-options": "Prune=true,Delete=true"
        }
    ),
    spec={
        "project": "default",
        "source": {
            "repoURL": "https://github.com/aiqs4/builder-space-argocd.git",
            "targetRevision": "HEAD",
            "path": "environments/prod/infrastructure"
        },
        "destination": {
            "server": "https://kubernetes.default.svc",
            "namespace": "default"
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
        depends_on=[argocd_chart]
    )
)

# Get ArgoCD server endpoint
argocd_server_service = k8s.core.v1.Service.get("argocd-server-svc",
    "argocd/argocd-server",
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[argocd_chart])
)

# Exports
pulumi.export("cluster_name", cluster_name)
pulumi.export("aws_region", aws_region)

pulumi.export("argocd_endpoint", 
    argocd_server_service.status.load_balancer.ingress[0].hostname.apply(
        lambda hostname: f"http://{hostname}" if hostname else "Provisioning..."
    )
)

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

pulumi.export("domain_setup", {
    # "subdomain_zone_id": subdomain_zone_id,
    # "subdomain_nameservers": subdomain_nameservers,
    # "dnssec_ds_record": dnssec_ds_record,
    "note": "Ensure DS record is added at parent; NS delegation already managed in DNS stack"
})

# IAM Role ARNs for ArgoCD manifests
pulumi.export("iam_roles", {
    "external_dns_role_arn": external_dns_role.arn,
    "cluster_autoscaler_role_arn": cluster_autoscaler_role.arn,
})

# GitOps setup instructions
pulumi.export("gitops_next_steps", [
    "1. Get IAM role ARNs: pulumi stack output iam_roles",
    "2. Update ArgoCD manifests with IAM role ARNs",
    "3. Push manifests to builder-space-argocd repository",
    "4. ArgoCD will automatically sync the resources",
    "5. Verify resources are running in the cluster",
    "6. Remove Helm charts from Pulumi after successful migration"
])