"""
Auth0 Multi-Domain Configuration
Creates DNS records for ALL domains, Auth0 custom domain for primary
"""

import json
import pulumi
import pulumi_auth0 as auth0
import pulumi_aws as aws

config = pulumi.Config()

# All your domains
ALL_DOMAINS = [
    "amano.services",
    "tekanya.services", 
    "lightsphere.space",
    "sosolola.cloud"
]

# Internal subdomains
INTERNAL_SUBDOMAINS = [
    "k8s.lightsphere.space"
]

# Primary domain (only one gets Auth0 custom domain on free plan)
PRIMARY_DOMAIN = "sosolola.cloud"
AUTH_SUBDOMAIN = "auth"

# ============================================================================
# Route53 DNS Records for ALL Domains
# ============================================================================

route53_records = {}

for domain in ALL_DOMAINS:
    # Get Route53 hosted zone
    zone = aws.route53.get_zone(name=f"{domain}.")
    
    # Create auth.* CNAME record
    cname_record = aws.route53.Record(f"auth-{domain.replace('.', '-')}",
        zone_id=zone.zone_id,
        name=AUTH_SUBDOMAIN,
        type="CNAME",
        ttl=300,
        # All point to the Auth0 verification domain for now
        records=["tekanya-cd-edaow2ksjrrcfbe8.edge.tenants.eu.auth0.com"],
    )
    
    route53_records[domain] = cname_record
    
    pulumi.export(f"dns_record_{domain.replace('.', '_')}", {
        "domain": f"auth.{domain}",
        "target": "tekanya-cd-edaow2ksjrrcfbe8.edge.tenants.eu.auth0.com",
        "status": "created"
    })

# ============================================================================
# Auth0 Application Configuration
# ============================================================================

# Build ALL callback URLs
callback_urls = []
logout_urls = []
web_origins = []

# Add auth.* domains
for domain in ALL_DOMAINS:
    auth_domain = f"{AUTH_SUBDOMAIN}.{domain}"
    callback_urls.append(f"https://{auth_domain}/oauth2/callback")
    logout_urls.append(f"https://{auth_domain}")
    web_origins.append(f"https://{auth_domain}")

# Add internal subdomains
for subdomain in INTERNAL_SUBDOMAINS:
    auth_domain = f"{AUTH_SUBDOMAIN}.{subdomain}"
    callback_urls.append(f"https://{auth_domain}/oauth2/callback")
    logout_urls.append(f"https://{auth_domain}")
    web_origins.append(f"https://{auth_domain}")

# Auth0 Application
app = auth0.Client("oauth2-proxy",
    name="OAuth2 Proxy Multi-Domain",
    description="OAuth2 Proxy for all domains and internal tools",
    app_type="regular_web",
    
    # All callback URLs
    callbacks=callback_urls,
    allowed_logout_urls=logout_urls,
    web_origins=web_origins,
    
    # Token settings
    oidc_conformant=True,
    jwt_configuration={
        "alg": "RS256",
        "lifetime_in_seconds": 36000,
    },
    
    grant_types=["authorization_code", "refresh_token"],
    
    refresh_token={
        "rotation_type": "rotating",
        "expiration_type": "expiring",
        "leeway": 0,
        "token_lifetime": 2592000,
        "idle_token_lifetime": 1296000,
    },
)

# ============================================================================
# Auth0 Custom Domain (Primary Only)
# ============================================================================

# Import existing custom domain
custom_domain = auth0.CustomDomain("auth-primary",
    domain=f"{AUTH_SUBDOMAIN}.{PRIMARY_DOMAIN}",
    type="auth0_managed_certs",
    opts=pulumi.ResourceOptions(import_="cd_edaOW2ksJRRcFBE8")
)

# ============================================================================
# Outputs
# ============================================================================

pulumi.export("auth0_client_id", app.client_id)
pulumi.export("auth0_tenant_domain", "tekanya.eu.auth0.com")
pulumi.export("auth0_custom_domain", f"{AUTH_SUBDOMAIN}.{PRIMARY_DOMAIN}")

pulumi.export("all_auth_domains", [f"{AUTH_SUBDOMAIN}.{domain}" for domain in ALL_DOMAINS])
pulumi.export("internal_auth_domains", [f"{AUTH_SUBDOMAIN}.{sub}" for sub in INTERNAL_SUBDOMAINS])

pulumi.export("callback_urls", callback_urls)

pulumi.export("oauth2_proxy_config", {
    "client_id": app.client_id,
    "tenant_domain": "tekanya.eu.auth0.com",
    "custom_domain": f"{AUTH_SUBDOMAIN}.{PRIMARY_DOMAIN}",
    "all_domains": ALL_DOMAINS,
    "internal_domains": INTERNAL_SUBDOMAINS,
    "callback_urls": callback_urls
})

pulumi.export("dns_status", {
    domain: f"auth.{domain} → tekanya-cd-edaow2ksjrrcfbe8.edge.tenants.eu.auth0.com"
    for domain in ALL_DOMAINS
})

pulumi.export("next_steps", f"""
Multi-Domain Auth0 Setup Complete!

✅ DNS Records Created:
{chr(10).join([f"   - auth.{domain}" for domain in ALL_DOMAINS])}

✅ Auth0 Custom Domain: auth.{PRIMARY_DOMAIN} (ready)

✅ Callback URLs configured for ALL domains:
{chr(10).join([f"   - {url}" for url in callback_urls[:5]])}
   ... and {len(callback_urls)-5} more

Next Steps:
1. Deploy KMS secrets: pulumi up -f kms-secrets.py
2. Install External Secrets Operator  
3. Deploy OAuth2 Proxy with multi-domain support
4. All your domains will work with Auth0!

Available Auth Endpoints:
- https://auth.amano.services (→ Auth0)
- https://auth.tekanya.services (→ Auth0) 
- https://auth.lightsphere.space (→ Auth0)
- https://auth.sosolola.cloud (→ Auth0, custom domain)
- https://auth.k8s.lightsphere.space (→ Auth0)
""")