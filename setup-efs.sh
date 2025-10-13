#!/bin/bash
set -e

echo "=== EFS Setup ==="

# 1. Deploy EFS in Pulumi
cd /home/alex/work/src/Amano/src/builder-space
pulumi up --stack eks

# Get EFS ID
EFS_ID=$(pulumi stack output efs_id --stack eks 2>/dev/null || echo "")

if [ -z "$EFS_ID" ]; then
    echo "Creating EFS..."
    cd infra-efs
    pip install -r requirements.txt
    pulumi stack init efs
    pulumi up --yes
    EFS_ID=$(pulumi stack output efs_id)
    cd ..
fi

echo "EFS ID: $EFS_ID"

# 2. Install EFS CSI Driver
echo "Installing EFS CSI driver..."
kubectl apply -k "github.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-2.0"

# Wait for driver
kubectl wait --for=condition=available --timeout=300s deployment/efs-csi-controller -n kube-system

# 3. Create StorageClass
echo "Creating EFS StorageClass..."
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: ${EFS_ID}
  directoryPerms: "700"
EOF

echo "✅ EFS setup complete!"
echo "Update your apps to use storageClassName: efs"
