"""
AWS KMS Secret Management for Auth0 OAuth2 Proxy
Creates secrets in AWS KMS and configures External Secrets Operator
"""

import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s
import json
import base64

config = pulumi.Config()

# ============================================================================
# AWS KMS Key for Auth0 Secrets
# ============================================================================

kms_key = aws.kms.Key("auth0-secrets-key",
    description="KMS key for Auth0 OAuth2 Proxy secrets",
    key_usage="ENCRYPT_DECRYPT",
    key_spec="SYMMETRIC_DEFAULT",
)

kms_alias = aws.kms.Alias("auth0-secrets-key-alias",
    name="alias/auth0-oauth2-proxy",
    target_key_id=kms_key.key_id,
)

# ============================================================================
# Store Auth0 Secrets in AWS Secrets Manager
# ============================================================================

# Auth0 Client Secret (you need to get this from Auth0 dashboard)
auth0_client_secret = config.get_secret("auth0_client_secret") or "REPLACE_WITH_AUTH0_CLIENT_SECRET"

# Generate cookie secret
import secrets
cookie_secret = secrets.token_urlsafe(32)

# Create secrets in AWS Secrets Manager
oauth2_secrets = aws.secretsmanager.Secret("oauth2-proxy-secrets",
    name="oauth2-proxy-auth0",
    description="Auth0 OAuth2 Proxy secrets",
    kms_key_id=kms_key.arn,
)

oauth2_secret_version = aws.secretsmanager.SecretVersion("oauth2-proxy-secrets-version",
    secret_id=oauth2_secrets.id,
    secret_string=pulumi.Output.all(
        client_id="aPEUWwTH91khPenCjJBEzyZ0wyzV2dZh",
        client_secret=auth0_client_secret,
        cookie_secret=cookie_secret
    ).apply(lambda secrets: json.dumps({
        "client-id": secrets["client_id"],
        "client-secret": secrets["client_secret"], 
        "cookie-secret": secrets["cookie_secret"]
    }))
)

# ============================================================================
# IAM Role for External Secrets Operator
# ============================================================================

# Create IAM role for External Secrets Operator
external_secrets_role = aws.iam.Role("external-secrets-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Effect": "Allow",
            "Principal": {
                "Federated": f"arn:aws:iam::{aws.get_caller_identity().account_id}:oidc-provider/oidc.eks.{aws.get_region().name}.amazonaws.com/id/OIDC_PROVIDER_ID"
            },
            "Condition": {
                "StringEquals": {
                    f"oidc.eks.{aws.get_region().name}.amazonaws.com/id/OIDC_PROVIDER_ID:sub": "system:serviceaccount:external-secrets:external-secrets",
                    f"oidc.eks.{aws.get_region().name}.amazonaws.com/id/OIDC_PROVIDER_ID:aud": "sts.amazonaws.com"
                }
            }
        }]
    })
)

# Attach policy to allow reading secrets
external_secrets_policy = aws.iam.RolePolicy("external-secrets-policy",
    role=external_secrets_role.id,
    policy=pulumi.Output.all(
        secrets_arn=oauth2_secrets.arn,
        kms_arn=kms_key.arn
    ).apply(lambda args: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                "Resource": args["secrets_arn"]
            },
            {
                "Effect": "Allow", 
                "Action": [
                    "kms:Decrypt"
                ],
                "Resource": args["kms_arn"]
            }
        ]
    }))
)

# ============================================================================
# Kubernetes External Secrets Configuration
# ============================================================================

# External Secrets Operator namespace
external_secrets_ns = k8s.core.v1.Namespace("external-secrets",
    metadata={"name": "external-secrets"}
)

# Service Account for External Secrets Operator
external_secrets_sa = k8s.core.v1.ServiceAccount("external-secrets-sa",
    metadata={
        "name": "external-secrets", 
        "namespace": "external-secrets",
        "annotations": {
            "eks.amazonaws.com/role-arn": external_secrets_role.arn
        }
    }
)

# SecretStore for AWS Secrets Manager
secret_store = k8s.apiextensions.CustomResource("aws-secret-store",
    api_version="external-secrets.io/v1beta1",
    kind="SecretStore",
    metadata={
        "name": "aws-secrets-manager",
        "namespace": "oauth2-proxy"
    },
    spec={
        "provider": {
            "aws": {
                "service": "SecretsManager",
                "region": aws.get_region().name,
                "auth": {
                    "serviceAccount": {
                        "name": "external-secrets"
                    }
                }
            }
        }
    }
)

# ExternalSecret to pull from AWS and create K8s secret
external_secret = k8s.apiextensions.CustomResource("oauth2-proxy-external-secret",
    api_version="external-secrets.io/v1beta1", 
    kind="ExternalSecret",
    metadata={
        "name": "oauth2-proxy-secrets",
        "namespace": "oauth2-proxy"
    },
    spec={
        "refreshInterval": "1h",
        "secretStoreRef": {
            "name": "aws-secrets-manager",
            "kind": "SecretStore"
        },
        "target": {
            "name": "oauth2-proxy",
            "creationPolicy": "Owner"
        },
        "data": [
            {
                "secretKey": "client-id",
                "remoteRef": {
                    "key": "oauth2-proxy-auth0",
                    "property": "client-id"
                }
            },
            {
                "secretKey": "client-secret", 
                "remoteRef": {
                    "key": "oauth2-proxy-auth0",
                    "property": "client-secret"
                }
            },
            {
                "secretKey": "cookie-secret",
                "remoteRef": {
                    "key": "oauth2-proxy-auth0", 
                    "property": "cookie-secret"
                }
            }
        ]
    }
)

# ============================================================================
# Outputs
# ============================================================================

pulumi.export("kms_key_id", kms_key.key_id)
pulumi.export("kms_key_arn", kms_key.arn) 
pulumi.export("secrets_manager_arn", oauth2_secrets.arn)
pulumi.export("external_secrets_role_arn", external_secrets_role.arn)
pulumi.export("cookie_secret_generated", cookie_secret)

pulumi.export("setup_instructions", f"""
AWS KMS + External Secrets Setup Complete!

Next Steps:
1. Set Auth0 client secret:
   pulumi config set --secret auth0_client_secret YOUR_AUTH0_CLIENT_SECRET
   pulumi up

2. Install External Secrets Operator:
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace

3. Verify secret creation:
   kubectl get secrets -n oauth2-proxy
   kubectl describe externalsecret oauth2-proxy-secrets -n oauth2-proxy

4. Deploy OAuth2 Proxy with secret reference (already configured)

Generated cookie secret (stored in AWS): {cookie_secret}
KMS Key: {kms_key.key_id}
Secrets Manager: oauth2-proxy-auth0
""")