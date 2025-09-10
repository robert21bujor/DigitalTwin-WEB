"""
New Department Example & Template
Copy this file and modify it to create new departments

INSTRUCTIONS:
1. Copy this file to: Departments/YourDepartmentName/your_department_name_department.py
   OR Departments/YourDepartmentName/your_department_name_agents.py
2. Copy department_config.yaml.template to: Departments/YourDepartmentName/department.yaml
3. Modify the class name: YourDepartmentNameDepartment OR YourDepartmentNameAgents
4. Modify the department_name in __init__: "YourDepartmentName"
5. Implement the setup_department() method with your specific logic
6. Add your agents to the agents/ folder
7. Update the department.yaml with your agents and configuration

The system will automatically discover and load your department!

QUICK START:
```bash
# Copy templates to create a new Sales department
cp -r Core/Templates/ Departments/Sales/
cd Departments/Sales/
mv new_department_example.py sales_department.py
mv department_config.yaml.template department.yaml

# Edit the files:
# 1. Change class name from TemplateDepartment to SalesDepartment
# 2. Change department name from "Template" to "Sales" 
# 3. Update department.yaml with your agents
```
"""

import logging
from typing import Dict, Any

import semantic_kernel as sk
from Core.Departments.department_base import BaseDepartment

logger = logging.getLogger(__name__)


class TemplateDepartment(BaseDepartment):
    """
    Template Department - Replace this with your department description
    """
    
    def __init__(self, kernel: sk.Kernel):
        # Replace "Template" with your department name (e.g., "Sales", "HR", "Finance")
        super().__init__("Template", kernel)
        
        # Add your department-specific attributes here
        self.custom_config = {}
        self.department_workflows = {}
        self.specialized_tools = {}
        
    def setup_department(self) -> bool:
        """
        Department-specific setup logic
        REQUIRED: You must implement this method
        """
        try:
            logger.info("Setting up Template department...")
            
            # Example setup steps - customize for your department:
            
            # 1. Configure department-specific settings
            self._setup_department_config()
            
            # 2. Initialize department workflows
            self._setup_workflows()
            
            # 3. Setup specialized tools or integrations
            self._setup_tools()
            
            # 4. Configure agent specializations
            self._configure_agents()
            
            logger.info("✅ Template department setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Template department setup failed: {e}")
            return False
    
    def _setup_department_config(self):
        """Setup department-specific configuration"""
        
        # Example configuration - customize for your department
        self.custom_config = {
            "department_policies": {
                "approval_required": True,
                "escalation_threshold": "high",
                "reporting_frequency": "weekly"
            },
            "integration_settings": {
                "external_apis": [],
                "database_connections": [],
                "notification_channels": []
            },
            "performance_metrics": [
                "task_completion_rate",
                "response_time",
                "quality_score"
            ]
        }
        
        logger.info("📋 Department configuration initialized")
    
    def _setup_workflows(self):
        """Setup department workflows"""
        
        # Example workflows - customize for your department
        self.department_workflows = {
            "standard_process": {
                "steps": ["intake", "analysis", "action", "review"],
                "agents_involved": ["agent1", "agent2"],
                "approval_required": True
            },
            "urgent_process": {
                "steps": ["immediate_action", "notify_manager"],
                "agents_involved": ["agent1"],
                "approval_required": False
            }
        }
        
        logger.info("🔄 Department workflows configured")
    
    def _setup_tools(self):
        """Setup specialized tools and integrations"""
        
        # Example tools - customize for your department
        self.specialized_tools = {
            "department_api": "configured",
            "reporting_system": "active",
            "notification_service": "enabled"
        }
        
        logger.info("🛠️ Specialized tools initialized")
    
    def _configure_agents(self):
        """Configure agent specializations"""
        
        # Example agent configuration - customize based on your agents
        for agent in self.agents:
            # Add department-specific attributes to agents
            agent.department_context = {
                "department": self.department_name,
                "workflows": self.department_workflows,
                "tools_access": self.specialized_tools
            }
        
        logger.info("🤖 Agent configurations applied")
    
    # Optional: Add department-specific methods
    
    def create_department_task(self, task_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Create a department-specific task"""
        task = {
            "id": f"TASK_{len(self.agents):04d}",
            "type": task_type,
            "department": self.department_name,
            "details": details,
            "workflow": self.department_workflows.get(task_type, self.department_workflows["standard_process"])
        }
        
        logger.info(f"🎯 Department task created: {task['id']}")
        return task
    
    def get_department_metrics(self) -> Dict[str, Any]:
        """Get department-specific metrics"""
        return {
            "total_agents": len(self.agents),
            "active_workflows": len(self.department_workflows),
            "tools_configured": len(self.specialized_tools),
            "configuration_status": bool(self.custom_config),
            "department_health": self.health_check()
        }
    
    def health_check(self) -> bool:
        """Department-specific health check"""
        base_health = super().health_check()
        
        # Add your department-specific health checks
        config_healthy = bool(self.custom_config)
        workflows_configured = bool(self.department_workflows)
        tools_ready = bool(self.specialized_tools)
        
        return base_health and config_healthy and workflows_configured and tools_ready
    
    def get_info(self) -> Dict[str, Any]:
        """Enhanced info with department-specific details"""
        base_info = super().get_info()
        base_info.update({
            "custom_config": self.custom_config,
            "workflows": list(self.department_workflows.keys()),
            "specialized_tools": list(self.specialized_tools.keys()),
            "department_metrics": self.get_department_metrics()
        })
        return base_info
    
    def shutdown(self):
        """Department-specific shutdown logic"""
        logger.info(f"Shutting down {self.department_name} department...")
        
        # Add any cleanup logic here
        # For example: close database connections, save state, etc.
        
        super().shutdown()


# EXAMPLE: How to create a new department
"""
1. Copy this file to: Departments/Sales/sales_department.py

2. Modify the class:
class SalesDepartment(BaseDepartment):
    def __init__(self, kernel: sk.Kernel):
        super().__init__("Sales", kernel)

3. Create department.yaml:
display_name: "Sales"
description: "Sales department with lead generation and conversion"
agents:
  - name: "LeadAgent"
    class: "LeadAgent"
    file: "agents/lead_agent.py"

4. Create agents/lead_agent.py with your agent implementation

5. The system will automatically discover and load your department!
""" 