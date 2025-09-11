# GitHub Actions Setup

## OIDC Configuration

1. Create IAM OIDC Identity Provider in AWS:
   - URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

2. Create IAM Role with trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:aiqs4/builder-space:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

3. Attach policies to role:
   - `AmazonEKSClusterPolicy`
   - `AmazonEKSWorkerNodePolicy` 
   - `AmazonEKS_CNI_Policy`
   - `AmazonEC2ContainerRegistryReadOnly`
   - Custom policy for VPC/EC2/IAM operations

4. Add GitHub secret:
   - `AWS_ROLE_ARN`: Full ARN of the created role

## Usage

- **Manual**: Actions → Deploy EKS Infrastructure → Run workflow
- **Auto**: Push to main branch triggers plan