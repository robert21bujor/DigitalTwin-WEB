# Department Templates

This directory contains templates for creating new departments in the AI Company System.

## 📁 Files

- **`new_department_example.py`** - Complete example of a department implementation
- **`department_config.yaml.template`** - YAML configuration template
- **`README.md`** - This file

## 🚀 Quick Start

Create a new department in 3 simple steps:

```bash
# 1. Copy templates
cp -r Core/Templates/ Departments/YourDepartment/
cd Departments/YourDepartment/

# 2. Rename files  
mv new_department_example.py your_department_department.py
mv department_config.yaml.template department.yaml

# 3. Edit files
# - Change class name: YourDepartmentDepartment
# - Update department name: "YourDepartment"
# - Configure agents in department.yaml
```

## 📖 What Each File Does

### `new_department_example.py`
- Extends `BaseDepartment` from `Core/department_base.py`
- Shows how to implement `setup_department()` method
- Includes examples of workflows, tools, and configurations
- Demonstrates department-specific methods and health checks

### `department_config.yaml.template`
- Defines department metadata (name, description, skills)
- Lists agents to load (name, class, file path)
- Specifies routing keywords for task assignment
- Configures department-specific settings

## 🏗️ Architecture

```
Core/
├── department_base.py          # Abstract base class (framework)
└── templates/                  # Templates for new departments
    ├── new_department_example.py    # Concrete implementation example
    └── department_config.yaml.template    # Configuration template
```

The system automatically discovers departments by:
1. Looking for `*_department.py` or `*_agents.py` files
2. Loading the corresponding `department.yaml` configuration
3. Initializing agents and managers based on the configuration

## 💡 Tips

- Department names should be PascalCase (e.g., "Sales", "HumanResources")
- Agent files go in `agents/` subdirectory within your department
- Use meaningful routing keywords to help with task assignment
- Implement health checks for monitoring department status 