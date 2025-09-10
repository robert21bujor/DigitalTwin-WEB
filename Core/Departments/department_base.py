"""
Base Department Template
All departments should extend this base class
"""

import yaml
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path

import semantic_kernel as sk
from Core.Agents.agent import Agent
from Core.Agents.manager import Manager
from Core.Departments.department_registry import DepartmentConfig, GenericDepartmentManager

logger = logging.getLogger(__name__)


class BaseDepartment(ABC):
    """
    Base template class that all departments should extend
    Provides common functionality and enforces department structure
    """
    
    def __init__(self, department_name: str, kernel: sk.Kernel):
        self.department_name = department_name
        self.kernel = kernel
        self.department_path = Path(f"Departments/{department_name}")
        self.config: Optional[DepartmentConfig] = None
        self.manager: Optional[GenericDepartmentManager] = None
        self.agents: List[Agent] = []
        self.initialized = False
        
        # Load department configuration
        self._load_config()
    
    def _load_config(self):
        """Load department configuration from YAML file"""
        config_file = self.department_path / "department.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Department config not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            self.config = DepartmentConfig(self.department_name, config_data)
            logger.info(f"Loaded config for {self.config.display_name} department")
            
        except Exception as e:
            logger.error(f"Failed to load department config: {e}")
            raise
    
    @abstractmethod
    def setup_department(self) -> bool:
        """
        Department-specific setup logic
        Must be implemented by each department
        Returns True if setup successful, False otherwise
        """
        pass
    
    def initialize(self) -> bool:
        """
        Initialize the department with agents and manager
        This is the main initialization method called by the system
        """
        try:
            logger.info(f"Initializing {self.config.display_name} department...")
            
            # Load agents
            self.agents = self._load_agents()
            
            # Create manager
            self.manager = GenericDepartmentManager(self.config, self.kernel, self.agents)
            
            # Run department-specific setup
            setup_success = self.setup_department()
            
            if setup_success:
                self.initialized = True
                logger.info(f"✅ {self.config.display_name} department initialized successfully")
                return True
            else:
                logger.error(f"❌ {self.config.display_name} department setup failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize {self.config.display_name} department: {e}")
            return False
    
    def _load_agents(self) -> List[Agent]:
        """Load all agents for this department"""
        agents = []
        
        for agent_config in self.config.agents:
            agent_name = agent_config['name']
            agent_class = agent_config['class']
            agent_file = agent_config.get('file', f"{agent_name.lower()}.py")
            
            try:
                # Build module path from file path
                module_parts = agent_file[:-3].replace('/', '.')
                module_path = f"Departments.{self.department_name}.{module_parts}"
                
                # Import the module
                import importlib
                module = importlib.import_module(module_path)
                
                # Get the agent class
                agent_cls = getattr(module, agent_class)
                
                # Instantiate the agent
                agent = agent_cls(self.kernel)
                agents.append(agent)
                
                logger.info(f"✅ Loaded agent: {agent_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to load agent {agent_name}: {e}")
        
        return agents
    
    def get_info(self) -> Dict[str, Any]:
        """Get department information"""
        return {
            "name": self.department_name,
            "display_name": self.config.display_name if self.config else "Unknown",
            "description": self.config.description if self.config else "",
            "agent_count": len(self.agents),
            "agents": [agent.name for agent in self.agents],
            "manager": self.manager.name if self.manager else None,
            "initialized": self.initialized,
            "skills": self.config.skills if self.config else [],
            "routing_keywords": self.config.routing_keywords if self.config else []
        }
    
    def get_manager(self) -> Optional[GenericDepartmentManager]:
        """Get department manager"""
        return self.manager
    
    def get_agents(self) -> List[Agent]:
        """Get all department agents"""
        return self.agents
    
    def is_initialized(self) -> bool:
        """Check if department is properly initialized"""
        return self.initialized
    
    def shutdown(self):
        """Clean shutdown of department resources"""
        logger.info(f"Shutting down {self.config.display_name} department")
        # Override in subclasses if needed
        pass
    
    # Optional methods that departments can override
    def pre_initialize_hook(self):
        """Called before initialization - override if needed"""
        pass
    
    def post_initialize_hook(self):
        """Called after successful initialization - override if needed"""
        pass
    
    def health_check(self) -> bool:
        """Health check for the department - override if needed"""
        return self.initialized and self.manager is not None and len(self.agents) > 0 