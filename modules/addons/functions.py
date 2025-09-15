"""
Addons Module Functions
Kubernetes add-ons and applications for EKS cluster
Refactored to function-based style following Pulumi best practices
"""

import pulumi
import pulumi_kubernetes as k8s
from typing import Dict, Optional


def create_kubernetes_provider(name: str, cluster_endpoint: 'pulumi.Output[str]', 
                              cluster_ca_data: 'pulumi.Output[str]') -> k8s.Provider:
    """
    Create Kubernetes provider for EKS cluster
    
    Args:
        name: Provider name
        cluster_endpoint: EKS cluster endpoint
        cluster_ca_data: EKS cluster CA certificate data
        
    Returns:
        Kubernetes provider instance
    """
    return k8s.Provider(
        f"{name}-k8s-provider",
        server=cluster_endpoint,
        cluster_ca_certificate=cluster_ca_data.apply(lambda data: data),
        exec=k8s.ProviderExecArgs(
            api_version="client.authentication.k8s.io/v1beta1",
            command="aws",
            args=["eks", "get-token", "--cluster-name", name]
        )
    )


def create_test_namespace(name: str, provider: k8s.Provider) -> Dict[str, any]:
    """
    Create test namespace for applications
    
    Args:
        name: Namespace name prefix
        provider: Kubernetes provider
        
    Returns:
        Dict with namespace resource and outputs
    """
    namespace = k8s.core.v1.Namespace(
        f"{name}-test-namespace",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="test",
            labels={
                "name": "test",
                "managed-by": "pulumi"
            }
        ),
        opts=pulumi.ResourceOptions(provider=provider)
    )
    
    return {
        "namespace": namespace,
        "namespace_name": namespace.metadata.name
    }


def deploy_metrics_server(name: str, provider: k8s.Provider) -> Dict[str, any]:
    """
    Deploy metrics server using Helm
    
    Args:
        name: Release name prefix
        provider: Kubernetes provider
        
    Returns:
        Dict with metrics server resources
    """
    metrics_server = k8s.helm.v3.Release(
        f"{name}-metrics-server",
        repository_opts=k8s.helm.v3.RepositoryOptsArgs(
            repo="https://kubernetes-sigs.github.io/metrics-server/"
        ),
        chart="metrics-server",
        name="metrics-server",
        namespace="kube-system",
        values={
            "args": [
                "--cert-dir=/tmp",
                "--secure-port=4443",
                "--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname",
                "--kubelet-use-node-status-port",
                "--metric-resolution=15s"
            ]
        },
        opts=pulumi.ResourceOptions(provider=provider)
    )
    
    return {
        "metrics_server": metrics_server,
        "status": "✅ Enabled"
    }


def deploy_test_internet_app(name: str, namespace_name: 'pulumi.Output[str]', 
                            provider: k8s.Provider) -> Dict[str, any]:
    """
    Deploy test application for internet connectivity
    
    Args:
        name: Application name prefix
        namespace_name: Namespace name
        provider: Kubernetes provider
        
    Returns:
        Dict with test deployment resources
    """
    deployment = k8s.apps.v1.Deployment(
        f"{name}-test-internet-app",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="test-internet-app",
            namespace=namespace_name,
            labels={
                "app": "test-internet",
                "managed-by": "pulumi"
            }
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=1,
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"app": "test-internet"}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"app": "test-internet"}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=[
                        k8s.core.v1.ContainerArgs(
                            name="test-internet",
                            image="busybox:1.35",
                            command=[
                                "sh", "-c",
                                "while true; do echo 'Testing internet connectivity...'; "
                                "nslookup google.com; "
                                "if wget -qO- --timeout=5 http://httpbin.org/ip; then "
                                "echo 'Internet connectivity: OK'; else "
                                "echo 'Internet connectivity: FAILED'; fi; "
                                "sleep 30; done"
                            ],
                            resources=k8s.core.v1.ResourceRequirementsArgs(
                                requests={
                                    "cpu": "10m",
                                    "memory": "32Mi"
                                },
                                limits={
                                    "cpu": "50m",
                                    "memory": "64Mi"
                                }
                            )
                        )
                    ],
                    restart_policy="Always"
                )
            )
        ),
        opts=pulumi.ResourceOptions(provider=provider)
    )
    
    return {
        "deployment": deployment,
        "deployment_name": "test-internet-app"
    }


def create_addons_resources(cluster_name: str,
                           cluster_endpoint: 'pulumi.Output[str]',
                           cluster_ca_data: 'pulumi.Output[str]',
                           enable_metrics_server: bool = True,
                           enable_aws_load_balancer_controller: bool = False,
                           enable_test_deployment: bool = True,
                           tags: Dict[str, str] = None) -> Dict[str, any]:
    """
    Create Kubernetes addons for EKS cluster
    
    Args:
        cluster_name: EKS cluster name
        cluster_endpoint: EKS cluster endpoint
        cluster_ca_data: EKS cluster CA certificate data
        enable_metrics_server: Deploy metrics server
        enable_aws_load_balancer_controller: Deploy AWS Load Balancer Controller
        enable_test_deployment: Deploy test application
        tags: Additional tags
        
    Returns:
        Dict with all addon resources and status
    """
    tags = tags or {}
    
    # Create Kubernetes provider
    k8s_provider = create_kubernetes_provider(cluster_name, cluster_endpoint, cluster_ca_data)
    
    # Create test namespace
    namespace_result = create_test_namespace(cluster_name, k8s_provider)
    
    # Track addon status
    addons_status = {}
    
    # Deploy metrics server
    metrics_server_result = None
    if enable_metrics_server:
        metrics_server_result = deploy_metrics_server(cluster_name, k8s_provider)
        addons_status["metrics_server"] = metrics_server_result["status"]
    else:
        addons_status["metrics_server"] = "❌ Disabled"
    
    # AWS Load Balancer Controller (placeholder)
    if enable_aws_load_balancer_controller:
        addons_status["aws_load_balancer_controller"] = "⚠️ Available (requires additional IAM setup)"
    else:
        addons_status["aws_load_balancer_controller"] = "❌ Disabled"
    
    # Deploy test application
    test_deployment_result = None
    if enable_test_deployment:
        test_deployment_result = deploy_test_internet_app(
            cluster_name, 
            namespace_result["namespace_name"], 
            k8s_provider
        )
    
    return {
        "metrics_server_status": addons_status.get("metrics_server", "❌ Unknown"),
        "aws_load_balancer_controller_status": addons_status.get("aws_load_balancer_controller", "❌ Unknown"),
        "test_namespace_name": namespace_result["namespace_name"],
        "test_deployment_name": test_deployment_result["deployment_name"] if test_deployment_result else "",
        # Keep references to resources for dependencies
        "_k8s_provider": k8s_provider,
        "_namespace": namespace_result["namespace"],
        "_metrics_server": metrics_server_result["metrics_server"] if metrics_server_result else None,
        "_test_deployment": test_deployment_result["deployment"] if test_deployment_result else None
    }