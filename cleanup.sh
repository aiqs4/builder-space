#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🗑️ Builder Space EKS Cleanup Script${NC}"
echo -e "${BLUE}===================================${NC}"

# Check if Pulumi is installed
if ! command -v pulumi &> /dev/null; then
    echo -e "${RED}❌ Pulumi is required but not installed.${NC}"
    echo "Please install Pulumi: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}📦 Activating Python virtual environment...${NC}"
    source venv/bin/activate
fi

echo -e "${YELLOW}📋 Current stack resources:${NC}"
pulumi stack --show-urns 2>/dev/null || echo "No stack found or error occurred"

echo ""
echo -e "${RED}⚠️ WARNING: This will destroy ALL infrastructure resources!${NC}"
echo -e "${RED}This includes:${NC}"
echo "- EKS cluster and node groups"
echo "- VPC and networking resources"
echo "- IAM roles and policies (if created by this stack)"
echo "- CloudWatch log groups"
echo "- KMS keys (if created by this stack)"
echo ""

read -p "$(echo -e ${RED}Are you sure you want to proceed? Type 'DELETE' to confirm: ${NC})" -r
echo
if [[ $REPLY != "DELETE" ]]; then
    echo -e "${YELLOW}⏸️ Cleanup cancelled.${NC}"
    exit 0
fi

echo -e "${YELLOW}🗑️ Destroying infrastructure...${NC}"
pulumi destroy --yes

echo -e "${GREEN}✅ Infrastructure destroyed successfully!${NC}"

echo ""
echo -e "${BLUE}📋 Manual cleanup (if needed):${NC}"
echo "1. Check for any remaining AWS resources in the console"
echo "2. Verify S3 state bucket is empty (if using S3 backend)"
echo "3. Remove local state files if no longer needed"
echo ""
echo -e "${YELLOW}💰 Cost impact: All infrastructure costs should now be stopped${NC}"