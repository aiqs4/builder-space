#!/bin/bash
set -e

# Get Zone IDs
ZONE_AMANO=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='amano.services.'].Id" --output text | cut -d'/' -f3)
ZONE_LIGHT=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='lightsphere.space.'].Id" --output text | cut -d'/' -f3)
ZONE_SOSO=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='sosolola.cloud.'].Id" --output text | cut -d'/' -f3)

echo "Zone IDs: $ZONE_AMANO, $ZONE_LIGHT, $ZONE_SOSO"

# Import MX records
pulumi import --yes aws:route53/record:Record mx-amano-services ${ZONE_AMANO}_amano.services._MX
pulumi import --yes aws:route53/record:Record mx-lightsphere-space ${ZONE_LIGHT}_lightsphere.space._MX
pulumi import --yes aws:route53/record:Record mx-sosolola-cloud ${ZONE_SOSO}_sosolola.cloud._MX

# Import SPF records
pulumi import --yes aws:route53/record:Record spf-amano-services ${ZONE_AMANO}_amano.services._TXT
pulumi import --yes aws:route53/record:Record spf-lightsphere-space ${ZONE_LIGHT}_lightsphere.space._TXT
pulumi import --yes aws:route53/record:Record spf-sosolola-cloud ${ZONE_SOSO}_sosolola.cloud._TXT

# Import DMARC records
pulumi import --yes aws:route53/record:Record dmarc-amano-services ${ZONE_AMANO}__dmarc.amano.services._TXT
pulumi import --yes aws:route53/record:Record dmarc-lightsphere-space ${ZONE_LIGHT}__dmarc.lightsphere.space._TXT
pulumi import --yes aws:route53/record:Record dmarc-sosolola-cloud ${ZONE_SOSO}__dmarc.sosolola.cloud._TXT

# Import Autodiscover records
pulumi import --yes aws:route53/record:Record autodiscover-amano-services ${ZONE_AMANO}_autodiscover.amano.services._CNAME
pulumi import --yes aws:route53/record:Record autodiscover-lightsphere-space ${ZONE_LIGHT}_autodiscover.lightsphere.space._CNAME
pulumi import --yes aws:route53/record:Record autodiscover-sosolola-cloud ${ZONE_SOSO}_autodiscover.sosolola.cloud._CNAME

# Import SES verification records
pulumi import --yes aws:route53/record:Record ses-verification-amano-services ${ZONE_AMANO}__amazonses.amano.services._TXT
pulumi import --yes aws:route53/record:Record ses-verification-lightsphere-space ${ZONE_LIGHT}__amazonses.lightsphere.space._TXT
pulumi import --yes aws:route53/record:Record ses-verification-sosolola-cloud ${ZONE_SOSO}__amazonses.sosolola.cloud._TXT

echo "✓ All resources imported!"
