"""
Department Registry System
Auto-discovers and manages departments and their agents
"""

import os
import yaml
import importlib
import logging
from typing import Dict, List, Any, Type, Optional
from pathlib import Path

import semantic_kernel as sk
from Core.Agents.agent import Agent
from Core.Agents.manager import Manager

logger = logging.getLogger(__name__)


class DepartmentConfig:
    """Configuration for a department"""
    
    def __init__(self, name: str, config_data: Dict[str, Any]):
        self.name = name
        self.display_name = config_data.get('display_name', name.title())
        self.description = config_data.get('description', '')
        self.manager_name = config_data.get('manager_name', f'{name.title()}Manager')
        self.agents = config_data.get('agents', [])
        self.memory_collection = config_data.get('memory_collection', f'{name.lower()}-memory')
        self.skills = config_data.get('skills', [])
        self.routing_keywords = config_data.get('routing_keywords', [])


class GenericDepartmentManager(Manager):
    """Generic manager that works with any department configuration"""
    
    def __init__(self, department_config: DepartmentConfig, kernel: sk.Kernel, agents: List[Agent]):
        super().__init__(
            name=department_config.manager_name,
            role=f"{department_config.display_name} Manager",
            kernel=kernel,
            team_members=agents
        )
        self.department_config = department_config
        self.department_name = department_config.name


class DepartmentRegistry:
    """Registry that auto-discovers and manages all departments"""
    
    def __init__(self, departments_path: str = "Departments"):
        self.departments_path = Path(departments_path)
        self.departments: Dict[str, DepartmentConfig] = {}
        self.managers: Dict[str, GenericDepartmentManager] = {}
        self.agents: Dict[str, List[Agent]] = {}
        
    def discover_departments(self) -> Dict[str, DepartmentConfig]:
        """Auto-discover all departments from the filesystem"""
        discovered = {}
        
        if not self.departments_path.exists():
            logger.warning(f"Departments path {self.departments_path} does not exist")
            return discovered
        
        for dept_path in self.departments_path.iterdir():
            if dept_path.is_dir() and not dept_path.name.startswith('.'):
                config_file = dept_path / 'department.yaml'
                
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config_data = yaml.safe_load(f)
                        
                        dept_config = DepartmentConfig(dept_path.name, config_data)
                        discovered[dept_path.name] = dept_config
                        logger.info(f"Discovered department: {dept_config.display_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to load department config for {dept_path.name}: {e}")
                else:
                    logger.debug(f"No department.yaml found in {dept_path.name}, skipping")
        
        return discovered
    
    def load_department_agents(self, dept_name: str, dept_config: DepartmentConfig, kernel: sk.Kernel) -> List[Agent]:
        """Load all agents for a department"""
        agents = []
        dept_path = self.departments_path / dept_name
        agents_path = dept_path / 'agents'
        
        # If there's a dedicated agents folder, look there
        if agents_path.exists():
            search_path = agents_path
        else:
            # Otherwise look in the department root
            search_path = dept_path
        
        for agent_config in dept_config.agents:
            agent_name = agent_config['name']
            agent_class = agent_config['class']
            agent_file = agent_config.get('file', f"{agent_name.lower()}.py")
            
            try:
                # Build module path from file path
                # Convert file path like "content_marketing/agents/content_agent.py" to module path
                module_parts = agent_file[:-3].replace('/', '.')  # Remove .py and convert slashes
                module_path = f"Departments.{dept_name}.{module_parts}"
                
                # Import the module
                module = importlib.import_module(module_path)
                
                # Get the agent class
                agent_cls = getattr(module, agent_class)
                
                # Instantiate the agent
                agent = agent_cls(kernel)
                agents.append(agent)
                
                logger.info(f"Loaded agent: {agent_name} from {dept_name}")
                
            except Exception as e:
                logger.error(f"Failed to load agent {agent_name} from {dept_name}: {e}")
        
        return agents
    
    def initialize_departments(self, kernel: sk.Kernel) -> Dict[str, GenericDepartmentManager]:
        """Initialize all discovered departments"""
        self.departments = self.discover_departments()
        
        for dept_name, dept_config in self.departments.items():
            try:
                # Load agents for this department
                agents = self.load_department_agents(dept_name, dept_config, kernel)
                self.agents[dept_name] = agents
                
                # Create manager for this department
                manager = GenericDepartmentManager(dept_config, kernel, agents)
                self.managers[dept_name] = manager
                
                logger.info(f"Initialized department: {dept_config.display_name} with {len(agents)} agents")
                
            except Exception as e:
                logger.error(f"Failed to initialize department {dept_name}: {e}")
        
        return self.managers
    
    def get_department_by_keywords(self, text: str) -> Optional[str]:
        """Find the best department match based on routing keywords"""
        text_lower = text.lower()
        
        for dept_name, dept_config in self.departments.items():
            for keyword in dept_config.routing_keywords:
                if keyword.lower() in text_lower:
                    return dept_name
        
        return None
    
    def get_all_departments(self) -> Dict[str, DepartmentConfig]:
        """Get all department configurations"""
        return self.departments
    
    def get_department_manager(self, dept_name: str) -> Optional[GenericDepartmentManager]:
        """Get manager for a specific department"""
        return self.managers.get(dept_name)
    
    def get_department_agents(self, dept_name: str) -> List[Agent]:
        """Get all agents for a specific department"""
        return self.agents.get(dept_name, []) 