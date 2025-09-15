"""
Unit tests for refactored Pulumi modules
Tests the function-based approach for creating resources
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.vpc.functions import create_vpc_resources
from modules.iam.functions import create_iam_resources
from modules.eks.functions import create_eks_resources
from modules.addons.functions import create_addons_resources
from modules.state_storage.functions import create_state_storage_resources


class TestModuleFunctions(unittest.TestCase):
    """Test the function-based module approach"""
    
    def test_vpc_function_structure(self):
        """Test that VPC function returns expected structure"""
        # Mock pulumi and AWS calls
        with patch('modules.vpc.functions.aws') as mock_aws:
            # Mock the get_availability_zones call
            mock_aws.get_availability_zones.return_value = Mock(names=["us-east-1a", "us-east-1b"])
            
            # Mock VPC creation
            mock_vpc = Mock()
            mock_vpc.id = "vpc-12345"
            mock_vpc.cidr_block = "10.0.0.0/16"
            mock_aws.ec2.Vpc.return_value = mock_vpc
            
            # Mock other resources
            mock_aws.ec2.InternetGateway.return_value = Mock(id="igw-12345")
            mock_aws.ec2.Subnet.return_value = Mock(id="subnet-12345")
            mock_aws.ec2.RouteTable.return_value = Mock(id="rt-12345")
            mock_aws.ec2.Route.return_value = Mock()
            mock_aws.ec2.RouteTableAssociation.return_value = Mock()
            mock_aws.ec2.SecurityGroup.return_value = Mock(id="sg-12345")
            mock_aws.ec2.SecurityGroupRule.return_value = Mock()
            
            # Test the function
            result = create_vpc_resources(
                cluster_name="test-cluster",
                vpc_cidr="10.0.0.0/16",
                public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"]
            )
            
            # Verify structure
            self.assertIn("vpc_id", result)
            self.assertIn("vpc_cidr_block", result)
            self.assertIn("public_subnet_ids", result)
            self.assertIn("cluster_security_group_id", result)
            self.assertIn("node_group_security_group_id", result)
    
    def test_iam_function_structure(self):
        """Test that IAM function returns expected structure"""
        with patch('modules.iam.functions.aws') as mock_aws:
            # Mock IAM role creation
            mock_role = Mock()
            mock_role.arn = "arn:aws:iam::123456789012:role/test-role"
            mock_role.name = "test-role"
            mock_aws.iam.Role.return_value = mock_role
            mock_aws.iam.RolePolicyAttachment.return_value = Mock()
            mock_aws.iam.InstanceProfile.return_value = Mock()
            
            # Test the function
            result = create_iam_resources(cluster_name="test-cluster")
            
            # Verify structure
            self.assertIn("cluster_role_arn", result)
            self.assertIn("cluster_role_name", result)
            self.assertIn("node_group_role_arn", result)
            self.assertIn("node_group_role_name", result)
    
    def test_state_storage_function_structure(self):
        """Test that state storage function returns expected structure"""
        with patch('modules.state_storage.functions.aws') as mock_aws:
            # Mock S3 bucket creation
            mock_bucket = Mock()
            mock_bucket.id = "test-bucket"
            mock_aws.s3.Bucket.return_value = mock_bucket
            mock_aws.s3.BucketVersioning.return_value = Mock()
            mock_aws.s3.BucketServerSideEncryptionConfiguration.return_value = Mock()
            mock_aws.s3.BucketPublicAccessBlock.return_value = Mock()
            mock_aws.s3.BucketLifecycleConfiguration.return_value = Mock()
            
            # Mock DynamoDB table creation
            mock_table = Mock()
            mock_table.name = "test-table"
            mock_table.arn = "arn:aws:dynamodb:us-east-1:123456789012:table/test-table"
            mock_aws.dynamodb.Table.return_value = mock_table
            
            # Test the function
            result = create_state_storage_resources(
                cluster_name="test-cluster",
                aws_region="us-east-1"
            )
            
            # Verify structure
            self.assertIn("bucket_name_output", result)
            self.assertIn("dynamodb_table_name_output", result)
            self.assertIn("backend_config", result)
            self.assertIn("configuration_commands", result)
            
            # Verify backend config structure
            backend_config = result["backend_config"]
            self.assertEqual(backend_config["backend_type"], "s3")
            self.assertIn("bucket", backend_config)
            self.assertIn("region", backend_config)
            self.assertIn("dynamodb_table", backend_config)


def get_function_outputs_shape():
    """Return the expected shape of function outputs for documentation"""
    return {
        "vpc_resources": {
            "required_outputs": [
                "vpc_id", "vpc_cidr_block", "public_subnet_ids",
                "cluster_security_group_id", "node_group_security_group_id",
                "availability_zones"
            ],
            "internal_resources": [
                "_vpc", "_igw", "_subnets", "_route_table", "_cluster_sg", "_node_sg"
            ]
        },
        "iam_resources": {
            "required_outputs": [
                "cluster_role_arn", "cluster_role_name",
                "node_group_role_arn", "node_group_role_name"
            ],
            "internal_resources": [
                "_cluster_role", "_node_role", "_cluster_policy_attachment",
                "_node_policy_attachments", "_instance_profile"
            ]
        },
        "eks_resources": {
            "required_outputs": [
                "cluster_id", "cluster_arn", "cluster_endpoint",
                "cluster_version_output", "cluster_certificate_authority_data",
                "node_group_arn", "node_group_status"
            ],
            "internal_resources": [
                "_log_group", "_cluster", "_node_group", "_addons"
            ]
        },
        "addons_resources": {
            "required_outputs": [
                "metrics_server_status", "aws_load_balancer_controller_status",
                "test_namespace_name", "test_deployment_name"
            ],
            "internal_resources": [
                "_k8s_provider", "_namespace", "_metrics_server", "_test_deployment"
            ]
        },
        "state_storage_resources": {
            "required_outputs": [
                "bucket_name_output", "dynamodb_table_name_output",
                "backend_config", "configuration_commands"
            ],
            "internal_resources": [
                "_bucket", "_table", "_bucket_config"
            ]
        }
    }


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)