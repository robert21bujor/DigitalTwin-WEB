"""
Company System
Auto-discovers and manages all departments using the template system
"""

import os
import importlib
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

import semantic_kernel as sk
from Core.Departments.department_base import BaseDepartment

# Import departments
from Departments.Marketing.marketing_department import MarketingDepartment
from Departments.Executive import ExecutiveAgents

logger = logging.getLogger("company_system")


class CompanySystem:
    """
    Main company system that auto-discovers and manages all departments
    """
    
    def __init__(self, kernel: sk.Kernel):
        self.kernel = kernel
        self.departments: Dict[str, BaseDepartment] = {}
        self.initialized = False
        self.company_metrics = {}
        
    def discover_departments(self) -> Dict[str, str]:
        """
        Auto-discover all departments by looking for department files
        Returns dict of {department_name: module_path}
        """
        discovered = {}
        departments_path = Path("Departments")
        
        if not departments_path.exists():
            logger.warning("Departments directory not found")
            return discovered
        
        for dept_path in departments_path.iterdir():
            if dept_path.is_dir() and not dept_path.name.startswith('.'):
                dept_name = dept_path.name
                
                # Look for department main file
                possible_files = [
                    f"{dept_name.lower()}_department.py",
                    f"{dept_name}_department.py",
                    f"{dept_name.lower()}_agents.py",
                    f"{dept_name}_agents.py",
                    "department.py",
                    "main.py"
                ]
                
                for file_name in possible_files:
                    dept_file = dept_path / file_name
                    if dept_file.exists():
                        module_path = f"Departments.{dept_name}.{file_name[:-3]}"
                        discovered[dept_name] = module_path
                        logger.info(f"📁 Discovered department: {dept_name}")
                        break
                else:
                    logger.debug(f"No department file found for {dept_name}")
        
        return discovered
    
    def load_department(self, dept_name: str, module_path: str) -> Optional[BaseDepartment]:
        """Load a specific department from its module path"""
        try:
            # Import the department module
            module = importlib.import_module(module_path)
            
            # Look for department class (should end with 'Department' or 'Agents')
            possible_class_names = [
                f"{dept_name}Department",
                f"{dept_name}Agents"
            ]
            
            dept_class = None
            for class_name in possible_class_names:
                if hasattr(module, class_name):
                    dept_class = getattr(module, class_name)
                    break
            
            if dept_class:
                # Instantiate the department
                department = dept_class(self.kernel)
                
                logger.info(f"✅ Loaded department: {dept_name}")
                return department
            else:
                logger.error(f"❌ Department class not found in {module_path}. Expected: {possible_class_names}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to load department {dept_name}: {e}")
            return None
    
    def initialize_all_departments(self) -> bool:
        """Initialize all discovered departments"""
        try:
            logger.info("🚀 Initializing Company System...")
            
            # Discover all departments
            discovered_departments = self.discover_departments()
            
            if not discovered_departments:
                logger.warning("⚠️ No departments discovered")
                return False
            
            # Load and initialize each department
            success_count = 0
            for dept_name, module_path in discovered_departments.items():
                logger.info(f"🔄 Loading {dept_name} department...")
                
                # Load department
                department = self.load_department(dept_name, module_path)
                
                if department:
                    # Initialize department
                    if department.initialize():
                        self.departments[dept_name] = department
                        success_count += 1
                        logger.info(f"✅ {dept_name} department initialized successfully")
                    else:
                        logger.error(f"❌ Failed to initialize {dept_name} department")
                else:
                    logger.error(f"❌ Failed to load {dept_name} department")
            
            # Initialize Executive department (oversight)
            executive_dept = ExecutiveAgents(self.kernel)
            if executive_dept.initialize():
                self.departments["Executive"] = executive_dept
                success_count += 1
                logger.info(f"✅ Executive department initialized successfully")
            
            # Check if we have at least one successful department
            if success_count > 0:
                self.initialized = True
                logger.info(f"🎉 Company System initialized with {success_count}/{len(discovered_departments)} departments")
                
                # Generate company metrics
                self._generate_company_metrics()
                
                return True
            else:
                logger.error("❌ No departments could be initialized")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize company system: {e}")
            return False
    
    def _generate_company_metrics(self):
        """Generate company-wide metrics"""
        total_agents = sum(len(dept.get_agents()) for dept in self.departments.values())
        total_managers = len([dept for dept in self.departments.values() if dept.get_manager()])
        
        self.company_metrics = {
            "total_departments": len(self.departments),
            "total_agents": total_agents,
            "total_managers": total_managers,
            "departments_initialized": len([dept for dept in self.departments.values() if dept.is_initialized()]),
            "company_health": self.get_company_health_score()
        }
        
        logger.info(f"📊 Company Metrics: {total_agents} agents across {len(self.departments)} departments")
    
    def get_department(self, dept_name: str) -> Optional[BaseDepartment]:
        """Get a specific department"""
        return self.departments.get(dept_name)
    
    def get_all_departments(self) -> Dict[str, BaseDepartment]:
        """Get all departments"""
        return self.departments
    
    def get_department_by_keywords(self, text: str) -> Optional[str]:
        """Find department based on keywords in text"""
        text_lower = text.lower()
        
        for dept_name, department in self.departments.items():
            if department.config and department.config.routing_keywords:
                for keyword in department.config.routing_keywords:
                    if keyword.lower() in text_lower:
                        return dept_name
        
        return None
    
    def get_company_health_score(self) -> float:
        """Calculate overall company health score"""
        if not self.departments:
            return 0.0
        
        healthy_departments = sum(1 for dept in self.departments.values() if dept.health_check())
        return (healthy_departments / len(self.departments)) * 100
    
    def get_company_dashboard(self) -> Dict[str, Any]:
        """Get company-wide dashboard"""
        return {
            "company_metrics": self.company_metrics,
            "departments": {
                dept_name: {
                    "name": dept.config.display_name if dept.config else dept_name,
                    "agents": len(dept.get_agents()),
                    "initialized": dept.is_initialized(),
                    "health": dept.health_check()
                }
                for dept_name, dept in self.departments.items()
            },
            "system_status": {
                "initialized": self.initialized,
                "health_score": self.get_company_health_score(),
                "total_departments": len(self.departments)
            }
        }
    
    def route_task_to_department(self, task_description: str) -> Optional[str]:
        """Route a task to the appropriate department based on keywords"""
        return self.get_department_by_keywords(task_description)
    
    def get_all_agents(self) -> List:
        """Get all agents across all departments"""
        all_agents = []
        for department in self.departments.values():
            all_agents.extend(department.get_agents())
        return all_agents
    
    def get_all_managers(self) -> List:
        """Get all managers across all departments"""
        managers = []
        for department in self.departments.values():
            manager = department.get_manager()
            if manager:
                managers.append(manager)
        return managers
    
    def shutdown_all_departments(self):
        """Gracefully shutdown all departments"""
        logger.info("🔄 Shutting down all departments...")
        
        for dept_name, department in self.departments.items():
            try:
                department.shutdown()
                logger.info(f"✅ {dept_name} department shut down")
            except Exception as e:
                logger.error(f"❌ Failed to shutdown {dept_name}: {e}")
        
        logger.info("🏁 Company system shutdown complete")
    
    def is_initialized(self) -> bool:
        """Check if company system is initialized"""
        return self.initialized
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive company information"""
        return {
            "company_system": {
                "initialized": self.initialized,
                "total_departments": len(self.departments),
                "health_score": self.get_company_health_score()
            },
            "departments": {
                dept_name: dept.get_info() 
                for dept_name, dept in self.departments.items()
            },
            "metrics": self.company_metrics,
            "dashboard": self.get_company_dashboard()
        } 
    
    # =======================================================================
    # COMPATIBILITY METHODS FOR EXISTING CHAT INTERFACES
    # These methods provide backwards compatibility with the old MarketingSystem
    # =======================================================================
    
    async def create_task(self, task_description: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        Create task compatible with existing chat interface expectations
        Routes task to appropriate department and generates a task ID
        """
        try:
            # Generate unique task ID
            task_id = f"TASK_{len(self.departments):04d}_{hash(task_description) % 10000:04d}"
            
            # Route to appropriate department
            department_name = self.route_task_to_department(task_description)
            
            if department_name and department_name in self.departments:
                department = self.departments[department_name]
                
                # For now, log the task (in future, departments can handle task creation)
                priority = context.get("priority", "medium") if context else "medium"
                created_by = context.get("created_by", "system") if context else "system"
                
                logger.info(f"TASK_CREATED | {task_id} | Department: {department_name} | Priority: {priority.upper()} | Created by: {created_by} | Description: {task_description[:100]}...")
                
                return task_id
            else:
                logger.warning(f"Could not route task: {task_description[:50]}... | Available departments: {list(self.departments.keys())}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get system status compatible with existing chat interface expectations
        Returns status in the format expected by chat interfaces
        """
        try:
            dashboard = self.get_company_dashboard()
            
            # For compatibility, provide task counts (simplified version)
            # In the future, departments can track actual tasks
            total_agents = dashboard["company_metrics"]["total_agents"]
            
            return {
                "active_tasks": 0,  # Would be tracked by departments in full implementation
                "completed_tasks": 0,  # Would be tracked by departments in full implementation
                "pending_tasks": 0,  # Would be tracked by departments in full implementation
                "total_departments": dashboard["company_metrics"]["total_departments"],
                "total_agents": total_agents,
                "health_score": dashboard["system_status"]["health_score"],
                "departments_status": {
                    dept_name: {
                        "name": dept_info["name"],
                        "agents": dept_info["agents"],
                        "health": "✅" if dept_info["health"] else "❌"
                    }
                    for dept_name, dept_info in dashboard["departments"].items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "active_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "error": str(e)
            }
    
    def stop_memory_sync(self):
        """
        Stop memory sync - compatibility method for existing interfaces
        In the new system, memory sync is handled per department
        """
        try:
            # Attempt to stop memory sync across all departments
            for department in self.departments.values():
                # If department has memory sync functionality, stop it
                if hasattr(department, 'stop_memory_sync'):
                    department.stop_memory_sync()
                    
            logger.info("Memory sync stopped across all departments")
            
        except Exception as e:
            logger.warning(f"Error stopping memory sync: {e}")
    
    async def start_memory_sync(self):
        """
        Start memory sync - compatibility method for existing interfaces
        In the new system, memory sync is handled per department
        """
        try:
            # Attempt to start memory sync across all departments
            for department in self.departments.values():
                # If department has memory sync functionality, start it
                if hasattr(department, 'start_memory_sync'):
                    await department.start_memory_sync()
                    
            logger.info("Memory sync started across all departments")
            
        except Exception as e:
            logger.warning(f"Error starting memory sync: {e}") 