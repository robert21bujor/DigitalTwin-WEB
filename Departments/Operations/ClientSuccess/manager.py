"""
Client Success Manager
======================

Manages client success and delivery consulting operations including:
- Customer success management and coordination
- Delivery consulting team oversight
- Client relationship management
- Implementation project coordination
- Quality assurance and client satisfaction
"""

import logging
from typing import List, Optional
import semantic_kernel as sk

from Core.Agents.agent import Agent
from Core.Agents.manager import Manager
from Core.Tasks.task import Task

# Import ClientSuccess agents
from .Agents.head_of_operations_agent import HeadOfOperationsAgent
from .Agents.senior_csm_agent import SeniorCSMAgent
from .Agents.senior_delivery_consultant_agent import SeniorDeliveryConsultantAgent
from .Agents.delivery_consultant_bg_agent import DeliveryConsultantBGAgent
from .Agents.delivery_consultant_hu_agent import DeliveryConsultantHUAgent
from .Agents.delivery_consultant_en_agent import DeliveryConsultantENAgent

# Configure logger
logger = logging.getLogger("client_success_manager")


class ClientSuccessManager(Manager):
    """
    Client Success Manager - Oversees customer success and delivery consulting
    focused on client satisfaction and successful project delivery.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel, team_members: List[Agent] = None):
        super().__init__(name, role, kernel, team_members or [])
        
        # Initialize Client Success team if not provided
        if not self.team_members:
            self._initialize_client_success_team()
        
        logger.info(f"Client Success Manager initialized with {len(self.team_members)} agents")
    
    def _initialize_client_success_team(self):
        """Initialize the complete Client Success team"""
        try:
            # Create Client Success agents
            self.team_members = [
                HeadOfOperationsAgent(
                    name="Head of Operations",
                    role="Strategic Operations Manager", 
                    kernel=self.kernel
                ),
                SeniorCSMAgent(
                    name="Senior Customer Success Manager",
                    role="Enterprise Account Manager",
                    kernel=self.kernel
                ),
                SeniorDeliveryConsultantAgent(
                    name="Senior Delivery Consultant",
                    role="Complex Project Delivery Lead",
                    kernel=self.kernel
                ),
                DeliveryConsultantBGAgent(
                    name="Delivery Consultant BG",
                    role="Bulgarian Market Specialist",
                    kernel=self.kernel
                ),
                DeliveryConsultantHUAgent(
                    name="Delivery Consultant HU",
                    role="Hungarian Market Specialist",
                    kernel=self.kernel
                ),
                DeliveryConsultantENAgent(
                    name="Delivery Consultant EN",
                    role="International Market Specialist",
                    kernel=self.kernel
                )
            ]
            
            logger.info(f"Initialized {len(self.team_members)} Client Success agents")
            
        except Exception as e:
            logger.error(f"Error initializing Client Success team: {str(e)}")
            self.team_members = []
    
    def route_client_request(self, request_type: str, language: str, content: str) -> dict:
        """Route client requests to appropriate agent based on type and language"""
        try:
            if not self.team_members:
                return {"error": "No client success agents available"}
            
            # Route based on request type and language
            if request_type in ["strategy", "operations", "escalation"]:
                head_ops = next((agent for agent in self.team_members if "Head of Operations" in agent.name), None)
                return {
                    "routed_to": "Strategic Operations",
                    "agent": head_ops.name if head_ops else "Head of Operations",
                    "content": content,
                    "specialization": "Strategic operations management"
                }
            
            elif request_type in ["account", "customer", "csm", "relationship"]:
                senior_csm = next((agent for agent in self.team_members if "Senior Customer Success" in agent.name), None)
                return {
                    "routed_to": "Customer Success Management",
                    "agent": senior_csm.name if senior_csm else "Senior CSM",
                    "content": content,
                    "specialization": "Enterprise account management"
                }
            
            elif request_type in ["delivery", "project", "implementation"]:
                # Route based on language/market
                if language.lower() in ["bg", "bulgarian"]:
                    bg_consultant = next((agent for agent in self.team_members if "BG" in agent.name), None)
                    return {
                        "routed_to": "Bulgarian Delivery",
                        "agent": bg_consultant.name if bg_consultant else "Delivery Consultant BG",
                        "content": content,
                        "specialization": "Bulgarian market implementation"
                    }
                elif language.lower() in ["hu", "hungarian"]:
                    hu_consultant = next((agent for agent in self.team_members if "HU" in agent.name), None)
                    return {
                        "routed_to": "Hungarian Delivery",
                        "agent": hu_consultant.name if hu_consultant else "Delivery Consultant HU",
                        "content": content,
                        "specialization": "Hungarian market implementation"
                    }
                elif language.lower() in ["en", "english", "international"]:
                    en_consultant = next((agent for agent in self.team_members if "EN" in agent.name), None)
                    return {
                        "routed_to": "International Delivery",
                        "agent": en_consultant.name if en_consultant else "Delivery Consultant EN",
                        "content": content,
                        "specialization": "International market implementation"
                    }
                else:
                    # Default to senior delivery consultant for complex projects
                    senior_delivery = next((agent for agent in self.team_members if "Senior Delivery" in agent.name), None)
                    return {
                        "routed_to": "Complex Project Delivery",
                        "agent": senior_delivery.name if senior_delivery else "Senior Delivery Consultant",
                        "content": content,
                        "specialization": "Complex project delivery leadership"
                    }
            
            else:
                # Default routing to head of operations
                head_ops = next((agent for agent in self.team_members if "Head of Operations" in agent.name), None)
                return {
                    "routed_to": "General Client Success",
                    "agent": head_ops.name if head_ops else "Head of Operations",
                    "content": content,
                    "specialization": "General client success coordination"
                }
                
        except Exception as e:
            logger.error(f"Error routing client request: {e}")
            return {"error": str(e)}
    
    def get_team_capabilities(self) -> dict:
        """Get comprehensive team capabilities"""
        return {
            "team_size": len(self.team_members),
            "language_support": ["English", "Bulgarian", "Hungarian"],
            "specializations": {
                "Strategic Operations": "Overall operations management and strategic oversight",
                "Customer Success": "Enterprise client relationship management",
                "Senior Delivery": "Complex project delivery leadership",
                "Bulgarian Market": "Localized Bulgarian implementation support",
                "Hungarian Market": "Localized Hungarian implementation support", 
                "International Market": "Global English-speaking market support"
            },
            "service_areas": [
                "Strategic operations planning",
                "Customer success management",
                "Project delivery consulting",
                "Multi-language implementation support",
                "Cultural adaptation and localization",
                "Quality assurance and compliance"
            ],
            "status": "operational" if len(self.team_members) > 0 else "no_agents"
        }
    
    def escalate_client_issue(self, severity: str, client_type: str, issue_details: str) -> dict:
        """Escalate client issues based on severity and type"""
        escalation_matrix = {
            "low": "Standard resolution process",
            "medium": "Priority attention required",
            "high": "Immediate senior consultant involvement",
            "critical": "Head of Operations emergency response"
        }
        
        # Determine appropriate escalation agent
        if severity in ["critical", "high"]:
            escalation_agent = "Head of Operations"
        elif client_type == "enterprise":
            escalation_agent = "Senior Customer Success Manager"
        else:
            escalation_agent = "Senior Delivery Consultant"
        
        return {
            "escalation_level": severity,
            "handling_protocol": escalation_matrix.get(severity, "Standard"),
            "assigned_agent": escalation_agent,
            "client_type": client_type,
            "response_time": {
                "low": "3 business days",
                "medium": "1 business day",
                "high": "4 hours",
                "critical": "Within 1 hour"
            }.get(severity, "Standard timing"),
            "issue_details": issue_details
        } 