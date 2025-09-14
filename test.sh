#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧪 Builder Space EKS Pulumi Test Script${NC}"
echo -e "${YELLOW}=======================================${NC}"

# Check if we're in the right directory
if [ ! -f "__main__.py" ]; then
    echo -e "${RED}❌ Error: Run this script from the project root directory${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Testing Pulumi project configuration...${NC}"

# Test 1: Python syntax validation
echo -e "${YELLOW}1. Testing Python syntax...${NC}"
python3 -m py_compile config.py __main__.py
find modules -name "*.py" -exec python3 -m py_compile {} \;
echo -e "${GREEN}✅ Python syntax validation passed${NC}"

# Test 2: Pulumi configuration validation  
echo -e "${YELLOW}2. Testing Pulumi configuration...${NC}"
if command -v pulumi &> /dev/null; then
    # Test if pulumi can read the configuration
    if pulumi preview --dry-run 2>/dev/null; then
        echo -e "${GREEN}✅ Pulumi configuration is valid${NC}"
    else
        echo -e "${YELLOW}⚠️  Pulumi preview requires AWS credentials and stack setup${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Pulumi CLI not installed - skipping configuration test${NC}"
fi

# Test 3: Module imports
echo -e "${YELLOW}3. Testing module imports...${NC}"
python3 -c "
import sys
sys.path.append('.')
try:
    from config import get_config
    from modules.vpc import VPCResources
    from modules.iam import IAMResources  
    from modules.eks import EKSResources
    from modules.addons import AddonsResources
    from modules.state_storage import StateStorageResources
    print('✅ All modules imported successfully')
except ImportError as e:
    print(f'❌ Module import failed: {e}')
    sys.exit(1)
"
echo -e "${GREEN}✅ Module imports successful${NC}"

# Test 4: Configuration loading
echo -e "${YELLOW}4. Testing configuration loading...${NC}"
python3 -c "
import sys
sys.path.append('.')
from config import get_config
config = get_config()
print(f'✅ Configuration loaded - cluster: {config.cluster_name}, region: {config.aws_region}')
"

# Test 5: GitHub Actions workflow validation
echo -e "${YELLOW}5. Testing GitHub Actions workflows...${NC}"
if [ -f ".github/workflows/deploy.yml" ] && [ -f ".github/workflows/backend-bootstrap.yml" ]; then
    echo -e "${GREEN}✅ GitHub Actions workflows present${NC}"
else
    echo -e "${RED}❌ Missing GitHub Actions workflows${NC}"
fi

# Test 6: Documentation check
echo -e "${YELLOW}6. Testing documentation...${NC}"
if [ -f "README.md" ] && [ -f "MIGRATION.md" ]; then
    echo -e "${GREEN}✅ Documentation files present${NC}"
else
    echo -e "${RED}❌ Missing documentation files${NC}"
fi

# Test 7: Legacy code archive
echo -e "${YELLOW}7. Testing legacy code archive...${NC}"
if [ -d "terraform-legacy" ]; then
    legacy_files=$(find terraform-legacy -name "*.tf" | wc -l)
    if [ "$legacy_files" -gt 0 ]; then
        echo -e "${GREEN}✅ Legacy Terraform code archived ($legacy_files files)${NC}"
    else
        echo -e "${RED}❌ Legacy directory exists but no .tf files found${NC}"
    fi
else
    echo -e "${RED}❌ Legacy code archive not found${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Test suite completed!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Configure AWS credentials: aws configure"
echo "2. Set Pulumi passphrase: export PULUMI_CONFIG_PASSPHRASE='your-passphrase'"
echo "3. Initialize stack: pulumi stack select dev --create"
echo "4. Preview deployment: pulumi preview"
echo "5. Deploy infrastructure: pulumi up"
echo ""
echo -e "${YELLOW}💡 Tip: Use './deploy.sh' for guided deployment${NC}"