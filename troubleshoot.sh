#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Builder Space Infrastructure Troubleshooting Tool${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "__main__.py" ]; then
    echo -e "${RED}❌ Error: Run this script from the project root directory${NC}"
    exit 1
fi

# Function to check command availability
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    fi
}

# Function to check AWS connectivity
check_aws() {
    echo -e "${YELLOW}🔐 Checking AWS credentials and connectivity...${NC}"
    
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        REGION=$(aws configure get region || echo "Not set")
        echo -e "${GREEN}✅ AWS credentials valid${NC}"
        echo -e "   Account: $ACCOUNT_ID"
        echo -e "   Region: $REGION"
    else
        echo -e "${RED}❌ AWS credentials not configured or invalid${NC}"
        echo "   Run: aws configure"
        return 1
    fi
    
    # Test basic AWS service access
    if aws s3 ls &> /dev/null; then
        echo -e "${GREEN}✅ S3 access verified${NC}"
    else
        echo -e "${YELLOW}⚠️ S3 access issue - check permissions${NC}"
    fi
    
    if aws dynamodb list-tables &> /dev/null; then
        echo -e "${GREEN}✅ DynamoDB access verified${NC}"
    else
        echo -e "${YELLOW}⚠️ DynamoDB access issue - check permissions${NC}"
    fi
    
    if aws eks list-clusters &> /dev/null; then
        echo -e "${GREEN}✅ EKS access verified${NC}"
    else
        echo -e "${YELLOW}⚠️ EKS access issue - check permissions${NC}"
    fi
}

# Function to check state storage
check_state_storage() {
    echo -e "${YELLOW}🗄️ Checking state storage...${NC}"
    
    cd bootstrap 2>/dev/null || {
        echo -e "${RED}❌ Bootstrap directory not found${NC}"
        return 1
    }
    
    if [ -f "Pulumi.yaml" ]; then
        echo -e "${GREEN}✅ Bootstrap Pulumi project found${NC}"
        
        # Check if stack exists
        if pulumi stack ls 2>/dev/null | grep -q "dev"; then
            echo -e "${GREEN}✅ Bootstrap stack 'dev' exists${NC}"
            
            # Try to get stack outputs
            BUCKET_NAME=$(pulumi stack output bucket_name 2>/dev/null || echo "")
            TABLE_NAME=$(pulumi stack output dynamodb_table_name 2>/dev/null || echo "")
            
            if [ -n "$BUCKET_NAME" ]; then
                echo -e "${GREEN}✅ State bucket: $BUCKET_NAME${NC}"
                if aws s3 ls "s3://$BUCKET_NAME" &> /dev/null; then
                    echo -e "${GREEN}✅ State bucket accessible${NC}"
                else
                    echo -e "${YELLOW}⚠️ State bucket not accessible${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️ State bucket name not found in stack output${NC}"
            fi
            
            if [ -n "$TABLE_NAME" ]; then
                echo -e "${GREEN}✅ State table: $TABLE_NAME${NC}"
                if aws dynamodb describe-table --table-name "$TABLE_NAME" &> /dev/null; then
                    echo -e "${GREEN}✅ State table accessible${NC}"
                else
                    echo -e "${YELLOW}⚠️ State table not accessible${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️ State table name not found in stack output${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️ Bootstrap stack 'dev' not found${NC}"
            echo "   Run: cd bootstrap && pulumi stack select dev --create"
        fi
    else
        echo -e "${RED}❌ Bootstrap Pulumi.yaml not found${NC}"
    fi
    
    cd .. 2>/dev/null || true
}

# Function to check main infrastructure
check_main_infrastructure() {
    echo -e "${YELLOW}🏗️ Checking main infrastructure...${NC}"
    
    if [ -f "Pulumi.yaml" ]; then
        echo -e "${GREEN}✅ Main Pulumi project found${NC}"
        
        # Check if stack exists
        if pulumi stack ls 2>/dev/null | grep -q "dev"; then
            echo -e "${GREEN}✅ Main stack 'dev' exists${NC}"
            
            # Check if cluster exists
            CLUSTER_NAME=$(pulumi config get cluster_name 2>/dev/null || echo "builder-space")
            REGION=$(pulumi config get aws:region 2>/dev/null || echo "af-south-1")
            
            if aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" &> /dev/null; then
                echo -e "${GREEN}✅ EKS cluster '$CLUSTER_NAME' exists${NC}"
                
                # Check cluster status
                STATUS=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query 'cluster.status' --output text)
                if [ "$STATUS" = "ACTIVE" ]; then
                    echo -e "${GREEN}✅ Cluster status: $STATUS${NC}"
                else
                    echo -e "${YELLOW}⚠️ Cluster status: $STATUS (not ACTIVE)${NC}"
                fi
                
                # Check kubectl connectivity
                if kubectl cluster-info &> /dev/null; then
                    echo -e "${GREEN}✅ kubectl connectivity verified${NC}"
                    
                    # Check nodes
                    NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
                    if [ "$NODE_COUNT" -gt 0 ]; then
                        echo -e "${GREEN}✅ Nodes available: $NODE_COUNT${NC}"
                    else
                        echo -e "${YELLOW}⚠️ No nodes found${NC}"
                    fi
                else
                    echo -e "${YELLOW}⚠️ kubectl connectivity failed${NC}"
                    echo "   Run: aws eks --region $REGION update-kubeconfig --name $CLUSTER_NAME"
                fi
            else
                echo -e "${YELLOW}⚠️ EKS cluster '$CLUSTER_NAME' not found${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️ Main stack 'dev' not found${NC}"
            echo "   Run: pulumi stack select dev --create"
        fi
    else
        echo -e "${RED}❌ Main Pulumi.yaml not found${NC}"
    fi
}

# Function to suggest fixes
suggest_fixes() {
    echo -e "${BLUE}💡 Common Fix Suggestions:${NC}"
    echo ""
    
    echo -e "${YELLOW}If you see 'BucketAlreadyOwnedByYou' or 'ResourceInUseException':${NC}"
    echo "   cd bootstrap && pulumi refresh --yes && pulumi up"
    echo ""
    
    echo -e "${YELLOW}If kubectl fails:${NC}"
    echo "   aws eks --region af-south-1 update-kubeconfig --name builder-space"
    echo ""
    
    echo -e "${YELLOW}If state is corrupted:${NC}"
    echo "   pulumi refresh --yes"
    echo ""
    
    echo -e "${YELLOW}For complete reset:${NC}"
    echo "   1. pulumi destroy --yes"
    echo "   2. cd bootstrap && pulumi destroy --yes"
    echo "   3. Start fresh with bootstrap"
    echo ""
    
    echo -e "${YELLOW}For local testing:${NC}"
    echo "   ./test.sh"
    echo ""
}

# Main execution
echo -e "${YELLOW}📋 Step 1: Checking prerequisites...${NC}"
check_command "aws" || exit 1
check_command "pulumi" || exit 1
check_command "kubectl" || echo -e "${YELLOW}⚠️ kubectl not found - cluster operations will fail${NC}"
check_command "python3" || exit 1

echo ""
echo -e "${YELLOW}📋 Step 2: Checking AWS connectivity...${NC}"
check_aws

echo ""
echo -e "${YELLOW}📋 Step 3: Checking state storage...${NC}"
check_state_storage

echo ""
echo -e "${YELLOW}📋 Step 4: Checking main infrastructure...${NC}"
check_main_infrastructure

echo ""
suggest_fixes

echo ""
echo -e "${GREEN}🎉 Troubleshooting completed!${NC}"
echo ""
echo -e "${BLUE}For more help, check the README.md troubleshooting section.${NC}"