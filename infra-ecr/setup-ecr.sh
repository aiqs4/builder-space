#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}ECR Pull-Through Cache Setup${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v pulumi &> /dev/null; then
    echo -e "${RED}Error: Pulumi CLI not found${NC}"
    echo "Install: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI not found${NC}"
    echo "Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "af-south-1")

echo -e "${GREEN}AWS Account ID: ${ACCOUNT_ID}${NC}"
echo -e "${GREEN}AWS Region: ${AWS_REGION}${NC}"
echo ""

# Ask for Pulumi passphrase
if [ -z "$PULUMI_CONFIG_PASSPHRASE" ]; then
    echo -e "${YELLOW}Enter Pulumi passphrase:${NC}"
    read -s PULUMI_CONFIG_PASSPHRASE
    export PULUMI_CONFIG_PASSPHRASE
    echo ""
fi

# Ask for Docker Hub credentials (optional)
echo -e "${YELLOW}Do you want to add Docker Hub credentials for higher rate limits? (y/N)${NC}"
read -r ADD_DOCKERHUB

if [[ "$ADD_DOCKERHUB" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Enter Docker Hub username:${NC}"
    read DOCKERHUB_USERNAME
    
    echo -e "${YELLOW}Enter Docker Hub token/password:${NC}"
    read -s DOCKERHUB_PASSWORD
    echo ""
    
    DOCKERHUB_ARGS="--set dockerhub_username=$DOCKERHUB_USERNAME --set-secret dockerhub_password=$DOCKERHUB_PASSWORD"
else
    DOCKERHUB_ARGS=""
fi

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create/select stack
echo -e "${YELLOW}Creating/selecting Pulumi stack...${NC}"
pulumi stack select ecr --create 2>/dev/null || pulumi stack select ecr
echo -e "${GREEN}✓ Stack selected${NC}"
echo ""

# Set configuration
echo -e "${YELLOW}Configuring stack...${NC}"
pulumi config set aws:region $AWS_REGION
pulumi config set cluster_name builder-space

if [ ! -z "$DOCKERHUB_USERNAME" ]; then
    pulumi config set dockerhub_username $DOCKERHUB_USERNAME
    pulumi config set --secret dockerhub_password $DOCKERHUB_PASSWORD
fi

echo -e "${GREEN}✓ Configuration complete${NC}"
echo ""

# Preview changes
echo -e "${YELLOW}Previewing changes...${NC}"
pulumi preview

echo ""
echo -e "${YELLOW}Do you want to deploy? (y/N)${NC}"
read -r DEPLOY

if [[ "$DEPLOY" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deploying ECR stack...${NC}"
    pulumi up --yes
    
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    
    # Get outputs
    REGISTRY_URL=$(pulumi stack output ecr_registry_url)
    
    echo -e "${GREEN}ECR Registry URL:${NC} $REGISTRY_URL"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Test Docker login:"
    echo "   aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY_URL"
    echo ""
    echo "2. Pull an image to test pull-through cache:"
    echo "   docker pull $REGISTRY_URL/docker-hub/library/nginx:latest"
    echo ""
    echo "3. Update your Helm values to use ECR:"
    echo "   Before: bitnami/wordpress:latest"
    echo "   After:  $REGISTRY_URL/docker-hub/bitnami/wordpress:latest"
    echo ""
    echo "4. View all outputs:"
    echo "   pulumi stack output"
    echo ""
    echo -e "${GREEN}Cost estimate: \$1-5/month (first 500MB free)${NC}"
else
    echo -e "${YELLOW}Deployment cancelled${NC}"
fi
