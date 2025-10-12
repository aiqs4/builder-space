#!/bin/bash
# Helper script to convert image URLs to ECR pull-through cache format

set -e

# Get AWS account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "YOUR_ACCOUNT_ID")
AWS_REGION=$(aws configure get region 2>/dev/null || echo "af-south-1")
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}ECR Image URL Converter${NC}"
echo -e "${GREEN}Registry: ${REGISTRY}${NC}"
echo ""

# Function to convert image URL
convert_image() {
    local original=$1
    local ecr_url=""
    
    # Remove docker.io prefix if present
    original=${original#docker.io/}
    
    # Handle different registries
    if [[ $original == quay.io/* ]]; then
        # Quay.io image
        ecr_url="${REGISTRY}/quay/${original#quay.io/}"
    elif [[ $original == ghcr.io/* ]]; then
        # GitHub Container Registry
        ecr_url="${REGISTRY}/github/${original#ghcr.io/}"
    elif [[ $original == registry.k8s.io/* ]]; then
        # Kubernetes registry
        ecr_url="${REGISTRY}/k8s/${original#registry.k8s.io/}"
    elif [[ $original == gcr.io/* ]] || [[ $original == k8s.gcr.io/* ]]; then
        # Google Container Registry (not supported by pull-through cache)
        echo -e "${YELLOW}Warning: GCR images require manual sync or private repo${NC}"
        ecr_url="# NOT_SUPPORTED: $original"
    elif [[ $original == */* ]]; then
        # Docker Hub with namespace (e.g., bitnami/wordpress)
        ecr_url="${REGISTRY}/docker-hub/${original}"
    else
        # Docker Hub official image (library/)
        ecr_url="${REGISTRY}/docker-hub/library/${original}"
    fi
    
    echo "$ecr_url"
}

# Common images
echo -e "${YELLOW}Common Image Conversions:${NC}"
echo ""

images=(
    "nginx:latest"
    "bitnami/wordpress:latest"
    "bitnami/postgresql:latest"
    "bitnami/mongodb:latest"
    "rocketchat/rocket.chat:latest"
    "frappe/erpnext:latest"
    "redis:latest"
    "quay.io/prometheus/prometheus:latest"
    "ghcr.io/example/app:v1.0"
)

for img in "${images[@]}"; do
    converted=$(convert_image "$img")
    printf "%-40s → %s\n" "$img" "$converted"
done

echo ""
echo -e "${YELLOW}Usage in Helm values.yaml:${NC}"
echo ""
cat << 'EOF'
# Before (Docker Hub):
image:
  registry: docker.io
  repository: bitnami/wordpress
  tag: latest

# After (ECR Pull-Through Cache):
image:
  registry: ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
  repository: docker-hub/bitnami/wordpress
  tag: latest
EOF

echo ""
echo -e "${GREEN}Your registry: ${REGISTRY}${NC}"
echo ""

# Interactive mode
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}Enter an image URL to convert (or press Enter to exit):${NC}"
    read -r user_image
    
    while [ ! -z "$user_image" ]; do
        converted=$(convert_image "$user_image")
        echo -e "${GREEN}ECR URL:${NC} $converted"
        echo ""
        echo -e "${YELLOW}Enter another image URL (or press Enter to exit):${NC}"
        read -r user_image
    done
else
    # Command line argument
    converted=$(convert_image "$1")
    echo "$converted"
fi
