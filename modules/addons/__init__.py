"""
Addons Module
Kubernetes add-ons and applications for EKS cluster
"""

import pulumi
import pulumi_kubernetes as k8s
from typing import Dict, Optional

class AddonsResources:
    """Kubernetes addons for EKS cluster"""
    
    def __init__(self,
                 cluster_name: str,
                 cluster_endpoint: pulumi.Output[str],
                 cluster_ca_data: pulumi.Output[str],
                 enable_metrics_server: bool = True,
                 enable_aws_load_balancer_controller: bool = False,
                 enable_test_deployment: bool = True,
                 tags: Dict[str, str] = None):
        
        self.cluster_name = cluster_name
        self.tags = tags or {}
        
        # Create Kubernetes provider
        self.k8s_provider = k8s.Provider(
            f"{cluster_name}-k8s-provider",
            server=cluster_endpoint,
            cluster_ca_certificate=cluster_ca_data.apply(lambda data: data),
            exec=k8s.ProviderExecArgs(
                api_version="client.authentication.k8s.io/v1beta1",
                command="aws",
                args=["eks", "get-token", "--cluster-name", cluster_name]
            )
        )
        
        # Create test namespace
        self.test_namespace = k8s.core.v1.Namespace(
            f"{cluster_name}-test-namespace",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name="test",
                labels={
                    "name": "test",
                    "managed-by": "pulumi"
                }
            ),
            opts=pulumi.ResourceOptions(provider=self.k8s_provider)
        )
        
        self.addons_status = {}
        
        # Metrics Server
        if enable_metrics_server:
            self.metrics_server = k8s.helm.v3.Release(
                f"{cluster_name}-metrics-server",
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
                opts=pulumi.ResourceOptions(provider=self.k8s_provider)
            )
            self.addons_status["metrics_server"] = "✅ Enabled"
        else:
            self.addons_status["metrics_server"] = "❌ Disabled"
        
        # AWS Load Balancer Controller (optional)
        if enable_aws_load_balancer_controller:
            # Note: This requires additional IAM setup that would be complex to implement here
            # For now, we'll mark it as available but not implemented
            self.addons_status["aws_load_balancer_controller"] = "⚠️ Available (requires additional IAM setup)"
        else:
            self.addons_status["aws_load_balancer_controller"] = "❌ Disabled"
        
        # Test deployment for internet connectivity
        if enable_test_deployment:
            self.test_deployment = k8s.apps.v1.Deployment(
                f"{cluster_name}-test-internet-app",
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    name="test-internet-app",
                    namespace=self.test_namespace.metadata.name,
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
                opts=pulumi.ResourceOptions(provider=self.k8s_provider)
            )
            self._test_deployment_name = "test-internet-app"
        else:
            self._test_deployment_name = ""
    
    @property
    def metrics_server_status(self) -> str:
        """Get metrics server status"""
        return self.addons_status.get("metrics_server", "❌ Unknown")
    
    @property
    def aws_load_balancer_controller_status(self) -> str:
        """Get AWS Load Balancer Controller status"""
        return self.addons_status.get("aws_load_balancer_controller", "❌ Unknown")
    
    @property
    def test_namespace_name(self) -> pulumi.Output[str]:
        """Get test namespace name"""
        return self.test_namespace.metadata.name
    
    @property
    def test_deployment_name(self) -> str:
        """Get test deployment name"""
        return self._test_deployment_name