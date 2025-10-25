"""
External DNS
Automatic DNS management for services
"""
import json
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s

def setup_external_dns(cluster_info, domains):
    """Setup External DNS with Route53 access"""
    
    current = aws.get_caller_identity()
    cluster = cluster_info["cluster"]
    
    # IAM policy for Route53 access
    policy = aws.iam.Policy("external-dns-policy",
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

    # IAM role using Pod Identity (modern IRSA)
    role = aws.iam.Role("external-dns-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "pods.eks.amazonaws.com"},
                "Action": ["sts:AssumeRole", "sts:TagSession"]
            }]
        }))

    aws.iam.RolePolicyAttachment("external-dns-policy-attach",
        role=role.name,
        policy_arn=policy.arn)

    # Pod Identity Association
    pod_identity = aws.eks.PodIdentityAssociation("external-dns-pod-identity",
        cluster_name=cluster.name,
        namespace="kube-system",
        service_account="external-dns",
        role_arn=role.arn)

    # Kubernetes provider
    kubeconfig = pulumi.Output.all(
        cluster.endpoint,
        cluster.certificate_authority.data,
        cluster.name
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
        opts=pulumi.ResourceOptions(depends_on=[cluster]))

    # ServiceAccount
    sa = k8s.core.v1.ServiceAccount("external-dns-sa",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="external-dns",
            namespace="kube-system",
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[pod_identity]
        ))

    # Deployment
    deployment = k8s.apps.v1.Deployment("external-dns",
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
                    service_account_name=sa.metadata.name,
                    containers=[k8s.core.v1.ContainerArgs(
                        name="external-dns",
                        image="registry.k8s.io/external-dns/external-dns:v0.14.2",
                        args=[
                            "--source=service",
                            "--source=ingress",
                            "--provider=aws",
                            f"--domain-filter={';'.join(domains)}",
                            "--policy=sync",
                            "--registry=txt",
                            "--txt-owner-id=builder-space",
                        ],
                    )],
                )
            ),
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            depends_on=[sa, pod_identity]
        ))

    return {
        "deployment": deployment,
        "service_account": sa,
        "role_arn": role.arn,
    }
