"""
Aurora PostgreSQL Serverless v2 Stack
Separate database deployment from EKS cluster
"""
import pulumi
from src import database

# Exports
pulumi.export("database_endpoint", database.aurora_cluster.endpoint)
pulumi.export("database_name", database.aurora_cluster.database_name)
pulumi.export("master_username", database.aurora_cluster.master_username)
pulumi.export("reader_endpoint", database.aurora_cluster.reader_endpoint)
