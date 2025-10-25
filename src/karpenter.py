"""
Karpenter - Autoscaling
Efficient, fast autoscaling for Kubernetes
"""
import json
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s

def setup_karpenter(cluster_info, network):
    """Setup Karpenter for cluster autoscaling"""
    
    current = aws.get_caller_identity()
    region = aws.get_region()
    cluster = cluster_info["cluster"]
    cluster_name = cluster_info["cluster_name"]
    node_role = cluster_info["node_role"]
    
    # Karpenter controller IAM policy
    policy = aws.iam.Policy("karpenter-controller-policy",
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
                    "Resource": node_role.arn
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "eks:DescribeCluster"
                    ],
                    "Resource": cluster.arn
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "pricing:GetProducts"
                    ],
                    "Resource": "*"
                }
            ]
        }))

    # IAM role using Pod Identity
    role = aws.iam.Role("karpenter-controller-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "pods.eks.amazonaws.com"},
                "Action": ["sts:AssumeRole", "sts:TagSession"]
            }]
        }))

    aws.iam.RolePolicyAttachment("karpenter-policy-attach",
        role=role.name,
        policy_arn=policy.arn)

    # Pod Identity Association
    pod_identity = aws.eks.PodIdentityAssociation("karpenter-pod-identity",
        cluster_name=cluster.name,
        namespace="kube-system",
        service_account="karpenter",
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

    k8s_provider = k8s.Provider("k8s-karpenter",
        kubeconfig=kubeconfig,
        opts=pulumi.ResourceOptions(depends_on=[cluster]))

    # Install Karpenter via Helm
    karpenter = k8s.helm.v3.Release("karpenter",
        chart="karpenter",
        version="1.0.6",  # Latest stable
        namespace="kube-system",
        repository_opts=k8s.helm.v3.RepositoryOptsArgs(
            repo="oci://public.ecr.aws/karpenter"
        ),
        values={
            "settings": {
                "clusterName": cluster_name,
                "clusterEndpoint": cluster.endpoint,
                "interruptionQueue": cluster_name,
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
            depends_on=[pod_identity]
        ))

    # Default NodePool for general workloads
    node_pool = k8s.apiextensions.CustomResource("default-node-pool",
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
            depends_on=[karpenter]
        ))

    # EC2NodeClass for the NodePool
    node_class = k8s.apiextensions.CustomResource("default-node-class",
        api_version="karpenter.k8s.aws/v1",
        kind="EC2NodeClass",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="default",
            namespace="kube-system",
        ),
        spec={
            "amiFamily": "AL2023",
            "role": node_role.name,
            "subnetSelectorTerms": [
                {"tags": {"kubernetes.io/role/elb": "1"}}
            ],
            "securityGroupSelectorTerms": [
                {"tags": {f"kubernetes.io/cluster/{cluster_name}": "owned"}}
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
            depends_on=[karpenter]
        ))

    return {
        "release": karpenter,
        "node_pool": node_pool,
        "node_class": node_class,
        "role_arn": role.arn,
    }
