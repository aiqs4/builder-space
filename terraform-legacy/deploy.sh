#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🚀 Builder Space EKS Deployment Script${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is required but not installed.${NC}"
    echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is required but not installed.${NC}"
    echo "Please install kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is required but not installed.${NC}"
    echo "Please install Terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured.${NC}"
    echo "Please configure AWS credentials: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met!${NC}"

# Get AWS account info
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "af-south-1")
echo -e "${BLUE}📍 AWS Account: ${AWS_ACCOUNT}, Region: ${AWS_REGION}${NC}"

# Terraform operations
echo -e "${YELLOW}🔧 Initializing Terraform...${NC}"
cd "$SCRIPT_DIR"
terraform init

echo -e "${YELLOW}📝 Formatting Terraform files...${NC}"
terraform fmt -recursive

echo -e "${YELLOW}✅ Validating Terraform configuration...${NC}"
terraform validate

echo -e "${YELLOW}📊 Planning deployment...${NC}"
terraform plan -out=tfplan

echo -e "${YELLOW}💰 Estimated costs:${NC}"
echo "EKS Cluster: ~\$72/month (\$0.10/hour)"
echo "Node Group (2 x t4g.small): ~\$29/month" 
echo "EBS Storage (40GB): ~\$8/month"
echo "Total: ~\$109/month"
echo ""

read -p "$(echo -e ${YELLOW}Do you want to proceed with deployment? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️ Deployment cancelled.${NC}"
    exit 0
fi

echo -e "${YELLOW}🚀 Deploying infrastructure...${NC}"
terraform apply tfplan

echo -e "${GREEN}✅ Infrastructure deployed successfully!${NC}"

# Configure kubectl
echo -e "${YELLOW}🔧 Configuring kubectl...${NC}"
CLUSTER_NAME=$(terraform output -raw cluster_name)
aws eks --region "$AWS_REGION" update-kubeconfig --name "$CLUSTER_NAME"

echo -e "${GREEN}✅ kubectl configured!${NC}"

# Verify deployment
echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
echo "Waiting for nodes to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Check nodes: kubectl get nodes"
echo "2. Check system pods: kubectl get pods -n kube-system"
echo "3. Test internet connectivity: kubectl logs -n test deployment/test-internet-app"
echo "4. Check metrics: kubectl top nodes"
echo ""
echo -e "${BLUE}🔗 Useful outputs:${NC}"
terraform output next_steps