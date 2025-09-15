"""
Addons Module
Pure declarative infrastructure - no classes or functions
"""

import pulumi
import pulumi_kubernetes as k8s
from config import get_config
from modules.eks import cluster_endpoint, cluster_certificate_authority_data

# Get configuration
config = get_config()
cluster_name = config.cluster_name
tags = config.common_tags

# Create Kubernetes provider
k8s_provider = k8s.Provider(
    f"{cluster_name}-k8s-provider",
    server=cluster_endpoint,
    cluster_ca_certificate=cluster_certificate_authority_data.apply(lambda data: data),
    exec=k8s.ProviderExecArgs(
        api_version="client.authentication.k8s.io/v1beta1",
        command="aws",
        args=["eks", "get-token", "--cluster-name", cluster_name]
    )
)

# Create test namespace
test_namespace = k8s.core.v1.Namespace(
    f"{cluster_name}-test-namespace",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="test",
        labels={
            "name": "test",
            "managed-by": "pulumi"
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Metrics Server (if enabled)
metrics_server_status = "❌ Disabled"
if True:  # Always enable metrics server for basic functionality
    metrics_server = k8s.apps.v1.Deployment(
        f"{cluster_name}-metrics-server",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="metrics-server",
            namespace="kube-system",
            labels={
                "k8s-app": "metrics-server",
                "managed-by": "pulumi"
            }
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={"k8s-app": "metrics-server"}
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    labels={"k8s-app": "metrics-server"}
                ),
                spec=k8s.core.v1.PodSpecArgs(
                    service_account_name="metrics-server",
                    volumes=[
                        k8s.core.v1.VolumeArgs(
                            name="tmp-dir",
                            empty_dir=k8s.core.v1.EmptyDirVolumeSourceArgs()
                        )
                    ],
                    priority_class_name="system-cluster-critical",
                    containers=[
                        k8s.core.v1.ContainerArgs(
                            name="metrics-server",
                            image="k8s.gcr.io/metrics-server/metrics-server:v0.6.4",
                            image_pull_policy="IfNotPresent",
                            args=[
                                "--cert-dir=/tmp",
                                "--secure-port=4443",
                                "--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname",
                                "--kubelet-use-node-status-port",
                                "--metric-resolution=15s",
                                "--kubelet-insecure-tls"
                            ],
                            ports=[
                                k8s.core.v1.ContainerPortArgs(
                                    name="https",
                                    container_port=4443,
                                    protocol="TCP"
                                )
                            ],
                            volume_mounts=[
                                k8s.core.v1.VolumeMountArgs(
                                    name="tmp-dir",
                                    mount_path="/tmp"
                                )
                            ],
                            liveness_probe=k8s.core.v1.ProbeArgs(
                                http_get=k8s.core.v1.HTTPGetActionArgs(
                                    path="/livez",
                                    port=4443,
                                    scheme="HTTPS"
                                ),
                                period_seconds=10,
                                failure_threshold=3
                            ),
                            readiness_probe=k8s.core.v1.ProbeArgs(
                                http_get=k8s.core.v1.HTTPGetActionArgs(
                                    path="/readyz",
                                    port=4443,
                                    scheme="HTTPS"
                                ),
                                initial_delay_seconds=20,
                                period_seconds=10,
                                failure_threshold=3
                            ),
                            security_context=k8s.core.v1.SecurityContextArgs(
                                read_only_root_filesystem=True,
                                run_as_non_root=True,
                                run_as_user=1000,
                                allow_privilege_escalation=False,
                                seccomp_profile=k8s.core.v1.SeccompProfileArgs(
                                    type="RuntimeDefault"
                                ),
                                capabilities=k8s.core.v1.CapabilitiesArgs(
                                    drop=["ALL"]
                                )
                            )
                        )
                    ],
                    node_selector={"kubernetes.io/os": "linux"}
                )
            )
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider)
    )
    metrics_server_status = "✅ Deployed"

# Test internet connectivity deployment
test_deployment = k8s.apps.v1.Deployment(
    f"{cluster_name}-test-internet-app",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="test-internet-app",
        namespace="test",
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
                        image="alpine:latest",
                        command=["sh", "-c"],
                        args=["while true; do echo 'Testing internet connectivity...'; nslookup google.com; sleep 30; done"],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "10m", "memory": "32Mi"},
                            limits={"cpu": "100m", "memory": "128Mi"}
                        )
                    )
                ]
            )
        )
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[test_namespace])
)

# Export status information
aws_load_balancer_controller_status = "❌ Disabled (requires additional IAM setup)"
test_deployment_name = test_deployment.metadata.name