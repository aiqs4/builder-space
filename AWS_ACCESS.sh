aws eks create-access-entry \
    --cluster-name builder-space \
    --principal-arn arn:aws:iam::207567777877:user/awsome \
    --type STANDARD

aws eks associate-access-policy \
    --cluster-name builder-space \
    --principal-arn arn:aws:iam::207567777877:user/awsome \
    --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy \
    --access-scope type=cluster

