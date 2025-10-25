"""
External DNS
Automatic DNS management for services
"""
import json
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s
from . import cluster

# Configuration
DOMAINS = [
    "amano.services",
    "tekanya.services",
    "lightsphere.space",
    "sosolola.cloud"
]

current = aws.get_caller_identity()

# IAM policy for Route53 access
external_dns_policy = aws.iam.Policy("external-dns-policy",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "route53:ChangeResourceRecordSets",
                "route53:ListResourceRecordSets"
            ],
            "Resource": "arn:aws:route53:::hostedzone/*"
        }, {
            "Effect": "Allow",
            "Action": [
                "route53:ListHostedZones",
                "route53:ListHostedZonesByName"
            ],
            "Resource": "*"
        }]
    }))

# IAM role using Pod Identity
external_dns_role = aws.iam.Role("external-dns-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "pods.eks.amazonaws.com"},
            "Action": ["sts:AssumeRole", "sts:TagSession"]
        }]
    }))

aws.iam.RolePolicyAttachment("external-dns-policy-attach",
    role=external_dns_role.name,
    policy_arn=external_dns_policy.arn)

# Pod Identity Association
external_dns_pod_identity = aws.eks.PodIdentityAssociation("external-dns-pod-identity",
    cluster_name=cluster.cluster.name,
    namespace="kube-system",
    service_account="external-dns",
    role_arn=external_dns_role.arn)

# Kubernetes provider
kubeconfig = pulumi.Output.all(
    cluster.cluster.endpoint,
    cluster.cluster.certificate_authority.data,
    cluster.cluster.name
).apply(lambda args: f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {args[1]}
    server: {args[0]}
  name: {args[2]}
contexts:
- context:
    cluster: {args[2]}
    user: {args[2]}
  name: {args[2]}
current-context: {args[2]}
kind: Config
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
""")

k8s_provider = k8s.Provider("k8s",
    kubeconfig=kubeconfig,
    opts=pulumi.ResourceOptions(depends_on=[cluster.cluster]))

# ServiceAccount
external_dns_sa = k8s.core.v1.ServiceAccount("external-dns-sa",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="external-dns",
        namespace="kube-system",
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[external_dns_pod_identity]
    ))

# Deployment
external_dns_deployment = k8s.apps.v1.Deployment("external-dns",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="external-dns",
        namespace="kube-system",
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"app": "external-dns"}
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"app": "external-dns"}
            ),
            spec=k8s.core.v1.PodSpecArgs(
                service_account_name=external_dns_sa.metadata.name,
                containers=[k8s.core.v1.ContainerArgs(
                    name="external-dns",
                    image="registry.k8s.io/external-dns/external-dns:v0.14.2",
                    args=[
                        "--source=service",
                        "--source=ingress",
                        "--provider=aws",
                        f"--domain-filter={';'.join(DOMAINS)}",
                        "--policy=sync",
                        "--registry=txt",
                        "--txt-owner-id=lightsphere",
                    ],
                )],
            )
        ),
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[external_dns_sa, external_dns_pod_identity]
    ))
