#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}💥 Builder Space EKS Cleanup Script${NC}"
echo -e "${RED}===================================${NC}"

# Get cluster info
CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "builder-space-dev")

echo -e "${YELLOW}⚠️  This will destroy the EKS cluster: ${CLUSTER_NAME}${NC}"
echo -e "${YELLOW}⚠️  This action is irreversible!${NC}"
echo ""

read -p "$(echo -e ${YELLOW}Are you sure you want to destroy the infrastructure? Type 'yes' to confirm: ${NC})" -r
if [[ ! $REPLY == "yes" ]]; then
    echo -e "${GREEN}✅ Cleanup cancelled.${NC}"
    exit 0
fi

echo -e "${YELLOW}🧹 Starting cleanup process...${NC}"

# Clean up any test resources first
echo -e "${YELLOW}🗑️ Cleaning up test resources...${NC}"
kubectl delete pod connectivity-test --ignore-not-found=true
kubectl delete pod dns-test --ignore-not-found=true

# Terraform destroy
echo -e "${YELLOW}💥 Destroying Terraform infrastructure...${NC}"
terraform destroy -auto-approve

echo -e "${GREEN}✅ Infrastructure destroyed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Cleanup complete${NC}"
echo "All AWS resources have been terminated."
echo "Your AWS bill should reflect the removal of EKS resources within 24 hours."
echo ""
echo -e "${YELLOW}💡 Note: You may want to clean up kubectl config:${NC}"
echo "kubectl config delete-context <context-name>"
echo "kubectl config delete-cluster <cluster-name>"