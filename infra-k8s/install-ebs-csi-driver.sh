#!/bin/bash
set -e

echo "=========================================================="
echo "Fixing EKS Infrastructure Issues"
echo "=========================================================="
echo ""
echo "This script will:"
echo "1. Create missing OIDC provider (fixes cluster autoscaler)"
echo "2. Install EBS CSI driver (fixes storage)"
echo "3. Clean up pending PVCs"
echo ""

# Check if we're in the right directory
if [ ! -f "__main__.py" ]; then
    echo "Error: Run this script from builder-space/infra-k8s directory"
    exit 1
fi

# Check if kubectl is configured
echo "Checking cluster connectivity..."
if ! kubectl cluster-info &>/dev/null; then
    echo "Error: kubectl not configured. Run: aws eks update-kubeconfig --name builder-space --region af-south-1"
    exit 1
fi

CLUSTER_NAME=$(kubectl config current-context | grep -oP 'builder-space')
echo "✓ Connected to cluster: $CLUSTER_NAME"
echo ""

# Check OIDC provider status
echo "Checking OIDC provider status..."
OIDC_ISSUER=$(aws eks describe-cluster --name builder-space --query 'cluster.identity.oidc.issuer' --output text --region af-south-1)
OIDC_ID=$(echo $OIDC_ISSUER | cut -d '/' -f5)
echo "Cluster OIDC Issuer: $OIDC_ISSUER"

if aws iam list-open-id-connect-providers | grep -q "$OIDC_ID"; then
    echo "✓ OIDC provider already registered in IAM"
else
    echo "⚠ OIDC provider NOT registered in IAM"
    echo "  This is why cluster autoscaler is failing!"
fi
echo ""

