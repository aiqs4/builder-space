"""
EKS Cluster Core
Minimal cluster setup with required IAM roles
"""
import json
import pulumi
import pulumi_aws as aws

def create_cluster(network, github_role_arn=None):
    """Create EKS cluster with minimal IAM configuration"""
    
    cluster_name = pulumi.Config().get("cluster_name") or "builder-space"
    
    # Minimal IAM role for cluster
    cluster_role = aws.iam.Role("eks-cluster-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {"Service": "eks.amazonaws.com"}
            }]
        }))

    aws.iam.RolePolicyAttachment("eks-cluster-policy",
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
        role=cluster_role.name)

    # Minimal IAM role for nodes
    node_role = aws.iam.Role("eks-node-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"}
            }]
        }))

    for policy in [
        "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
        "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",  # For session manager access
    ]:
        aws.iam.RolePolicyAttachment(f"node-policy-{policy.split('/')[-1]}",
            policy_arn=policy,
            role=node_role.name)

    # EKS Cluster
    cluster = aws.eks.Cluster("cluster",
        name=cluster_name,
        role_arn=cluster_role.arn,
        version="1.31",  # Latest stable
        vpc_config=aws.eks.ClusterVpcConfigArgs(
            subnet_ids=network["subnet_ids"],
            endpoint_public_access=True,
            endpoint_private_access=True,
        ),
        access_config=aws.eks.ClusterAccessConfigArgs(
            authentication_mode="API"
        ),
        # Enable control plane logging
        enabled_cluster_log_types=["api", "audit", "authenticator"])

    # GitHub Actions access (if provided)
    if github_role_arn:
        github_access = aws.eks.AccessEntry("github-actions-access",
            cluster_name=cluster.name,
            principal_arn=github_role_arn,
            type="STANDARD")

        aws.eks.AccessPolicyAssociation("github-actions-admin",
            cluster_name=cluster.name,
            principal_arn=github_role_arn,
            policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
            access_scope=aws.eks.AccessPolicyAssociationAccessScopeArgs(type="cluster"))

    # Node Group - production ready
    node_count = int(pulumi.Config().get("node_count") or "3")
    instance_type = pulumi.Config().get("instance_type") or "t3.xlarge"
    
    node_group = aws.eks.NodeGroup("primary-nodes",
        cluster_name=cluster.name,
        node_role_arn=node_role.arn,
        subnet_ids=network["subnet_ids"],
        instance_types=[instance_type],
        capacity_type="ON_DEMAND",
        scaling_config=aws.eks.NodeGroupScalingConfigArgs(
            desired_size=node_count,
            max_size=node_count + 2,
            min_size=1,
        ),
        disk_size=100,
        tags={"Name": f"{cluster_name}-primary-nodes"})

    return {
        "cluster": cluster,
        "node_role": node_role,
        "cluster_name": cluster_name,
    }
