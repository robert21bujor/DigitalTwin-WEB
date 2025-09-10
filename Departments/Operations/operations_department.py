"""
Operations Department
====================
Main entry point for the Operations department with all specialized sub-departments
"""

import logging
from typing import Dict, Any, List, Optional
import yaml
from pathlib import Path

import semantic_kernel as sk
from Core.Departments.department_base import BaseDepartment

logger = logging.getLogger(__name__)


class OperationsDepartment(BaseDepartment):
    """
    Operations Department with Legal, Client Success, Custom Reporting, and DC Support divisions
    """
    
    def __init__(self, kernel: sk.Kernel):
        super().__init__("Operations", kernel)
        
        # Operations-specific attributes
        self.subdepartments = {
            "legal": [],
            "client_success": [],
            "custom_reporting": [],
            "dc_support": []
        }
        
        # Track department metrics
        self.active_clients = 0
        self.legal_cases_handled = 0
        self.reports_generated = 0
        self.support_tickets_resolved = 0
        self.client_satisfaction_score = 0
        
    def setup_department(self) -> bool:
        """
        Operations-specific setup logic
        """
        try:
            logger.info("Setting up Operations department...")
            
            # Organize agents by subdepartment
            self._organize_agents_by_subdepartment()
            
            # Setup subdepartment-specific configurations
            self._setup_subdepartment_configs()
            
            # Initialize operations workflows
            self._setup_operations_workflows()
            
            logger.info("✅ Operations department setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Operations department setup failed: {e}")
            return False
    
    def _organize_agents_by_subdepartment(self):
        """Organize agents into their respective subdepartments"""
        for agent in self.agents:
            agent_type = type(agent).__name__.lower()
            
            if "legal" in agent_type:
                self.subdepartments["legal"].append(agent)
            elif any(term in agent_type for term in ["csm", "delivery", "head"]):
                self.subdepartments["client_success"].append(agent)
            elif "reporting" in agent_type:
                self.subdepartments["custom_reporting"].append(agent)
            elif "support" in agent_type or "intern" in agent_type:
                self.subdepartments["dc_support"].append(agent)
    
    def _setup_subdepartment_configs(self):
        """Setup configuration for each subdepartment"""
        # Legal Configuration
        self.legal_config = {
            "contract_management": True,
            "compliance_monitoring": True,
            "legal_document_templates": True,
            "risk_assessment_enabled": True
        }
        
        # Client Success Configuration  
        self.client_success_config = {
            "customer_health_scoring": True,
            "delivery_methodology": "Agile",
            "multi_language_support": ["EN", "BG", "HU"],
            "escalation_procedures": True,
            "client_onboarding_automated": True
        }
        
        # Custom Reporting Configuration
        self.reporting_config = {
            "real_time_dashboards": True,
            "automated_report_generation": True,
            "data_visualization_tools": True,
            "custom_kpi_tracking": True
        }
        
        # DC Support Configuration
        self.support_config = {
            "ticket_management_system": True,
            "knowledge_base_enabled": True,
            "escalation_matrix": True,
            "performance_tracking": True
        }
    
    def setup_department(self) -> bool:
        """
        Operations-specific setup logic
        """
        try:
            logger.info("Setting up Operations department...")
            
            # Create and initialize agents
            self._create_operations_agents()
            
            # Organize agents by subdepartment
            self._organize_agents_by_subdepartment()
            
            logger.info("✅ Operations department setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Operations department setup failed: {e}")
            return False
    
    def _create_operations_agents(self):
        """Create and initialize Operations agents"""
        try:
            # Import agents
            from .ClientSuccess.Agents.head_of_operations_agent import HeadOfOperationsAgent
            from .ClientSuccess.Agents.senior_csm_agent import SeniorCSMAgent
            from .ClientSuccess.Agents.senior_delivery_consultant_agent import SeniorDeliveryConsultantAgent
            from .ClientSuccess.Agents.delivery_consultant_bg_agent import DeliveryConsultantBGAgent
            from .ClientSuccess.Agents.delivery_consultant_hu_agent import DeliveryConsultantHUAgent
            from .ClientSuccess.Agents.delivery_consultant_en_agent import DeliveryConsultantENAgent
            from .CustomReporting.Agents.reporting_manager_agent import ReportingManagerAgent
            from .CustomReporting.Agents.reporting_specialist_agent import ReportingSpecialistAgent
            from .Legal.Agents.legal_agent import LegalAgent
            
            # Create agents
            agents = [
                HeadOfOperationsAgent("Head of Operations", "Strategic Operations Manager", self.kernel),
                SeniorCSMAgent("Senior Customer Success Manager", "Enterprise Account Manager", self.kernel),
                SeniorDeliveryConsultantAgent("Senior Delivery Consultant", "Complex Project Delivery Lead", self.kernel),
                DeliveryConsultantBGAgent("Delivery Consultant BG", "Bulgarian Market Specialist", self.kernel),
                DeliveryConsultantHUAgent("Delivery Consultant HU", "Hungarian Market Specialist", self.kernel),
                DeliveryConsultantENAgent("Delivery Consultant EN", "International Market Specialist", self.kernel),
                ReportingManagerAgent("Reporting Manager", "BI Strategy and Management", self.kernel),
                ReportingSpecialistAgent("Reporting Specialist", "Technical Report Developer", self.kernel),
                LegalAgent("Legal Agent", "Legal Compliance Specialist", self.kernel)
            ]
            
            self.agents.extend(agents)
            logger.info(f"Created {len(agents)} Operations agents")
            
        except Exception as e:
            logger.error(f"Error creating Operations agents: {e}")
            raise
    
    def _setup_operations_workflows(self):
        """Initialize Operations-specific workflows"""
        workflows = {
            "client_success_pipeline": {
                "stages": ["Onboarding", "Implementation", "Adoption", "Expansion", "Renewal"],
                "health_scoring": True,
                "automated_alerts": True
            },
            "legal_review_process": {
                "steps": ["Initial Review", "Risk Assessment", "Approval", "Documentation", "Monitoring"],
                "compliance_tracking": True,
                "document_management": True
            },
            "reporting_lifecycle": {
                "phases": ["Requirements", "Design", "Development", "Testing", "Delivery"],
                "quality_assurance": True,
                "stakeholder_approval": True
            },
            "support_ticket_flow": {
                "levels": ["L1 Support", "L2 Escalation", "L3 Specialist", "Management"],
                "sla_tracking": True,
                "customer_communication": True
            }
        }
        
        logger.info("Operations workflows initialized")
        return workflows
    
    def get_department_status(self) -> Dict[str, Any]:
        """Get comprehensive department status"""
        return {
            "department": "Operations",
            "active_agents": len(self.agents),
            "subdepartments": {
                "legal": len(self.subdepartments["legal"]),
                "client_success": len(self.subdepartments["client_success"]),
                "custom_reporting": len(self.subdepartments["custom_reporting"]),
                "dc_support": len(self.subdepartments["dc_support"])
            },
            "metrics": {
                "active_clients": self.active_clients,
                "legal_cases_handled": self.legal_cases_handled,
                "reports_generated": self.reports_generated,
                "support_tickets_resolved": self.support_tickets_resolved,
                "client_satisfaction_score": self.client_satisfaction_score
            },
            "status": "operational" if len(self.agents) > 0 else "pending_agents"
        }
    
    def process_operations_request(self, request_type: str, content: str) -> Dict[str, Any]:
        """Process operations specific requests"""
        try:
            if request_type == "legal":
                return self._handle_legal_request(content)
            elif request_type == "client_success":
                return self._handle_client_success_request(content)
            elif request_type == "reporting":
                return self._handle_reporting_request(content)
            elif request_type == "support":
                return self._handle_support_request(content)
            else:
                return {"error": f"Unknown request type: {request_type}"}
                
        except Exception as e:
            logger.error(f"Error processing Operations request: {e}")
            return {"error": str(e)}
    
    def _handle_legal_request(self, content: str) -> Dict[str, Any]:
        """Handle legal requests"""
        if self.subdepartments["legal"]:
            agent = self.subdepartments["legal"][0]
            return {"routed_to": "Legal", "agent": agent.name, "content": content}
        return {"error": "No legal agents available"}
    
    def _handle_client_success_request(self, content: str) -> Dict[str, Any]:
        """Handle client success requests"""
        if self.subdepartments["client_success"]:
            # Route to appropriate agent based on request priority
            agent = self.subdepartments["client_success"][0]  # Head of Operations first
            return {"routed_to": "ClientSuccess", "agent": agent.name, "content": content}
        return {"error": "No client success agents available"}
    
    def _handle_reporting_request(self, content: str) -> Dict[str, Any]:
        """Handle reporting requests"""
        if self.subdepartments["custom_reporting"]:
            # Prioritize Reporting Manager for complex requests
            agent = self.subdepartments["custom_reporting"][0]
            return {"routed_to": "Reporting", "agent": agent.name, "content": content}
        return {"error": "No reporting agents available"}
    
    def _handle_support_request(self, content: str) -> Dict[str, Any]:
        """Handle support requests"""
        if self.subdepartments["dc_support"]:
            agent = self.subdepartments["dc_support"][0]
            return {"routed_to": "Support", "agent": agent.name, "content": content}
        return {"error": "No support agents available"} 