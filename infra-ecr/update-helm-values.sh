#!/bin/bash
# Automated script to update all Helm values files with ECR registry URLs

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Update Helm Values for ECR${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "infra-ecr/Pulumi.yaml" ]; then
    echo -e "${RED}Error: Run this from /home/alex/work/src/Amano/src/builder-space${NC}"
    exit 1
fi

# Get registry URL from Pulumi
cd infra-ecr
REGISTRY=$(pulumi stack output ecr_registry_url 2>/dev/null)

if [ -z "$REGISTRY" ]; then
    echo -e "${RED}Error: ECR stack not deployed yet${NC}"
    echo "Run: cd infra-ecr && ./setup-ecr.sh"
    exit 1
fi

echo -e "${GREEN}Registry URL: ${REGISTRY}${NC}"
echo ""

cd ..

# Define files to update
ARGOCD_DIR="../builder-space-argocd/environments/prod"

declare -A FILES=(
    ["${ARGOCD_DIR}/spruch/values.yaml"]="WordPress"
    ["${ARGOCD_DIR}/rocketchat/values.yaml"]="Rocket.Chat"
    ["${ARGOCD_DIR}/erpnext/values.yaml"]="ERPNext"
)

echo -e "${YELLOW}Files to update:${NC}"
for file in "${!FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ✓ $file (${FILES[$file]})"
    else
        echo -e "  ✗ $file (${FILES[$file]}) - NOT FOUND"
    fi
done
echo ""

echo -e "${YELLOW}This will update all image registries to use ECR.${NC}"
echo -e "${YELLOW}A backup will be created for each file.${NC}"
echo ""
echo -e "${YELLOW}Continue? (y/N)${NC}"
read -r CONTINUE

if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# WordPress
WORDPRESS_FILE="${ARGOCD_DIR}/spruch/values.yaml"
if [ -f "$WORDPRESS_FILE" ]; then
    echo -e "${YELLOW}Updating WordPress...${NC}"
    cp "$WORDPRESS_FILE" "${WORDPRESS_FILE}.backup"
    
    # Update WordPress image
    sed -i "s|registry: docker.io|registry: ${REGISTRY}|g" "$WORDPRESS_FILE"
    sed -i "s|repository: bitnami/wordpress|repository: docker-hub/bitnami/wordpress|g" "$WORDPRESS_FILE"
    
    # Update MariaDB image (if present)
    sed -i "/mariadb:/,/image:/ s|registry: docker.io|registry: ${REGISTRY}|" "$WORDPRESS_FILE"
    sed -i "/mariadb:/,/repository:/ s|repository: bitnami/mariadb|repository: docker-hub/bitnami/mariadb|" "$WORDPRESS_FILE"
    
    echo -e "${GREEN}✓ WordPress updated${NC}"
fi

# Rocket.Chat
ROCKETCHAT_FILE="${ARGOCD_DIR}/rocketchat/values.yaml"
if [ -f "$ROCKETCHAT_FILE" ]; then
    echo -e "${YELLOW}Updating Rocket.Chat...${NC}"
    cp "$ROCKETCHAT_FILE" "${ROCKETCHAT_FILE}.backup"
    
    # Update Rocket.Chat image
    sed -i "s|repository: registry.rocket.chat/rocketchat/rocket.chat|repository: ${REGISTRY}/docker-hub/rocketchat/rocket.chat|g" "$ROCKETCHAT_FILE"
    
    # Update MongoDB image
    sed -i "/mongodb:/,/image:/ s|registry: docker.io|registry: ${REGISTRY}|" "$ROCKETCHAT_FILE"
    sed -i "/mongodb:/,/repository:/ s|repository: bitnami/mongodb|repository: docker-hub/bitnami/mongodb|" "$ROCKETCHAT_FILE"
    
    echo -e "${GREEN}✓ Rocket.Chat updated${NC}"
fi

# ERPNext
ERPNEXT_FILE="${ARGOCD_DIR}/erpnext/values.yaml"
if [ -f "$ERPNEXT_FILE" ]; then
    echo -e "${YELLOW}Updating ERPNext...${NC}"
    cp "$ERPNEXT_FILE" "${ERPNEXT_FILE}.backup"
    
    # Update ERPNext image
    sed -i "s|registry: docker.io|registry: ${REGISTRY}|g" "$ERPNEXT_FILE"
    sed -i "s|repository: frappe/erpnext|repository: docker-hub/frappe/erpnext|g" "$ERPNEXT_FILE"
    
    # Update Redis image (if present)
    sed -i "/redis:/,/image:/ s|registry: docker.io|registry: ${REGISTRY}|" "$ERPNEXT_FILE"
    sed -i "/redis:/,/repository:/ s|repository: bitnami/redis|repository: docker-hub/bitnami/redis|" "$ERPNEXT_FILE"
    
    echo -e "${GREEN}✓ ERPNext updated${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

echo -e "${YELLOW}Changed files:${NC}"
for file in "${!FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  $file"
        echo "  Backup: ${file}.backup"
    fi
done
echo ""

echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review changes:"
echo "   cd ${ARGOCD_DIR}"
echo "   git diff"
echo ""
echo "2. Test locally (optional):"
echo "   aws ecr get-login-password --region af-south-1 | \\"
echo "     docker login --username AWS --password-stdin ${REGISTRY}"
echo "   docker pull ${REGISTRY}/docker-hub/bitnami/wordpress:latest"
echo ""
echo "3. Commit and deploy:"
echo "   git add environments/prod/*/values.yaml"
echo "   git commit -m 'Switch to ECR pull-through cache'"
echo "   git push"
echo ""
echo "4. Monitor deployment:"
echo "   kubectl get pods -n spruch -w"
echo "   kubectl get pods -n rocketchat -w"
echo "   kubectl get pods -n erpnext -w"
echo ""
echo -e "${GREEN}Done!${NC}"
