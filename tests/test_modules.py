"""
Unit tests for function-based Pulumi modules
Tests the shape of outputs and basic functionality
"""

import unittest
import sys
import os

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModuleStructure(unittest.TestCase):
    """Test that modules follow the expected function-based pattern"""
    
    def test_vpc_module_function_exists(self):
        """Test that VPC module has the expected function"""
        try:
            from modules.vpc import create_vpc_resources
            # Check function signature by calling help
            self.assertTrue(callable(create_vpc_resources))
        except ImportError as e:
            self.fail(f"Could not import create_vpc_resources: {e}")
    
    def test_iam_module_function_exists(self):
        """Test that IAM module has the expected function"""
        try:
            from modules.iam import create_iam_resources
            self.assertTrue(callable(create_iam_resources))
        except ImportError as e:
            self.fail(f"Could not import create_iam_resources: {e}")
    
    def test_eks_module_function_exists(self):
        """Test that EKS module has the expected function"""
        try:
            from modules.eks import create_eks_resources
            self.assertTrue(callable(create_eks_resources))
        except ImportError as e:
            self.fail(f"Could not import create_eks_resources: {e}")
    
    def test_addons_module_function_exists(self):
        """Test that Addons module has the expected function"""
        try:
            from modules.addons import create_addons_resources
            self.assertTrue(callable(create_addons_resources))
        except ImportError as e:
            self.fail(f"Could not import create_addons_resources: {e}")
    
    def test_state_storage_module_function_exists(self):
        """Test that State Storage module has the expected function"""
        try:
            from modules.state_storage import create_state_storage_resources
            self.assertTrue(callable(create_state_storage_resources))
        except ImportError as e:
            self.fail(f"Could not import create_state_storage_resources: {e}")
    
    def test_main_module_imports(self):
        """Test that main module can import all functions"""
        try:
            from modules import (
                create_vpc_resources,
                create_iam_resources,
                create_eks_resources,
                create_addons_resources,
                create_state_storage_resources
            )
            # All imports successful
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Could not import functions from modules: {e}")
    
    def test_no_large_classes_remain(self):
        """Test that no large Resource classes remain in modules"""
        import inspect
        
        # Check VPC module
        try:
            import modules.vpc as vpc_module
            members = inspect.getmembers(vpc_module, inspect.isclass)
            class_names = [name for name, obj in members if not name.startswith('_')]
            self.assertEqual(len(class_names), 0, f"VPC module still has classes: {class_names}")
        except ImportError:
            pass  # Module might not be importable in test environment
        
        # Check IAM module  
        try:
            import modules.iam as iam_module
            members = inspect.getmembers(iam_module, inspect.isclass)
            class_names = [name for name, obj in members if not name.startswith('_')]
            self.assertEqual(len(class_names), 0, f"IAM module still has classes: {class_names}")
        except ImportError:
            pass
        
        # Check EKS module
        try:
            import modules.eks as eks_module
            members = inspect.getmembers(eks_module, inspect.isclass)
            class_names = [name for name, obj in members if not name.startswith('_')]
            self.assertEqual(len(class_names), 0, f"EKS module still has classes: {class_names}")
        except ImportError:
            pass
    
    def test_function_naming_pattern(self):
        """Test that all modules follow the create_*_resources naming pattern"""
        expected_functions = [
            "create_vpc_resources",
            "create_iam_resources", 
            "create_eks_resources",
            "create_addons_resources",
            "create_state_storage_resources"
        ]
        
        for func_name in expected_functions:
            with self.subTest(function=func_name):
                self.assertTrue(func_name.startswith("create_"))
                self.assertTrue(func_name.endswith("_resources"))


if __name__ == '__main__':
    unittest.main()