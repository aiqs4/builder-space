"""
Karpenter - Autoscaling
Efficient, fast autoscaling for Kubernetes
"""
import json
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s
from . import cluster, network

# Get AWS info
current = aws.get_caller_identity()
region = aws.get_region()

# Karpenter controller IAM policy
karpenter_policy = aws.iam.Policy("karpenter-controller-policy",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateFleet",
                    "ec2:CreateLaunchTemplate",
                    "ec2:CreateTags",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeImages",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceTypeOfferings",
                    "ec2:DescribeInstanceTypes",
                    "ec2:DescribeLaunchTemplates",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSpotPriceHistory",
                    "ec2:DescribeSubnets",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances",
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": cluster.node_role.arn
            },
            {
                "Effect": "Allow",
                "Action": ["eks:DescribeCluster"],
                "Resource": cluster.cluster.arn
            },
            {
                "Effect": "Allow",
                "Action": ["pricing:GetProducts"],
                "Resource": "*"
            }
        ]
    }))

# IAM role using Pod Identity
karpenter_role = aws.iam.Role("karpenter-controller-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "pods.eks.amazonaws.com"},
            "Action": ["sts:AssumeRole", "sts:TagSession"]
        }]
    }))

aws.iam.RolePolicyAttachment("karpenter-policy-attach",
    role=karpenter_role.name,
    policy_arn=karpenter_policy.arn)

# Pod Identity Association
karpenter_pod_identity = aws.eks.PodIdentityAssociation("karpenter-pod-identity",
    cluster_name=cluster.cluster.name,
    namespace="kube-system",
    service_account="karpenter",
    role_arn=karpenter_role.arn)

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

k8s_provider = k8s.Provider("k8s-karpenter",
    kubeconfig=kubeconfig,
    opts=pulumi.ResourceOptions(depends_on=[cluster.cluster]))

# Install Karpenter via Helm
karpenter_release = k8s.helm.v3.Release("karpenter",
    chart="karpenter",
    version="1.0.6",
    namespace="kube-system",
    repository_opts=k8s.helm.v3.RepositoryOptsArgs(
        repo="oci://public.ecr.aws/karpenter"
    ),
    values={
        "settings": {
            "clusterName": cluster.cluster_name,
            "clusterEndpoint": cluster.cluster.endpoint,
            "interruptionQueue": cluster.cluster_name,
        },
        "serviceAccount": {
            "name": "karpenter",
            "annotations": {},
        },
        "controller": {
            "resources": {
                "requests": {
                    "cpu": "100m",
                    "memory": "256Mi"
                }
            }
        }
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[karpenter_pod_identity]
    ))

# Default NodePool for general workloads
karpenter_node_pool = k8s.apiextensions.CustomResource("default-node-pool",
    api_version="karpenter.sh/v1",
    kind="NodePool",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="default",
        namespace="kube-system",
    ),
    spec={
        "template": {
            "spec": {
                "nodeClassRef": {
                    "group": "karpenter.k8s.aws",
                    "kind": "EC2NodeClass",
                    "name": "default",
                },
                "requirements": [
                    {
                        "key": "kubernetes.io/arch",
                        "operator": "In",
                        "values": ["amd64", "arm64"]
                    },
                    {
                        "key": "kubernetes.io/os",
                        "operator": "In",
                        "values": ["linux"]
                    },
                    {
                        "key": "karpenter.sh/capacity-type",
                        "operator": "In",
                        "values": ["spot", "on-demand"]
                    },
                    {
                        "key": "karpenter.k8s.aws/instance-category",
                        "operator": "In",
                        "values": ["t", "c", "m"]
                    },
                ],
            },
        },
        "limits": {
            "cpu": "100",
            "memory": "400Gi"
        },
        "disruption": {
            "consolidationPolicy": "WhenEmptyOrUnderutilized",
            "consolidateAfter": "1m",
        },
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[karpenter_release]
    ))

# EC2NodeClass for the NodePool
karpenter_node_class = k8s.apiextensions.CustomResource("default-node-class",
    api_version="karpenter.k8s.aws/v1",
    kind="EC2NodeClass",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="default",
        namespace="kube-system",
    ),
    spec={
        "amiFamily": "AL2023",
        "role": cluster.node_role.name,
        "subnetSelectorTerms": [
            {"tags": {"kubernetes.io/role/elb": "1"}}
        ],
        "securityGroupSelectorTerms": [
            {"tags": {f"kubernetes.io/cluster/{cluster.cluster_name}": "owned"}}
        ],
        "blockDeviceMappings": [{
            "deviceName": "/dev/xvda",
            "ebs": {
                "volumeSize": "100Gi",
                "volumeType": "gp3",
                "deleteOnTermination": True,
            }
        }],
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[karpenter_release]
    ))
