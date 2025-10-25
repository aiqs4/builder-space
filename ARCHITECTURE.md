# 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AWS Region: af-south-1                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      VPC: 10.0.0.0/16                             │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐       │ │
│  │  │   Public Subnet 1       │  │   Public Subnet 2       │       │ │
│  │  │   10.0.0.0/22 (1022 IPs)│  │   10.0.4.0/22 (1022 IPs)│       │ │
│  │  │   af-south-1a           │  │   af-south-1b           │       │ │
│  │  │                         │  │                         │       │ │
│  │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │       │ │
│  │  │  │ EKS Node        │    │  │  │ EKS Node        │    │       │ │
│  │  │  │ t3.xlarge       │    │  │  │ t3.xlarge       │    │       │ │
│  │  │  │ (ON_DEMAND)     │    │  │  │ (ON_DEMAND)     │    │       │ │
│  │  │  └─────────────────┘    │  │  └─────────────────┘    │       │ │
│  │  │                         │  │                         │       │ │
│  │  │  ┌─────────────────┐    │  │  ┌─────────────────┐    │       │ │
│  │  │  │ Karpenter Node  │    │  │  │ Karpenter Node  │    │       │ │
│  │  │  │ (Dynamic)       │    │  │  │ (Dynamic)       │    │       │ │
│  │  │  │ SPOT/ON_DEMAND  │    │  │  │ SPOT/ON_DEMAND  │    │       │ │
│  │  │  └─────────────────┘    │  │  └─────────────────┘    │       │ │
│  │  └─────────────────────────┘  └─────────────────────────┘       │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │           EKS Control Plane (v1.31)                         │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │ │
│  │  │  │ API      │ │ etcd     │ │Scheduler │ │Controller│      │ │ │
│  │  │  │ Server   │ │          │ │          │ │ Manager  │      │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │              Aurora PostgreSQL Serverless v2                │ │ │
│  │  │  ┌──────────────────────────────────────────────────────┐   │ │ │
│  │  │  │  Writer Instance (db.serverless)                     │   │ │ │
│  │  │  │  Scaling: 0.5 - 2.0 ACU                             │   │ │ │
│  │  │  │  Database: builderspace                             │   │ │ │
│  │  │  │  IAM Auth: ✅  Encryption: ✅  Backups: 7 days      │   │ │ │
│  │  │  └──────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    EKS Add-ons (AWS Managed)                      │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │ │
│  │  │  VPC CNI     │ │  CoreDNS     │ │ EBS CSI      │             │ │
│  │  │  v1.18.5     │ │  v1.11.3     │ │ v1.37.0      │             │ │
│  │  │  (Auto IAM)  │ │  (Auto IAM)  │ │ (Auto IAM)   │             │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘             │ │
│  │  ┌──────────────────────────────────┐                            │ │
│  │  │  Pod Identity Agent v1.3.4       │                            │ │
│  │  │  (Auto IAM)                      │                            │ │
│  │  └──────────────────────────────────┘                            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                 Custom Components (Pod Identity)                  │ │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐        │ │
│  │  │   External DNS          │  │   Karpenter             │        │ │
│  │  │   v0.14.2               │  │   v1.0.6                │        │ │
│  │  │                         │  │                         │        │ │
│  │  │   Manages DNS for:      │  │   Features:             │        │ │
│  │  │   • amano.services      │  │   • Spot + On-demand    │        │ │
│  │  │   • tekanya.services    │  │   • Consolidation       │        │ │
│  │  │   • lightsphere.space   │  │   • Multi-arch          │        │ │
│  │  │   • sosolola.cloud      │  │   • Fast scaling        │        │ │
│  │  └─────────────────────────┘  └─────────────────────────┘        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                     External Services                             │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │ │
│  │  │  Route53     │ │  CloudWatch  │ │  ECR         │             │ │
│  │  │  (DNS Mgmt)  │ │  (Logging)   │ │  (Images)    │             │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Traffic Flow                                    │
└─────────────────────────────────────────────────────────────────────────┘

    Internet
       │
       ↓
   [IGW] ─────────────────────────────────────┐
       │                                       │
       ↓                                       ↓
   [LoadBalancer] ──────→ [Service] ──────→ [Pods]
       │                      │
       │                      ↓
       │                [External DNS]
       │                      │
       │                      ↓
       │                 [Route53]
       │
       └──────────────→ [Karpenter]
                             │
                             ↓
                        [EC2 API]
                             │
                             ↓
                      [New Nodes]


┌─────────────────────────────────────────────────────────────────────────┐
│                      IAM & Security Flow                                │
└─────────────────────────────────────────────────────────────────────────┘

    Service Account (K8s)
           │
           ↓
    [Pod Identity Agent]
           │
           ↓
    [IAM Role] ────────→ [AWS Services]
           │                    │
           │                    ├─→ Route53 (External DNS)
           │                    ├─→ EC2 (Karpenter)
           │                    ├─→ RDS (Apps)
           │                    └─→ CloudWatch (Logging)
           │
           ↓
    [Temporary Credentials]