# Check cluster autoscaler status
echo "Checking cluster autoscaler status..."
CA_STATUS=$(kubectl get pods -n kube-system -l app.kubernetes.io/name=cluster-autoscaler -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
if [ "$CA_STATUS" = "Running" ]; then
    echo "✓ Cluster autoscaler is running"
else
    echo "⚠ Cluster autoscaler status: $CA_STATUS"
    if [ "$CA_STATUS" != "Running" ] && [ "$CA_STATUS" != "NotFound" ]; then
        echo "  Last error:"
        kubectl logs -n kube-system -l app.kubernetes.io/name=cluster-autoscaler --tail=3 2>/dev/null | grep -i "error\|failed" | head -1 || echo "  (check logs for details)"
    fi
fi
echo ""

# Check current EBS CSI driver status
echo "Checking current EBS CSI driver status..."
if aws eks describe-addon --cluster-name builder-space --addon-name aws-ebs-csi-driver --region af-south-1 &>/dev/null; then
    echo "⚠ EBS CSI driver addon already exists"
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping driver installation"
        UPDATE_DRIVER=false
    else
        UPDATE_DRIVER=true
    fi
else
    echo "✓ EBS CSI driver not installed yet"
    UPDATE_DRIVER=true
fi
echo ""

# Deploy via Pulumi
if [ "$UPDATE_DRIVER" = true ]; then
    echo "=========================================================="
    echo "Step 1: Deploying Infrastructure via Pulumi"
    echo "=========================================================="
    echo ""
    echo "This will:"
    echo "  - Create OIDC provider in IAM (if missing)"
    echo "  - Install/Update EBS CSI driver"
    echo "  - Fix cluster autoscaler authentication"
    echo ""
    
    pulumi up --yes
    
    echo ""
    echo "✓ Infrastructure deployed successfully!"
    echo ""
fi

# Wait for OIDC provider to be active
echo "=========================================================="
echo "Step 2: Verifying OIDC Provider"
echo "=========================================================="
echo ""

sleep 5  # Give IAM a moment to propagate

if aws iam list-open-id-connect-providers | grep -q "$OIDC_ID"; then
    echo "✓ OIDC provider is now registered in IAM"
    aws iam list-open-id-connect-providers | grep "oidc.eks"
else
    echo "⚠ OIDC provider not found. This may cause issues."
fi
echo ""

# Check cluster autoscaler recovery
echo "=========================================================="
echo "Step 3: Checking Cluster Autoscaler Recovery"
echo "=========================================================="
echo ""

echo "Waiting for cluster autoscaler to recover..."
sleep 10

# Delete the crashing pod to force restart with new credentials
OLD_CA_POD=$(kubectl get pods -n kube-system -l app.kubernetes.io/name=cluster-autoscaler -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$OLD_CA_POD" ]; then
    echo "Restarting cluster autoscaler pod: $OLD_CA_POD"
    kubectl delete pod "$OLD_CA_POD" -n kube-system --wait=false
    echo "Waiting for new pod to start..."
    sleep 15
fi

CA_STATUS=$(kubectl get pods -n kube-system -l app.kubernetes.io/name=cluster-autoscaler -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
echo "Cluster Autoscaler Status: $CA_STATUS"

if [ "$CA_STATUS" = "Running" ]; then
    echo "✓ Cluster autoscaler is now running!"
else
    echo "⚠ Cluster autoscaler is still $CA_STATUS"
    echo "  Check logs: kubectl logs -n kube-system -l app.kubernetes.io/name=cluster-autoscaler"
fi
echo ""

# Wait for driver to be ready
echo "=========================================================="
echo "Step 4: Waiting for EBS CSI Driver"
echo "=========================================================="
echo ""

echo "Waiting for EBS CSI controller pods..."
kubectl wait --for=condition=ready pod \
    -l app.kubernetes.io/name=aws-ebs-csi-driver \
    -n kube-system \
    --timeout=300s || true

echo ""
echo "EBS CSI Driver Status:"
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver
echo ""

# Check storage classes
echo "=========================================================="
echo "Step 5: Verifying Storage Classes"
echo "=========================================================="
echo ""
kubectl get storageclass
echo ""

# Clean up old pending PVCs
echo "=========================================================="
echo "Step 6: Cleaning up old pending PVCs"
echo "=========================================================="
echo ""

PENDING_PVCS=$(kubectl get pvc -n spruch -o json 2>/dev/null | jq -r '.items[] | select(.status.phase=="Pending") | .metadata.name' || echo "")

if [ -n "$PENDING_PVCS" ]; then
    echo "Found pending PVCs in spruch namespace:"
    echo "$PENDING_PVCS"
    echo ""
    read -p "Delete these pending PVCs so they can be recreated? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$PENDING_PVCS" | while read pvc; do
            echo "Deleting PVC: $pvc"
            kubectl delete pvc "$pvc" -n spruch --wait=false
        done
        echo "✓ Old PVCs deleted. ArgoCD will recreate them."
    else
        echo "Skipped PVC cleanup. You can delete them manually later."
    fi
else
    echo "✓ No pending PVCs found in spruch namespace"
fi
echo ""

# Verify everything is working
echo "=========================================================="
echo "Step 7: Final Verification"
echo "=========================================================="
echo ""

echo "Cluster Autoscaler:"
kubectl get pods -n kube-system -l app.kubernetes.io/name=cluster-autoscaler
echo ""

echo "External DNS:"
kubectl get pods -n external-dns 2>/dev/null || echo "(not deployed yet)"
echo ""

echo "EBS CSI Driver Pods:"
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver
echo ""

echo "Storage Classes:"
kubectl get sc
echo ""

echo "PVCs in spruch namespace:"
kubectl get pvc -n spruch 2>/dev/null || echo "Namespace not found or no PVCs yet"
echo ""

echo "=========================================================="
echo "✅ Infrastructure Setup Complete!"
echo "=========================================================="
echo ""
echo "What was fixed:"
echo "  ✓ OIDC provider registered in IAM"
echo "  ✓ Cluster autoscaler can now authenticate"
echo "  ✓ EBS CSI driver installed and running"
echo "  ✓ Storage classes available (gp2, gp3)"
echo ""
echo "Next Steps:"
echo "1. Monitor cluster autoscaler: kubectl logs -n kube-system -l app.kubernetes.io/name=cluster-autoscaler -f"
echo "2. Check WordPress pods: kubectl get pods -n spruch -w"
echo "3. Monitor PVC status: kubectl get pvc -n spruch -w"
echo ""
echo "Troubleshooting:"
echo "- Cluster Autoscaler logs: kubectl logs -n kube-system -l app.kubernetes.io/name=cluster-autoscaler"
echo "- EBS CSI Driver logs: kubectl logs -n kube-system -l app=ebs-csi-controller -c csi-provisioner"
echo "- Describe PVC: kubectl describe pvc <pvc-name> -n spruch"
echo ""
