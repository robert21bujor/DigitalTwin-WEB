"""
Business Development Department
==============================
Main entry point for the Business Development department with all specialized agents
"""

import logging
from typing import Dict, Any

import semantic_kernel as sk
from Core.Departments.department_base import BaseDepartment

logger = logging.getLogger(__name__)


class BusinessDevDepartment(BaseDepartment):
    """
    Business Development Department with IPM, BDM, and Presales divisions
    """
    
    def __init__(self, kernel: sk.Kernel):
        super().__init__("BusinessDev", kernel)
        
        # BusinessDev-specific attributes
        self.divisions = {
            "project_management": [],
            "partnership_development": [],
            "presales_engineering": []
        }
        
        # Track department metrics
        self.active_projects = 0
        self.partnerships_established = 0
        self.presales_engagements = 0
        self.board_meetings_coordinated = 0
        
    def setup_department(self) -> bool:
        """
        BusinessDev-specific setup logic
        """
        try:
            logger.info("Setting up Business Development department...")
            
            # Organize agents by division
            self._organize_agents_by_division()
            
            # Setup division-specific configurations
            self._setup_division_configs()
            
            # Initialize business development workflows
            self._setup_businessdev_workflows()
            
            logger.info("✅ Business Development department setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Business Development department setup failed: {e}")
            return False
    
    def _organize_agents_by_division(self):
        """Organize agents into their respective divisions"""
        for agent in self.agents:
            agent_type = type(agent).__name__.lower()
            
            if "ipm" in agent_type:
                self.divisions["project_management"].append(agent)
            elif "bdm" in agent_type:
                self.divisions["partnership_development"].append(agent)
            elif "presales" in agent_type:
                self.divisions["presales_engineering"].append(agent)
    
    def _setup_division_configs(self):
        """Setup configuration for each division"""
        # Project Management Configuration
        self.project_management_config = {
            "max_concurrent_projects": 10,
            "project_status_tracking": True,
            "milestone_notifications": True,
            "resource_allocation_enabled": True
        }
        
        # Partnership Development Configuration  
        self.partnership_config = {
            "partner_tier_system": ["Strategic", "Premium", "Standard"],
            "partnership_lifecycle_tracking": True,
            "revenue_sharing_calculator": True,
            "contract_management": True
        }
        
        # Presales Engineering Configuration
        self.presales_config = {
            "demo_environment_ready": True,
            "technical_documentation": True,
            "solution_architecture_tools": True,
            "poc_management": True
        }
    
    def setup_department(self) -> bool:
        """
        BusinessDev-specific setup logic
        """
        try:
            logger.info("Setting up BusinessDev department...")
            
            # Create and initialize agents
            self._create_businessdev_agents()
            
            # Organize agents by division
            self._organize_agents_by_division()
            
            # Setup division-specific configurations
            self._setup_businessdev_workflows()
            
            logger.info("✅ BusinessDev department setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ BusinessDev department setup failed: {e}")
            return False
    
    def _create_businessdev_agents(self):
        """Create and initialize BusinessDev agents"""
        try:
            from .Agents.ipm_agent import IPMAgent
            from .Agents.bdm_agent import BDMAgent
            from .Agents.presales_engineer_agent import PresalesEngineerAgent
            
            # Create agents
            agents = [
                IPMAgent("IPM Agent", "International Partnerships Manager", self.kernel),
                BDMAgent("BDM Agent", "Business Development Manager", self.kernel),
                PresalesEngineerAgent("Presales Engineer", "Technical Solution Designer", self.kernel),
            ]
            
            self.agents.extend(agents)
            logger.info(f"Created {len(agents)} BusinessDev agents")
            
        except Exception as e:
            logger.error(f"Error creating BusinessDev agents: {e}")
            raise
    
    def _organize_agents_by_division(self):
        """Organize agents into their respective divisions"""
        for agent in self.agents:
            agent_name = agent.name.lower()
            
            # Project Management agents
            if 'ipm' in agent_name or 'project' in agent_name:
                self.divisions["project_management"].append(agent)
                agent.division = "project_management"
                
            # Partnership Development agents  
            elif 'bdm' in agent_name or 'business development' in agent_name:
                self.divisions["partnership_development"].append(agent)
                agent.division = "partnership_development"
                
            # Presales Engineering agents
            elif 'presales' in agent_name or 'engineer' in agent_name:
                self.divisions["presales_engineering"].append(agent)
                agent.division = "presales_engineering"
        
        # Log division organization
        for division, agents in self.divisions.items():
            logger.info(f"📊 {division.replace('_', ' ').title()}: {len(agents)} agents")
    
    def _setup_businessdev_workflows(self):
        """Initialize BusinessDev-specific workflows"""
        workflows = {
            "partnership_pipeline": {
                "stages": ["Identification", "Initial Contact", "Evaluation", "Negotiation", "Agreement", "Onboarding"],
                "automated_transitions": True,
                "stakeholder_notifications": True
            },
            "project_lifecycle": {
                "phases": ["Initiation", "Planning", "Execution", "Monitoring", "Closure"],
                "milestone_tracking": True,
                "resource_allocation": True
            },
            "presales_process": {
                "steps": ["Qualification", "Discovery", "Demo", "Proposal", "Technical Evaluation", "Closure"],
                "technical_documentation": True,
                "solution_customization": True
            }
        }
        
        logger.info("BusinessDev workflows initialized")
        return workflows
    
    def get_department_status(self) -> Dict[str, Any]:
        """Get comprehensive department status"""
        return {
            "department": "BusinessDev",
            "active_agents": len(self.agents),
            "divisions": {
                "project_management": len(self.divisions["project_management"]),
                "partnership_development": len(self.divisions["partnership_development"]),
                "presales_engineering": len(self.divisions["presales_engineering"])
            },
            "metrics": {
                "active_projects": self.active_projects,
                "partnerships_established": self.partnerships_established,
                "presales_engagements": self.presales_engagements
            },
            "status": "operational" if len(self.agents) > 0 else "pending_agents"
        }
    
    def process_businessdev_request(self, request_type: str, content: str) -> Dict[str, Any]:
        """Process business development specific requests"""
        try:
            if request_type == "project_management":
                return self._handle_project_request(content)
            elif request_type == "partnership":
                return self._handle_partnership_request(content)
            elif request_type == "presales":
                return self._handle_presales_request(content)
            else:
                return {"error": f"Unknown request type: {request_type}"}
                
        except Exception as e:
            logger.error(f"Error processing BusinessDev request: {e}")
            return {"error": str(e)}
    
    def _handle_project_request(self, content: str) -> Dict[str, Any]:
        """Handle project management requests"""
        if self.divisions["project_management"]:
            agent = self.divisions["project_management"][0]
            # Route to IPM agent
            return {"routed_to": "IPM", "agent": agent.name, "content": content}
        return {"error": "No project management agents available"}
    
    def _handle_partnership_request(self, content: str) -> Dict[str, Any]:
        """Handle partnership development requests"""
        if self.divisions["partnership_development"]:
            agent = self.divisions["partnership_development"][0]
            # Route to BDM agent
            return {"routed_to": "BDM", "agent": agent.name, "content": content}
        return {"error": "No partnership development agents available"}
    
    def _handle_presales_request(self, content: str) -> Dict[str, Any]:
        """Handle presales engineering requests"""
        if self.divisions["presales_engineering"]:
            agent = self.divisions["presales_engineering"][0]
            # Route to Presales Engineer
            return {"routed_to": "Presales", "agent": agent.name, "content": content}
        return {"error": "No presales engineering agents available"}