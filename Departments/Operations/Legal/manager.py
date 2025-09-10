"""
Legal Manager
=============

Manages legal operations and compliance activities including:
- Legal team coordination and oversight
- Compliance program management
- Risk assessment and mitigation
- Contract management and review
- Legal strategy and planning
"""

import logging
from typing import List, Optional
import semantic_kernel as sk

from Core.Agents.agent import Agent
from Core.Agents.manager import Manager
from Core.Tasks.task import Task

# Import Legal agents
from .Agents.legal_agent import LegalAgent

# Configure logger
logger = logging.getLogger("legal_manager")


class LegalManager(Manager):
    """
    Legal Manager - Oversees legal operations and compliance
    focused on organizational protection and regulatory adherence.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel, team_members: List[Agent] = None):
        super().__init__(name, role, kernel, team_members or [])
        
        # Initialize Legal team if not provided
        if not self.team_members:
            self._initialize_legal_team()
        
        logger.info(f"Legal Manager initialized with {len(self.team_members)} agents")
    
    def _initialize_legal_team(self):
        """Initialize the complete Legal team"""
        try:
            # Create Legal agents
            self.team_members = [
                LegalAgent(
                    name="Legal Agent",
                    role="Legal Counsel and Compliance Specialist", 
                    kernel=self.kernel
                )
            ]
            
            logger.info(f"Initialized {len(self.team_members)} Legal agents")
            
        except Exception as e:
            logger.error(f"Error initializing Legal team: {str(e)}")
            self.team_members = []
    
    def handle_legal_request(self, request_type: str, content: str) -> dict:
        """Handle legal requests and route to appropriate agent"""
        try:
            if self.team_members:
                legal_agent = self.team_members[0]  # Primary legal agent
                
                # Route different types of legal requests
                if request_type in ["contract", "agreement", "terms"]:
                    return {
                        "routed_to": "Contract Management",
                        "agent": legal_agent.name,
                        "content": content,
                        "specialization": "Contract drafting and review"
                    }
                elif request_type in ["compliance", "regulation", "gdpr"]:
                    return {
                        "routed_to": "Compliance Assessment",
                        "agent": legal_agent.name,
                        "content": content,
                        "specialization": "Regulatory compliance monitoring"
                    }
                elif request_type in ["risk", "liability", "mitigation"]:
                    return {
                        "routed_to": "Risk Management",
                        "agent": legal_agent.name,
                        "content": content,
                        "specialization": "Legal risk assessment and mitigation"
                    }
                elif request_type in ["ip", "intellectual property", "patent", "trademark"]:
                    return {
                        "routed_to": "Intellectual Property",
                        "agent": legal_agent.name,
                        "content": content,
                        "specialization": "IP protection and management"
                    }
                elif request_type in ["dispute", "litigation", "conflict"]:
                    return {
                        "routed_to": "Dispute Resolution",
                        "agent": legal_agent.name,
                        "content": content,
                        "specialization": "Dispute resolution and litigation support"
                    }
                else:
                    return {
                        "routed_to": "General Legal",
                        "agent": legal_agent.name,
                        "content": content,
                        "specialization": "General legal guidance and support"
                    }
            else:
                return {"error": "No legal agents available"}
                
        except Exception as e:
            logger.error(f"Error handling legal request: {e}")
            return {"error": str(e)}
    
    def get_team_status(self) -> dict:
        """Get comprehensive Legal team status"""
        if not self.team_members:
            return {"status": "no_agents", "team_size": 0}
        
        legal_agent = self.team_members[0]
        
        return {
            "team_size": len(self.team_members),
            "primary_agent": legal_agent.name,
            "specializations": [
                "Contract Management",
                "Regulatory Compliance",
                "Risk Assessment",
                "Intellectual Property",
                "Dispute Resolution"
            ],
            "status": "operational"
        }
    
    def escalate_legal_matter(self, matter_type: str, urgency: str, details: str) -> dict:
        """Escalate urgent legal matters"""
        escalation_levels = {
            "low": "Standard legal review process",
            "medium": "Priority legal attention required",
            "high": "Immediate legal intervention needed",
            "critical": "Emergency legal response required"
        }
        
        return {
            "escalation_level": urgency,
            "handling_protocol": escalation_levels.get(urgency, "Standard"),
            "matter_type": matter_type,
            "assigned_agent": self.team_members[0].name if self.team_members else "No agent available",
            "response_time": {
                "low": "5 business days",
                "medium": "2 business days", 
                "high": "Same business day",
                "critical": "Within 2 hours"
            }.get(urgency, "Standard timing"),
            "details": details
        } 