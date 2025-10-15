# AWS WorkMail & SES Email Infrastructure

This stack manages email infrastructure for all domains using AWS WorkMail and SES.

## Problem Solved

**Issue**: Only the primary domain (tekanya.awsapps.com) was showing in WorkMail console, even though all domains were registered in the organization.

**Root Cause**: `tekanya.services` was missing ALL required DNS records:
- No MX record (mail routing)
- No DKIM records (email signing)
- No SPF record (sender authentication)
- No DMARC record (email policy)
- No autodiscover record (client configuration)

Without these DNS records, WorkMail cannot route emails, so the domain doesn't appear as usable in the console.

## What This Stack Does

1. **SES Domain Verification**
   - Creates/imports SES domain identities for all domains
   - Creates DNS TXT records for domain verification
   - Enables DKIM signing with 3 CNAME records per domain

2. **WorkMail DNS Configuration**
   - Creates MX records pointing to AWS WorkMail
   - Creates autodiscover CNAME for email client configuration
   - Creates SPF TXT records for sender authentication
   - Creates DMARC TXT records for email policy

3. **Email Infrastructure**
   - Configures SES configuration sets for tracking
   - Ensures all domains are properly registered in WorkMail
   - Manages DNS records via Route53

## Domains Configured

- `amano.services`
- `tekanya.services` (this was the problematic one!)
- `lightsphere.space`
- `sosolola.cloud`

## Quick Setup

```bash
cd infra-email
./setup-email.sh
```

Or manually:

```bash
cd infra-email
pip install -r requirements.txt
pulumi stack init email
pulumi up
```

## Verification

After deployment, wait 5-10 minutes for DNS propagation, then verify:

### Check DNS Records
```bash
# MX record
dig MX tekanya.services @8.8.8.8

# SES verification
dig TXT _amazonses.tekanya.services @8.8.8.8

# DKIM records
dig CNAME <token>._domainkey.tekanya.services @8.8.8.8
```

### Check SES Status
```bash
aws ses get-identity-verification-attributes --region us-east-1 \
  --identities amano.services tekanya.services lightsphere.space sosolola.cloud
```

### Check WorkMail Domains
```bash
# List all domains
aws workmail list-mail-domains \
  --organization-id m-6e08a2a35de44418ac00d3daa51bf5f2 \
  --region us-east-1

# Check specific domain
aws workmail get-mail-domain \
  --organization-id m-6e08a2a35de44418ac00d3daa51bf5f2 \
  --domain-name tekanya.services \
  --region us-east-1
```

## Using WorkMail

### Access Web Console
```
https://tekanya.awsapps.com/mail
```

### Add Email Aliases

1. Go to AWS WorkMail Console
2. Select organization: `tekanya`
3. Go to Users
4. Select your user
5. Click "Add email alias"
6. Add aliases for each domain:
   - `user@amano.services`
   - `user@tekanya.services`
   - `user@lightsphere.space`
   - `user@sosolola.cloud`

### Send Test Email
```bash
aws ses send-email --region us-east-1 \
  --from you@sosolola.cloud \
  --destination ToAddresses=your.email@gmail.com \
  --message Subject={Data="Test"},Body={Text={Data="Test email"}}
```

## DNS Records Created

For each domain, the following records are created:

| Record Type | Name | Value | Purpose |
|-------------|------|-------|---------|
| MX | @ | `10 inbound-smtp.us-east-1.amazonaws.com` | Mail routing |
| TXT | _amazonses | `<verification-token>` | Domain verification |
| CNAME | <token1>._domainkey | `<token1>.dkim.amazonses.com` | DKIM signing |
| CNAME | <token2>._domainkey | `<token2>.dkim.amazonses.com` | DKIM signing |
| CNAME | <token3>._domainkey | `<token3>.dkim.amazonses.com` | DKIM signing |
| TXT | @ | `v=spf1 include:amazonses.com ~all` | Sender authentication |
| TXT | _dmarc | `v=DMARC1;p=quarantine;pct=100;fo=1` | Email policy |
| CNAME | autodiscover | `autodiscover.mail.us-east-1.awsapps.com` | Client config |

## Troubleshooting

### Domain Not Showing in WorkMail Console

**Cause**: DNS records not propagated or verification pending

**Solution**:
1. Wait 10 minutes for DNS propagation
2. Refresh WorkMail console
3. Verify DNS records with `dig` commands above
4. Check verification status with AWS CLI

### DKIM Not Verified

**Cause**: CNAME records not created or not propagated

**Solution**:
1. Check Route53 to ensure 3 DKIM CNAME records exist
2. Wait for DNS propagation
3. Verify with: `dig CNAME <token>._domainkey.domain.com`

### Cannot Send Emails

**Cause**: SES sandbox mode (for new accounts)

**Solution**:
1. Request production access: https://console.aws.amazon.com/ses/
2. Or verify recipient email addresses in SES console

## Configuration

Edit `Pulumi.email.yaml` to customize:

```yaml
config:
  infra-email:workmail_org_id: m-6e08a2a35de44418ac00d3daa51bf5f2
  infra-email:workmail_alias: tekanya
  infra-email:primary_domain: sosolola.cloud
  infra-email:domains:
    - amano.services
    - tekanya.services
    - lightsphere.space
    - sosolola.cloud
```

## Stack Outputs

View deployment information:
```bash
pulumi stack output
```

Key outputs:
- `workmail_organization`: Organization details and console URL
- `domains_configured`: List of configured domains
- `ses_domains`: SES verification tokens
- `dns_records_created`: Summary of DNS records
- `next_steps`: Post-deployment instructions

## Cost Estimate

- **WorkMail**: $4/user/month
- **SES**: $0.10 per 1,000 emails sent
- **Route53**: $0.50/hosted zone/month (already have zones)
- **Total**: ~$4-5/month for single user + minimal email volume

## Related Stacks

- `infra-auth0`: Authentication with Auth0 (uses same domains)
- `infra-k8s-dns`: DNS management for Kubernetes (subdomain delegation)

## References

- [AWS WorkMail Documentation](https://docs.aws.amazon.com/workmail/)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [Pulumi AWS Provider](https://www.pulumi.com/registry/packages/aws/)
