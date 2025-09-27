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

# Reference DNS stack providing the hosted zone & DNSSEC outputs
dns_stack_name = config.require("dns_stack")  # e.g. org/project/stack for infra-k8s-dns
dns_stack = pulumi.StackReference(dns_stack_name)

subdomain_zone_id = dns_stack.get_output("subdomain_zone_id")
subdomain_nameservers = dns_stack.get_output("subdomain_name_servers")
dnssec_ds_record = dns_stack.get_output("dnssec_ds_record")
domain_name_output = dns_stack.get_output("subdomain_zone_name")

# Allow override via config (optional); fallback to referenced zone name
domain_name = config.get("domain_name") or domain_name_output

# Get cluster info
cluster_info = aws.eks.get_cluster(name=cluster_name)
current = aws.get_caller_identity()
current_region = aws.get_region()

# Simple k8s provider
k8s_provider = k8s.Provider("k8s-provider")

# IAM Role for External DNS
external_dns_role = aws.iam.Role("external-dns-role",
    assume_role_policy=cluster_info.identities[0].oidc.issuer.apply(
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
    assume_role_policy=cluster_info.identities[0].oidc.issuer.apply(
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
            "redis": {"enabled": True},
            "repoServer": {"replicas": 1}
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
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

# ArgoCD Application to manage infrastructure components (GitOps approach)
argocd_bootstrap_app = k8s.apiextensions.CustomResource("argocd-bootstrap",
    api_version="argoproj.io/v1alpha1",
    kind="Application",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="infrastructure-bootstrap",
        namespace="argocd"
    ),
    spec={
        "project": "default",
        "source": {
            "repoURL": "https://github.com/your-org/k8s-manifests",  # Replace with your repo
            "targetRevision": "HEAD",
            "path": "infrastructure"
        },
        "destination": {
            "server": "https://kubernetes.default.svc",
            "namespace": "argocd"
        },
        "syncPolicy": {
            "automated": {
                "prune": True,
                "selfHeal": True
            },
            "syncOptions": [
                "CreateNamespace=true"
            ]
        }
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
    "subdomain_zone_id": subdomain_zone_id,
    "subdomain_nameservers": subdomain_nameservers,
    "dnssec_ds_record": dnssec_ds_record,
    "note": "Ensure DS record is added at parent; NS delegation already managed in DNS stack"
})

# GitOps setup instructions
pulumi.export("gitops_next_steps", [
    "1. Create a Git repository for your K8s manifests",
    "2. Add infrastructure components as Helm charts or plain YAML",
    "3. Update the ArgoCD bootstrap application repoURL",
    "4. Commit infrastructure configs to Git",
    "5. ArgoCD will automatically sync and manage your cluster"
])