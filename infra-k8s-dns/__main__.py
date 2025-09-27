import pulumi
import pulumi_aws as aws
import json

config = pulumi.Config()
domain = config.require("domain")
parent_zone_id = config.require("parentZoneId")
cluster_oidc_issuer = config.require("clusterOidcIssuer")
enable_dnssec = config.get_bool("enable_dnssec") if config.get("enable_dnssec") is not None else False

# Create subdomain zone
sub_zone = aws.route53.Zone("eks-subdomain",
    name=f"k8s.{domain}",
    tags={
        "Environment": "production",
        "Purpose": "eks-dns"
    }
)

caller_identity = aws.get_caller_identity()

dnssec_kms_key = None
ksk = None
dnssec_enable = None

if enable_dnssec:
    dnssec_kms_key = aws.kms.Key(
        "eks-dnssec-kms-key",
        description=f"DNSSEC signing key for k8s.{domain}",
        key_usage="SIGN_VERIFY",
        customer_master_key_spec="ECC_NIST_P256",
        deletion_window_in_days=7,
        policy=pulumi.Output.all(caller_identity.account_id, sub_zone.zone_id).apply(lambda args: json.dumps({
            "Version": "2012-10-17",
            "Id": "route53-dnssec-key-policy",
            "Statement": [
                {
                    "Sid": "EnableRootPermissions",
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{args[0]}:root"},
                    "Action": "kms:*",
                    "Resource": "*"
                },
                {
                    "Sid": "AllowRoute53DNSSECService",
                    "Effect": "Allow",
                    "Principal": {"Service": "dnssec-route53.amazonaws.com"},
                    "Action": [
                        "kms:DescribeKey",
                        "kms:GetPublicKey",
                        "kms:Sign"
                    ],
                    "Resource": "*"
                }
            ]
        })),
        tags={
            "Environment": "production",
            "Purpose": "dnssec"
        }
    )

    aws.kms.Alias(
        "eks-dnssec-kms-alias",
        name=f"alias/eks-dnssec-k8s-{domain.replace('.', '-')}",
        target_key_id=dnssec_kms_key.key_id
    )

    ksk = aws.route53.KeySigningKey(
        "eks-dnssec-ksk",
        hosted_zone_id=sub_zone.zone_id,
        key_management_service_arn=dnssec_kms_key.arn,
        name="ksk1",
        status="ACTIVE",
        opts=pulumi.ResourceOptions(depends_on=[dnssec_kms_key])
    )

    dnssec_enable = aws.route53.HostedZoneDnsSec(
        "eks-dnssec-enable",
        hosted_zone_id=sub_zone.zone_id,
        opts=pulumi.ResourceOptions(depends_on=[ksk])
    )

# Delegate subdomain
aws.route53.Record("subdomain-delegation",
    zone_id=parent_zone_id,
    name=f"eks.{domain}",
    type="NS",
    ttl=300,
    records=sub_zone.name_servers
)

# IAM policy for subdomain-only access
dns_policy = aws.iam.Policy("eks-dns-policy",
    policy=sub_zone.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["route53:GetHostedZone", "route53:ListResourceRecordSets"],
                "Resource": arn
            },
            {
                "Effect": "Allow",
                "Action": "route53:ChangeResourceRecordSets",
                "Resource": arn,
                "Condition": {
                    "ForAllValues:StringEquals": {
                        "route53:RRType": ["A", "AAAA", "CNAME", "TXT"]
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": ["route53:ListHostedZones", "route53:GetChange"],
                "Resource": "*"
            }
        ]
    }))
)

# (caller_identity already retrieved above)

# IRSA role
dns_role = aws.iam.Role("eks-dns-role",
    assume_role_policy=pulumi.Output.all(caller_identity.account_id, cluster_oidc_issuer).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{args[0]}:oidc-provider/{args[1].replace('https://', '')}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{args[1].replace('https://', '')}:sub": "system:serviceaccount:kube-system:external-dns",
                        f"{args[1].replace('https://', '')}:aud": "sts.amazonaws.com"
                    }
                }
            }]
        })
    )
)

aws.iam.RolePolicyAttachment("dns-policy-attachment",
    role=dns_role.name,
    policy_arn=dns_policy.arn
)

# Exports
pulumi.export("subdomain_zone_id", sub_zone.zone_id)
pulumi.export("subdomain_name_servers", sub_zone.name_servers)
pulumi.export("dns_role_arn", dns_role.arn)
pulumi.export("subdomain_zone_name", sub_zone.name)
if enable_dnssec and ksk is not None:
    pulumi.export("dnssec_ds_record", ksk.ds_record)
    pulumi.export("dnssec_kms_key_arn", dnssec_kms_key.arn if dnssec_kms_key else None)
else:
    pulumi.export("dnssec_ds_record", None)
    pulumi.export("dnssec_kms_key_arn", None)