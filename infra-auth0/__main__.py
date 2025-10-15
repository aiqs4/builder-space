"""
Auth0 Configuration for OAuth2 Proxy Integration
Manages Auth0 tenant, application, and Google social connection
Integrates with AWS Route53 for custom domain verification

Supports multiple custom domains:
- auth.tekanya.services
- auth.amano.services
- auth.lightsphere.space
- auth.sosolola.cloud
"""

import json
import pulumi
import pulumi_auth0 as auth0
import pulumi_aws as aws

config = pulumi.Config()

# Configuration - Primary domain for initial setup
primary_domain = config.get("primary_domain") or "sosolola.cloud"
auth_subdomain = config.get("auth_subdomain") or "auth"
admin_email = config.get("admin_email") or "sascha.dewald@gmail.com"

# All domains to configure
all_domains = config.get_object("domains") or [
    "amano.services",
    "tekanya.services", 
    "lightsphere.space",
    "sosolola.cloud"
]

# Auth0 custom domain limitation: only 1 allowed on free/basic plan
# We'll create DNS for ALL domains, but only register 1 with Auth0
auth0_custom_domain = primary_domain  # Only this one gets Auth0 custom domain
dns_domains = all_domains  # All get DNS records

# Email lists for different user types
email_config = {
    "admin_emails": [admin_email],
    "member_emails": config.get_object("member_emails") or [
        "sascha.dewald@gmail.com",
        "team@amano.services",
        "support@tekanya.services"
    ],
    "customer_domains": config.get_object("customer_domains") or [
        "gmail.com",
        "outlook.com", 
        "hotmail.com",
        "yahoo.com",
        "icloud.com"
    ],
    "allowed_domains": config.get_object("allowed_domains") or [
        "amano.services",
        "tekanya.services",
        "lightsphere.space",
        "sosolola.cloud"
    ]
}

# Build auth domains and callback URLs for ALL domains
all_auth_domains = [f"{auth_subdomain}.{domain}" for domain in all_domains]

# Internal subdomains
internal_subdomains = ["k8s.lightsphere.space"]

# All callback URLs (Auth0 supports multiple)
callback_urls = []
logout_urls = []
web_origins = []

# Add callbacks for all auth.* domains
for domain in all_domains:
    auth_domain = f"{auth_subdomain}.{domain}"
    callback_urls.append(f"https://{auth_domain}/oauth2/callback")
    logout_urls.append(f"https://{auth_domain}")
    web_origins.append(f"https://{auth_domain}")

# Add callbacks for internal subdomains  
for subdomain in internal_subdomains:
    callback_urls.append(f"https://{auth_subdomain}.{subdomain}/oauth2/callback")
    logout_urls.append(f"https://{auth_subdomain}.{subdomain}")
    web_origins.append(f"https://{auth_subdomain}.{subdomain}")

# ============================================================================
# Auth0 Application for OAuth2 Proxy
# ============================================================================

app = auth0.Client("oauth2-proxy",
    name="OAuth2 Proxy",
    description="OAuth2 Proxy for Kubernetes Ingress Authentication",
    app_type="regular_web",
    
    # OAuth2 settings
    callbacks=callback_urls,
    allowed_logout_urls=logout_urls,
    web_origins=web_origins,
    
    # Token settings
    oidc_conformant=True,
    jwt_configuration={
        "alg": "RS256",
        "lifetime_in_seconds": 36000,  # 10 hours
    },
    
    # Grant types
    grant_types=[
        "authorization_code",
        "refresh_token",
    ],
    
    # Refresh token settings
    refresh_token={
        "rotation_type": "rotating",
        "expiration_type": "expiring",
        "leeway": 0,
        "token_lifetime": 2592000,  # 30 days
        "idle_token_lifetime": 1296000,  # 15 days
    },
)

# ============================================================================
# Google Social Connection
# Uses Auth0's built-in Google OAuth integration
# No need for custom Google credentials unless you want custom branding
# ============================================================================

# Note: The existing google-oauth2 connection (con_bwWBaN9ZjAi40ase) will be used
# We're just ensuring it's enabled for our OAuth2 Proxy application
# If you want to manage it with Pulumi, uncomment below and import existing resource

# google_connection = auth0.Connection("google-oauth2",
#     name="google-oauth2", 
#     strategy="google-oauth2",
#     enabled_clients=[app.id],
#     opts=pulumi.ResourceOptions(import_="con_bwWBaN9ZjAi40ase")
# )

# ============================================================================
# Email Provider Configuration (Optional)
# Configure AWS SES for custom email templates and notifications
# ============================================================================

# Email provider for custom notifications (uncomment if needed)
# email_provider = auth0.EmailProvider("ses",
#     name="ses",
#     enabled=True,
#     default_from_address=f"noreply@{primary_domain}",
#     credentials={
#         "access_key_id": config.require_secret("aws_ses_access_key_id"),
#         "secret_access_key": config.require_secret("aws_ses_secret_access_key"),
#         "region": config.get("aws_region") or "af-south-1",
#     },
# )

# ============================================================================
# User Roles and Management
# ============================================================================

# Admin role for privileged users
admin_role = auth0.Role("admin-role",
    name="Administrator",
    description="Full administrative access to all applications and services",
)

