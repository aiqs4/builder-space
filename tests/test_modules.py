"""
Unit tests for declarative Pulumi modules
Tests that modules contain only resource declarations (no functions or classes)
"""

import unittest
import sys
import os
import inspect

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDeclarativeStructure(unittest.TestCase):
    """Test that modules follow pure declarative pattern"""
    
    def test_no_functions_in_modules(self):
        """Test that modules contain no user-defined functions"""
        module_names = ['vpc', 'iam', 'eks', 'addons', 'state_storage']
        
        for module_name in module_names:
            with self.subTest(module=module_name):
                try:
                    module = __import__(f'modules.{module_name}', fromlist=[''])
                    functions = inspect.getmembers(module, inspect.isfunction)
                    # Filter out built-in and imported functions, only check module-defined ones
                    user_functions = [name for name, func in functions 
                                    if func.__module__ == f'modules.{module_name}']
                    self.assertEqual(len(user_functions), 0, 
                                   f"{module_name} module has functions: {user_functions}. Should be pure declarations.")
                except ImportError:
                    self.skipTest(f"Could not import {module_name} module (missing dependencies)")
    
    def test_no_classes_in_modules(self):
        """Test that modules contain no user-defined classes"""
        module_names = ['vpc', 'iam', 'eks', 'addons', 'state_storage']
        
        for module_name in module_names:
            with self.subTest(module=module_name):
                try:
                    module = __import__(f'modules.{module_name}', fromlist=[''])
                    classes = inspect.getmembers(module, inspect.isclass)
                    # Filter out imported classes, only check module-defined ones
                    user_classes = [name for name, cls in classes 
                                  if cls.__module__ == f'modules.{module_name}']
                    self.assertEqual(len(user_classes), 0, 
                                   f"{module_name} module has classes: {user_classes}. Should be pure declarations.")
                except ImportError:
                    self.skipTest(f"Could not import {module_name} module (missing dependencies)")
    
    def test_modules_have_resource_declarations(self):
        """Test that modules export resource variables"""
        expected_exports = {
            'vpc': ['vpc_id', 'vpc_cidr_block', 'public_subnet_ids', 'cluster_security_group_id'],
            'iam': ['cluster_role_arn', 'cluster_role_name', 'node_group_role_arn', 'node_group_role_name'],
            'eks': ['cluster_id', 'cluster_arn', 'cluster_endpoint', 'cluster_version'],
            'addons': ['metrics_server_status', 'aws_load_balancer_controller_status', 'test_deployment_name'],
            'state_storage': ['state_bucket_name', 'state_bucket_arn', 'state_lock_table_name']
        }
        
        for module_name, expected_vars in expected_exports.items():
            with self.subTest(module=module_name):
                try:
                    module = __import__(f'modules.{module_name}', fromlist=[''])
                    for var_name in expected_vars:
                        self.assertTrue(hasattr(module, var_name), 
                                      f"{module_name} module missing export: {var_name}")
                except ImportError:
                    self.skipTest(f"Could not import {module_name} module (missing dependencies)")
    
    def test_main_imports_modules_declaratively(self):
        """Test that main file imports modules declaratively"""
        try:
            with open('__main__.py', 'r') as f:
                main_content = f.read()
            
            # Check that modules are imported as modules, not specific functions
            self.assertIn('import modules.vpc as vpc_module', main_content)
            self.assertIn('import modules.iam as iam_module', main_content)
            self.assertIn('import modules.eks as eks_module', main_content)
            self.assertIn('import modules.addons as addons_module', main_content)
            self.assertIn('import modules.state_storage as state_storage_module', main_content)
            
            # Check that there are no function calls in main
            self.assertNotIn('create_vpc_resources(', main_content)
            self.assertNotIn('create_iam_resources(', main_content)
            self.assertNotIn('create_eks_resources(', main_content)
            
        except FileNotFoundError:
            self.skipTest("__main__.py not found")
    
    def test_purely_declarative_pattern(self):
        """Test that modules follow pure declarative IaC pattern"""
        # This test validates that our approach matches the user's requirement:
        # "IaC should be just declaration. No if/else, only if really needed"
        
        module_names = ['vpc', 'iam', 'eks', 'addons', 'state_storage']
        
        for module_name in module_names:
            with self.subTest(module=module_name):
                try:
                    # Read module source
                    with open(f'modules/{module_name}/__init__.py', 'r') as f:
                        content = f.read()
                    
                    # Should contain resource declarations (AWS or Kubernetes)
                    if module_name == 'addons':
                        self.assertIn('k8s.', content, f"{module_name} should contain Kubernetes resource declarations")
                    else:
                        self.assertIn('aws.', content, f"{module_name} should contain AWS resource declarations")
                    
                    # Should not contain class definitions  
                    self.assertNotIn('class ', content, f"{module_name} should not contain class definitions")
                    
                    # Should not contain function definitions (except minimal conditional logic)
                    self.assertNotIn('def create_', content, f"{module_name} should not contain create_* functions")
                    
                except FileNotFoundError:
                    self.skipTest(f"Module file {module_name}/__init__.py not found")


if __name__ == '__main__':
    unittest.main()