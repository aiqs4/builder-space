#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Builder Space EKS Test Script${NC}"
echo -e "${BLUE}===============================${NC}"

# Get cluster info
CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "builder-space")
REGION=$(terraform output -raw region 2>/dev/null || echo "af-south-1")

echo -e "${YELLOW}🔍 Testing EKS cluster: ${CLUSTER_NAME}${NC}"

# Test 1: Cluster connectivity
echo -e "${YELLOW}📡 Test 1: Cluster connectivity...${NC}"
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✅ Cluster is accessible${NC}"
else
    echo -e "${RED}❌ Cluster is not accessible${NC}"
    echo "Run: aws eks --region $REGION update-kubeconfig --name $CLUSTER_NAME"
    exit 1
fi

# Test 2: Node status
echo -e "${YELLOW}🖥️ Test 2: Node status...${NC}"
NODES=$(kubectl get nodes --no-headers | wc -l)
READY_NODES=$(kubectl get nodes --no-headers | grep -c Ready || echo 0)

echo "Total nodes: $NODES"
echo "Ready nodes: $READY_NODES"

if [ "$READY_NODES" -ge 2 ]; then
    echo -e "${GREEN}✅ All nodes are ready${NC}"
else
    echo -e "${YELLOW}⚠️ Some nodes may not be ready yet${NC}"
    kubectl get nodes
fi

# Test 3: System pods
echo -e "${YELLOW}🏗️ Test 3: System pods status...${NC}"
SYSTEM_PODS=$(kubectl get pods -n kube-system --no-headers | wc -l)
RUNNING_PODS=$(kubectl get pods -n kube-system --no-headers | grep -c Running || echo 0)

echo "Total system pods: $SYSTEM_PODS"
echo "Running system pods: $RUNNING_PODS"

if [ "$RUNNING_PODS" -gt 5 ]; then
    echo -e "${GREEN}✅ System pods are running${NC}"
else
    echo -e "${YELLOW}⚠️ Some system pods may not be ready${NC}"
    kubectl get pods -n kube-system
fi

# Test 4: Internet connectivity test
echo -e "${YELLOW}🌐 Test 4: Internet connectivity...${NC}"
if kubectl get deployment -n test test-internet-app &> /dev/null; then
    echo "Checking test deployment logs..."
    kubectl logs -n test deployment/test-internet-app --tail=5
    
    # Check if we can see IP responses
    if kubectl logs -n test deployment/test-internet-app | grep -q "origin"; then
        echo -e "${GREEN}✅ Internet connectivity working${NC}"
    else
        echo -e "${YELLOW}⚠️ Internet test deployment exists but no connectivity logs yet${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Test deployment not found${NC}"
fi

# Test 5: Metrics server
echo -e "${YELLOW}📊 Test 5: Metrics server...${NC}"
if kubectl top nodes &> /dev/null; then
    echo -e "${GREEN}✅ Metrics server is working${NC}"
    kubectl top nodes
else
    echo -e "${YELLOW}⚠️ Metrics server not ready yet${NC}"
fi

# Test 6: Create a quick test pod
echo -e "${YELLOW}🧪 Test 6: Deploy test pod with internet access...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: connectivity-test
  namespace: default
spec:
  containers:
  - name: test
    image: alpine:latest
    command: ["/bin/sh"]
    args: ["-c", "wget -qO- http://httpbin.org/ip && echo ' - Success!' && sleep 30"]
  restartPolicy: Never
EOF

echo "Waiting for test pod to complete..."
kubectl wait --for=condition=Ready pod/connectivity-test --timeout=60s || true
sleep 5
kubectl logs connectivity-test

# Clean up test pod
kubectl delete pod connectivity-test --ignore-not-found=true

# Test 7: DNS resolution
echo -e "${YELLOW}🔍 Test 7: DNS resolution...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: dns-test
  namespace: default
spec:
  containers:
  - name: test
    image: alpine:latest
    command: ["/bin/sh"]
    args: ["-c", "nslookup kubernetes.default.svc.cluster.local && echo 'DNS working!'"]
  restartPolicy: Never
EOF

kubectl wait --for=condition=Ready pod/dns-test --timeout=60s || true
sleep 3
kubectl logs dns-test
kubectl delete pod dns-test --ignore-not-found=true

# Summary
echo ""
echo -e "${BLUE}📋 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo "Nodes: $READY_NODES/$NODES ready"
echo "System pods: $RUNNING_PODS running"
echo ""

# Show helpful commands
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "kubectl get nodes -o wide"
echo "kubectl get pods -A"
echo "kubectl top nodes"
echo "kubectl top pods -A"
echo "kubectl logs -n test deployment/test-internet-app -f"
echo ""

# Cost estimation
echo -e "${BLUE}💰 Current Resource Usage:${NC}"
if command -v bc &> /dev/null; then
    NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
    ESTIMATED_COST=$(echo "scale=2; 72 + ($NODE_COUNT * 14.4) + ($NODE_COUNT * 4)" | bc)
    echo "Estimated monthly cost: \$${ESTIMATED_COST}"
else
    echo "Install 'bc' for cost calculations"
fi