# Member role for team members
member_role = auth0.Role("member-role", 
    name="Team Member",
    description="Access to internal tools and services",
)

# Customer role for external users
customer_role = auth0.Role("customer-role",
    name="Customer",
    description="Access to customer-facing applications",
)

# ============================================================================
# Custom Domains with Route53 Integration
# ============================================================================

# Auth0 custom domains require verification via TXT records
# We'll create custom domains and corresponding Route53 records

# ============================================================================
# Route53 DNS Records for ALL domains
# Create auth.* DNS records for all domains, even if Auth0 limits custom domains
# ============================================================================

route53_records = {}

# Create DNS records for ALL domains
for domain in dns_domains:
    # Get the Route53 hosted zone for this domain
    zone = aws.route53.get_zone(name=f"{domain}.")
    
    # Create CNAME record pointing to Auth0 
    # All point to the same Auth0 custom domain (sosolola.cloud) for now
    cname_record = aws.route53.Record(f"auth-cname-{domain.replace('.', '-')}",
        zone_id=zone.zone_id,
        name=auth_subdomain,
        type="CNAME", 
        ttl=300,
        records=["tekanya-cd-edaow2ksjrrcfbe8.edge.tenants.eu.auth0.com"],
    )
    
    route53_records[domain] = cname_record

# ============================================================================
# Auth0 Custom Domain (only ONE allowed on free plan)
# ============================================================================

# Only create Auth0 custom domain for the primary domain  
custom_domain = auth0.CustomDomain(f"auth-{auth0_custom_domain.replace('.', '-')}",
    domain=f"{auth_subdomain}.{auth0_custom_domain}",
    type="auth0_managed_certs",
    opts=pulumi.ResourceOptions(
        import_="cd_edaOW2ksJRRcFBE8" if auth0_custom_domain == "sosolola.cloud" else None
    )
)

# ============================================================================
# Outputs
# ============================================================================

# Note: Auth0 tenant domain for authentication
pulumi.export("auth0_tenant_domain", config.get("auth0:domain") or "tekanya.eu.auth0.com")
pulumi.export("auth0_client_id", app.client_id)
# Note: client_secret is sensitive and only available through Pulumi config or Auth0 dashboard
# Export a placeholder - actual secret should be retrieved from Auth0 dashboard
pulumi.export("auth0_client_secret_note", "Retrieve from Auth0 Dashboard > Applications > OAuth2 Proxy > Settings")
pulumi.export("auth0_application_id", app.id)
pulumi.export("google_connection", "Using Auth0's built-in Google OAuth (con_bwWBaN9ZjAi40ase)")

# Export custom domain information
pulumi.export("custom_domains", all_auth_domains)
pulumi.export("custom_domain_status", {
    auth0_custom_domain: custom_domain.status
})
pulumi.export("custom_domain_origins", {
    auth0_custom_domain: custom_domain.origin_domain_name
})
pulumi.export("route53_cnames", {
    domain: route53_records[domain].fqdn
    for domain in dns_domains
})

# Export for use in infra-k8s stack
pulumi.export("oauth2_proxy_config", {
    "tenant_domain": config.get("auth0:domain") or "tekanya.eu.auth0.com",
    "client_id": app.client_id,
    "redirect_urls": callback_urls,
    "custom_domains": all_auth_domains,
})

# Instructions for next steps
pulumi.export("next_steps", pulumi.Output.all(
    client_id=app.client_id,
    app_id=app.id,
    domains=all_auth_domains,
).apply(lambda args: f"""
Auth0 Configuration Complete!

Custom Domains Configured:
{chr(10).join(f"  - https://{d}" for d in args['domains'])}

Next Steps:

1. Get Client Secret from Auth0 Dashboard:
   - Go to: https://manage.auth0.com/dashboard/
   - Navigate to: Applications > OAuth2 Proxy > Settings
   - Copy the Client Secret (you'll need this for step 2)

2. Verify Custom Domains in Auth0:
   - Go to Auth0 Dashboard > Branding > Custom Domains
   - Wait for all domains to show "Ready" status
   - DNS records have been automatically created in Route53

3. Update infra-k8s stack configuration:
   cd ../infra-k8s
   pulumi config set auth0_tenant_domain tekanya.eu.auth0.com
   pulumi config set --secret auth0_client_id {args['client_id']}
   pulumi config set --secret auth0_client_secret <paste_from_step_1>
   pulumi up

4. Update OAuth2 Proxy ArgoCD values:
   Edit: builder-space-argocd/environments/prod/oauth2-proxy/values.yaml
   Set the following values:
   - Client ID: {args['client_id']}
   - Client Secret: <from step 1>
   - Auth0 Domain: tekanya.eu.auth0.com

5. Deploy OAuth2 Proxy for each domain:
   cd ../../builder-space-argocd
   kubectl apply -f applications/infrastructure/oauth2-proxy/application.yaml

6. Test authentication on any domain:
   Open: https://{args['domains'][0]}
   Login with: Your Gmail account

Note: Custom domains require Auth0 Professional plan or higher.
If using free tier, use the default tekanya.eu.auth0.com domain instead.
"""))
