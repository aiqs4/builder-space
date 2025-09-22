"""
Kubernetes Resources Deployment - KISS approach
Deploys ArgoCD using Helm chart to existing EKS cluster
"""

import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v4 import Chart, ChartOpts

# Configuration
config = pulumi.Config()
cluster_name = config.get("cluster_name") or "builder-space"
argocd_namespace = config.get("argocd_namespace") or "argocd"
aws_region = config.get("aws:region") or "af-south-1"

# Get current AWS region
current_region = aws.get_region()

# Get EKS cluster information
cluster_info = aws.eks.get_cluster(name=cluster_name)

# Configure Kubernetes provider using EKS cluster
k8s_provider = k8s.Provider("k8s-provider",
    kubeconfig=pulumi.Output.all(
        cluster_info.endpoint,
        cluster_info.certificate_authority.data,
        cluster_name,
        current_region.name
    ).apply(lambda args: f"""apiVersion: v1
clusters:
- cluster:
    server: {args[0]}
    certificate-authority-data: {args[1]}
  name: {args[2]}
contexts:
- context:
    cluster: {args[2]}
    user: {args[2]}
  name: {args[2]}
current-context: {args[2]}
kind: Config
preferences: {{}}
users:
- name: {args[2]}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
        - eks
        - get-token
        - --cluster-name
        - {args[2]}
        - --region
        - {args[3]}
""")
)

# Create ArgoCD namespace
argocd_ns = k8s.core.v1.Namespace(
    "argocd-namespace",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name=argocd_namespace,
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Deploy ArgoCD using Helm chart
argocd_chart = Chart(
    "argocd",
    ChartOpts(
        chart="argo-cd",
        version="7.7.9",  # Latest stable version
        namespace=argocd_namespace,
        repository_opts=k8s.helm.v4.RepositoryOptsArgs(
            repo="https://argoproj.github.io/argo-helm"
        ),
        values={
            # Expose ArgoCD server via LoadBalancer
            "server": {
                "service": {
                    "type": "LoadBalancer",
                    "annotations": {
                        "service.beta.kubernetes.io/aws-load-balancer-type": "nlb",
                        "service.beta.kubernetes.io/aws-load-balancer-scheme": "internet-facing"
                    }
                },
                "extraArgs": [
                    "--insecure"  # Allow HTTP access for initial setup
                ]
            },
            # Disable dex for simplicity (use built-in admin user)
            "dex": {
                "enabled": False
            },
            # Redis configuration for session storage
            "redis": {
                "enabled": True
            },
            # Repository server configuration
            "repoServer": {
                "replicas": 1
            },
            # Application controller configuration
            "controller": {
                "replicas": 1
            }
        }
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[argocd_ns]
    )
)

# Get ArgoCD server service to extract LoadBalancer endpoint
argocd_server_service = k8s.core.v1.Service.get(
    "argocd-server-service",
    pulumi.Output.concat(argocd_namespace, "/argocd-server"),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[argocd_chart])
)

# Get the initial admin password secret (for reference in exports)
# Note: The actual password retrieval should be done via kubectl

# Exports
pulumi.export("cluster_name", cluster_name)
pulumi.export("argocd_namespace", argocd_namespace)

# ArgoCD endpoint (LoadBalancer URL)
pulumi.export("argocd_endpoint", 
    argocd_server_service.status.load_balancer.ingress[0].hostname.apply(
        lambda hostname: f"http://{hostname}" if hostname else "LoadBalancer provisioning..."
    )
)

# ArgoCD access details
pulumi.export("argocd_username", "admin")

# Export command to get initial password (safer than trying to decode in Pulumi)
pulumi.export("argocd_password_command", 
    f"kubectl get secret argocd-initial-admin-secret -n {argocd_namespace} -o jsonpath='{{.data.password}}' | base64 -d"
)

# kubectl commands for manual access
pulumi.export("kubectl_argocd_commands", [
    f"aws eks --region {aws_region} update-kubeconfig --name {cluster_name}",
    f"kubectl get svc -n {argocd_namespace}",
    f"kubectl get secret argocd-initial-admin-secret -n {argocd_namespace} -o jsonpath='{{.data.password}}' | base64 -d",
    f"kubectl port-forward svc/argocd-server -n {argocd_namespace} 8080:443"
])

# ArgoCD CLI setup commands  
pulumi.export("argocd_cli_setup", [
    "# Install ArgoCD CLI",
    "curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64",
    "sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd",
    "rm argocd-linux-amd64",
    "",
    "# Login to ArgoCD (replace ARGOCD_SERVER with the LoadBalancer URL)",
    f"argocd login ARGOCD_SERVER --username admin --password $(kubectl get secret argocd-initial-admin-secret -n {argocd_namespace} -o jsonpath='{{.data.password}}' | base64 -d)"
])