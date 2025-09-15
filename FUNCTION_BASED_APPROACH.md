# Function-Based Pulumi Modules

This project has been refactored to use Pulumi's idiomatic, declarative style with simple module-level resource definitions and small helper functions instead of large, stateful classes.

## Overview

The refactored modules follow Pulumi best practices:
- **Declarative**: Resources are represented as module-level constructs
- **Simple**: Function calls instead of complex class instantiation  
- **Testable**: Small, focused functions that are easy to test and mock
- **Readable**: Clear input/output contracts and explicit dependencies
- **Maintainable**: Better separation of concerns and code reusability

## Module Structure

Each module now provides:
- A main function (e.g., `create_vpc_resources()`) that creates all related resources
- Small helper functions for specific resource types
- Clear return dictionaries with both outputs and internal resource references
- Legacy class wrappers for backward compatibility during migration

## Usage Examples

### VPC Resources
```python
from modules.vpc.functions import create_vpc_resources

vpc_resources = create_vpc_resources(
    cluster_name="my-cluster",
    vpc_cidr="10.0.0.0/16",
    public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"],
    tags={"Environment": "dev"}
)

# Access outputs
vpc_id = vpc_resources["vpc_id"]
subnet_ids = vpc_resources["public_subnet_ids"]
```

### IAM Resources
```python
from modules.iam.functions import create_iam_resources

iam_resources = create_iam_resources(
    cluster_name="my-cluster",
    tags={"Environment": "dev"}
)

# Access outputs
cluster_role_arn = iam_resources["cluster_role_arn"]
node_role_arn = iam_resources["node_group_role_arn"]
```

### EKS Resources
```python
from modules.eks.functions import create_eks_resources

eks_resources = create_eks_resources(
    cluster_name="my-cluster",
    cluster_version="1.32",
    cluster_role_arn=iam_resources["cluster_role_arn"],
    node_group_role_arn=iam_resources["node_group_role_arn"],
    subnet_ids=vpc_resources["public_subnet_ids"],
    cluster_security_group_id=vpc_resources["cluster_security_group_id"],
    node_security_group_id=vpc_resources["node_group_security_group_id"],
    node_instance_types=["t3.small"],
    node_desired_size=2,
    node_max_size=3,
    node_min_size=1,
    node_disk_size=20,
    tags={"Environment": "dev"}
)

# Access outputs
cluster_endpoint = eks_resources["cluster_endpoint"]
cluster_arn = eks_resources["cluster_arn"]
```

### Addons Resources
```python
from modules.addons.functions import create_addons_resources

addons_resources = create_addons_resources(
    cluster_name="my-cluster",
    cluster_endpoint=eks_resources["cluster_endpoint"],
    cluster_ca_data=eks_resources["cluster_certificate_authority_data"],
    enable_metrics_server=True,
    enable_test_deployment=True,
    tags={"Environment": "dev"}
)
```

### State Storage Resources
```python
from modules.state_storage.functions import create_state_storage_resources

state_storage = create_state_storage_resources(
    cluster_name="my-cluster",
    aws_region="us-east-1",
    tags={"Environment": "dev"}
)

# Get backend configuration
backend_config = state_storage["backend_config"]
setup_commands = state_storage["configuration_commands"]
```

## Function Output Structure

Each main function returns a consistent dictionary structure:

```python
{
    # Public outputs (for use by other modules)
    "vpc_id": pulumi.Output[str],
    "subnet_ids": List[pulumi.Output[str]],
    "security_group_ids": pulumi.Output[str],
    
    # Internal resource references (for dependencies, prefixed with _)
    "_vpc": aws.ec2.Vpc,
    "_subnets": List[aws.ec2.Subnet],
    "_security_groups": List[aws.ec2.SecurityGroup]
}
```

## Migration from Class-Based Approach

### Before (Class-Based)
```python
from modules.vpc import VPCResources

# Heavy class instantiation
vpc = VPCResources(
    cluster_name="my-cluster",
    vpc_cidr="10.0.0.0/16",
    public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"],
    tags=tags
)

# Access via properties
vpc_id = vpc.vpc_id
subnet_ids = vpc.public_subnet_ids
```

### After (Function-Based)
```python
from modules.vpc.functions import create_vpc_resources

# Simple function call
vpc_resources = create_vpc_resources(
    cluster_name="my-cluster",
    vpc_cidr="10.0.0.0/16",
    public_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24"],
    tags=tags
)

# Access via dictionary
vpc_id = vpc_resources["vpc_id"]
subnet_ids = vpc_resources["public_subnet_ids"]
```

## Migration Helper

Use the migration helper script to transition existing deployments:

```bash
python3 migration_helper.py
```

The helper provides:
1. Approach comparison
2. Resource import commands for existing infrastructure
3. New `__main__.py` template generation

## Testing

The function-based approach makes testing much easier:

```python
import unittest
from unittest.mock import Mock, patch
from modules.vpc.functions import create_vpc_resources

class TestVPCFunctions(unittest.TestCase):
    def test_vpc_creation(self):
        with patch('modules.vpc.functions.aws') as mock_aws:
            # Mock AWS resources
            mock_aws.ec2.Vpc.return_value = Mock(id="vpc-123")
            
            # Test function
            result = create_vpc_resources(
                cluster_name="test",
                vpc_cidr="10.0.0.0/16",
                public_subnet_cidrs=["10.0.1.0/24"]
            )
            
            # Verify output structure
            self.assertIn("vpc_id", result)
            self.assertIn("public_subnet_ids", result)
```

## Benefits

### Developer Experience
- **Clearer Code**: Function calls are more explicit than class constructors
- **Better IDE Support**: Functions have clearer signatures and return types
- **Easier Debugging**: Smaller functions are easier to debug and understand

### Testing & Maintenance
- **Unit Testing**: Each function can be tested independently
- **Mocking**: Simple to mock AWS resources and test logic
- **Refactoring**: Easier to modify individual functions without affecting others

### Pulumi Best Practices
- **Declarative Style**: Matches Pulumi's resource-centric model
- **Resource Graph**: Clearer understanding of resource dependencies
- **Import/Adoption**: Easier to handle existing resource adoption

## Backward Compatibility

The legacy class-based approach still works during migration:

```python
# This still works (uses function-based approach internally)
from modules.vpc import VPCResources
vpc = VPCResources(cluster_name="test", ...)
```

Legacy classes are thin wrappers around the new functions, so you can migrate gradually.

## File Structure

```
modules/
├── vpc/
│   ├── __init__.py      # Legacy class + new exports
│   └── functions.py     # Function-based implementation
├── iam/
│   ├── __init__.py      # Legacy class + new exports  
│   └── functions.py     # Function-based implementation
├── eks/
│   ├── __init__.py      # Legacy class + new exports
│   └── functions.py     # Function-based implementation
├── addons/
│   ├── __init__.py      # Legacy class + new exports
│   └── functions.py     # Function-based implementation
└── state_storage/
    ├── __init__.py      # Legacy class + new exports
    └── functions.py     # Function-based implementation
```

## Next Steps

1. **Review Examples**: Check `examples/function_based_approach.py`
2. **Run Tests**: Execute unit tests with `python3 tests/test_module_functions.py`
3. **Migration**: Use `migration_helper.py` for existing deployments
4. **Deploy**: Use the new approach in your `__main__.py`

The function-based approach provides a cleaner, more maintainable, and more testable codebase that follows Pulumi's idiomatic patterns.