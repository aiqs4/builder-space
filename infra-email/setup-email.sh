#!/bin/bash
set -e

echo "======================================"
echo "AWS WorkMail & SES Email Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}This script will:${NC}"
echo "  1. Create/update SES domain identities"
echo "  2. Create all required DNS records (MX, DKIM, SPF, DMARC, autodiscover)"
echo "  3. Ensure all domains are registered in WorkMail"
echo "  4. Verify domain ownership and DKIM"
echo ""

# Check if Pulumi is installed
if ! command -v pulumi &> /dev/null; then
    echo -e "${RED}Error: Pulumi is not installed${NC}"
    echo "Install from: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

# Get AWS account info
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"  # WorkMail requires us-east-1

echo -e "${GREEN}AWS Account ID: ${ACCOUNT_ID}${NC}"
echo -e "${GREEN}AWS Region: ${AWS_REGION}${NC}"
echo ""

# Check Pulumi passphrase
if [ -z "$PULUMI_CONFIG_PASSPHRASE" ]; then
    echo -e "${YELLOW}Enter Pulumi passphrase:${NC}"
    read -s PULUMI_CONFIG_PASSPHRASE
    export PULUMI_CONFIG_PASSPHRASE
    echo ""
fi

# Navigate to infra-email directory
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -q -r requirements.txt

echo ""
echo -e "${YELLOW}Initializing Pulumi stack...${NC}"

# Initialize stack if it doesn't exist
if ! pulumi stack select email 2>/dev/null; then
    echo "Creating new stack: email"
    pulumi stack init email
fi

echo ""
echo -e "${GREEN}Current configuration:${NC}"
pulumi config

echo ""
echo -e "${YELLOW}Ready to deploy email infrastructure${NC}"
echo -e "${YELLOW}This will:${NC}"
echo "  - Verify/import existing SES domains"
echo "  - Create missing DNS records for tekanya.services"
echo "  - Ensure all domains work with WorkMail"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}Deploying email infrastructure...${NC}"
    pulumi up --yes
    
    echo ""
    echo -e "${GREEN}✓ Deployment complete!${NC}"
    echo ""
    
    # Show next steps
    echo -e "${YELLOW}Next Steps:${NC}"
    echo ""
    echo "1. Wait 5-10 minutes for DNS propagation"
    echo ""
    echo "2. Verify DNS records:"
    echo "   dig MX tekanya.services @8.8.8.8"
    echo "   dig TXT _amazonses.tekanya.services @8.8.8.8"
    echo ""
    echo "3. Check SES verification status:"
    echo "   aws ses get-identity-verification-attributes --region us-east-1 \\"
    echo "     --identities amano.services tekanya.services lightsphere.space sosolola.cloud"
    echo ""
    echo "4. Verify WorkMail domains:"
    echo "   aws workmail list-mail-domains \\"
    echo "     --organization-id m-6e08a2a35de44418ac00d3daa51bf5f2 \\"
    echo "     --region us-east-1"
    echo ""
    echo "5. Check domain details:"
    echo "   aws workmail get-mail-domain \\"
    echo "     --organization-id m-6e08a2a35de44418ac00d3daa51bf5f2 \\"
    echo "     --domain-name tekanya.services \\"
    echo "     --region us-east-1"
    echo ""
    echo "6. Access WorkMail Console:"
    echo "   https://tekanya.awsapps.com/mail"
    echo ""
    echo "7. Add email aliases for your user in WorkMail Console"
    echo ""
    
    echo -e "${GREEN}All domains should now appear in WorkMail console!${NC}"
    echo -e "${YELLOW}The issue was missing DNS records for tekanya.services${NC}"
else
    echo -e "${YELLOW}Deployment cancelled${NC}"
fi