┌─────────────────────────────────────────────────────────────────────────┐
│                      Code Structure                                     │
└─────────────────────────────────────────────────────────────────────────┘

    __main__.py
         │
         ├─→ network.py ──────────→ [VPC, Subnets, IGW, Routes]
         │
         ├─→ cluster.py ──────────→ [EKS Cluster, Node Group, IAM]
         │
         ├─→ addons.py ───────────→ [VPC-CNI, CoreDNS, Pod Identity, EBS CSI]
         │
         ├─→ database.py ─────────→ [Aurora Serverless v2]
         │
         ├─→ external_dns.py ─────→ [External DNS + IAM]
         │
         └─→ karpenter.py ────────→ [Karpenter + NodePool + IAM]


┌─────────────────────────────────────────────────────────────────────────┐
│                      Resource Dependencies                              │
└─────────────────────────────────────────────────────────────────────────┘

    network
       │
       ├─→ cluster ──────→ addons
       │      │
       │      ├─→ external_dns
       │      │
       │      └─→ karpenter
       │
       └─→ database


┌─────────────────────────────────────────────────────────────────────────┐
│                      Scaling Behavior                                   │
└─────────────────────────────────────────────────────────────────────────┘

    Workload Deployed
           │
           ↓
    [K8s Scheduler] ─────→ No capacity?
           │                     │
           │                     ↓
           │              [Karpenter]
           │                     │
           ↓                     ↓
    [Existing Node]      [Provision Node]
           │                     │
           │                     ├─→ Try SPOT first
           │                     └─→ Fallback ON_DEMAND
           │
           └─────────→ [Pod Running]
                            │
                            ↓
                      [Service Created]
                            │
                            ↓
                      [External DNS]
                            │
                            ↓
                      [Route53 Record]


┌─────────────────────────────────────────────────────────────────────────┐
│                      Cost Optimization                                  │
└─────────────────────────────────────────────────────────────────────────┘

    Idle Time Detected
           │
           ↓
    [Karpenter Consolidation]
           │
           ├─→ Underutilized nodes
           │      │
           │      ↓
           │   [Drain pods]
           │      │
           │      ↓
           │   [Terminate node]
           │
           └─→ Empty nodes
                  │
                  ↓
               [Immediate termination]

    Database Idle
           │
           ↓
    [Aurora Serverless v2]
           │
           ↓
    [Scale to 0.5 ACU]
           │
           ↓
    [Minimal cost]


┌─────────────────────────────────────────────────────────────────────────┐
│                      Key Metrics                                        │
└─────────────────────────────────────────────────────────────────────────┘

    Network:      2x /22 subnets = 2,044 usable IPs
    Compute:      3 initial nodes + Karpenter dynamic
    Storage:      EBS CSI for persistent volumes
    Database:     0.5 - 2.0 ACU (scales with load)
    Autoscaling:  < 30 seconds node provisioning
    DNS:          Automatic across 4 domains
    Cost:         ~$150-300/month (varies with load)

```

## Component Details

### Network Layer
- **VPC CIDR**: 10.0.0.0/16 (65,536 IPs)
- **Subnet 1**: 10.0.0.0/22 (1,022 usable IPs) - AZ: af-south-1a
- **Subnet 2**: 10.0.4.0/22 (1,022 usable IPs) - AZ: af-south-1b
- **Routing**: Single route table, all traffic via IGW

### Compute Layer
- **Initial Nodes**: 3x t3.xlarge (ON_DEMAND)
- **Karpenter Nodes**: Dynamic (SPOT + ON_DEMAND mix)
- **Instance Types**: t, c, m families
- **Architecture**: arm64 + amd64

### Control Plane
- **Version**: EKS 1.31
- **Endpoint**: Public + Private
- **Logging**: Enabled (api, audit, authenticator)
- **Auth**: API mode (modern)

### Storage
- **Persistent**: EBS CSI (AWS managed)
- **Storage Classes**: gp3 (default), gp2, io1, io2
- **Snapshots**: Automatic via EBS

### Database
- **Engine**: Aurora PostgreSQL 16.4
- **Scaling**: 0.5 - 2.0 ACU (Serverless v2)
- **Backups**: 7-day retention
- **Encryption**: ✅ At rest
- **Auth**: IAM + password

### DNS
- **Provider**: External DNS v0.14.2
- **Zones**: 4 domains (amano, tekanya, lightsphere, sosolola)
- **Update**: Automatic on service creation
- **TTL**: 300 seconds

### Autoscaling
- **Engine**: Karpenter v1.0.6
- **Strategy**: Consolidate when underutilized
- **Spot**: Preferred, fallback to on-demand
- **Provisioning**: < 30 seconds

### Security
- **IAM**: Pod Identity (modern IRSA)
- **RBAC**: Cluster admin for GitHub Actions
- **Network**: VPC isolation
- **Encryption**: Database + EBS volumes
- **Secrets**: AWS Secrets Manager ready

### Monitoring
- **Control Plane**: CloudWatch Logs
- **Nodes**: CloudWatch Agent (optional)
- **Database**: RDS Enhanced Monitoring
- **Cost**: AWS Cost Explorer

## KISS Principles Demonstrated

✅ **Simple**: Each component has one job
✅ **Minimal**: Only production essentials
✅ **Managed**: AWS handles heavy lifting
✅ **Scalable**: Karpenter + Aurora Serverless
✅ **Cost-Effective**: Spot + consolidation + serverless DB
✅ **Production-Ready**: HA, backups, encryption, monitoring
