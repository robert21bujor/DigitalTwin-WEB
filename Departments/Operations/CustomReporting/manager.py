"""
Custom Reporting Manager
========================

Manages custom reporting and business intelligence operations including:
- BI strategy and reporting team coordination
- Custom dashboard and report development oversight
- Data analytics and insights generation
- Stakeholder reporting and communication
- Quality assurance and technical excellence
"""

import logging
from typing import List, Optional
import semantic_kernel as sk

from Core.Agents.agent import Agent
from Core.Agents.manager import Manager
from Core.Tasks.task import Task

# Import CustomReporting agents
from .Agents.reporting_manager_agent import ReportingManagerAgent
from .Agents.reporting_specialist_agent import ReportingSpecialistAgent

# Configure logger
logger = logging.getLogger("custom_reporting_manager")


class CustomReportingManager(Manager):
    """
    Custom Reporting Manager - Oversees business intelligence and reporting
    focused on data-driven insights and strategic reporting excellence.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel, team_members: List[Agent] = None):
        super().__init__(name, role, kernel, team_members or [])
        
        # Initialize Custom Reporting team if not provided
        if not self.team_members:
            self._initialize_reporting_team()
        
        logger.info(f"Custom Reporting Manager initialized with {len(self.team_members)} agents")
    
    def _initialize_reporting_team(self):
        """Initialize the complete Custom Reporting team"""
        try:
            # Create Custom Reporting agents
            self.team_members = [
                ReportingManagerAgent(
                    name="Reporting Manager",
                    role="BI Strategy and Reporting Lead", 
                    kernel=self.kernel
                ),
                ReportingSpecialistAgent(
                    name="Reporting Specialist",
                    role="Technical Report Developer",
                    kernel=self.kernel
                )
            ]
            
            logger.info(f"Initialized {len(self.team_members)} Custom Reporting agents")
            
        except Exception as e:
            logger.error(f"Error initializing Custom Reporting team: {str(e)}")
            self.team_members = []
    
    def route_reporting_request(self, request_type: str, complexity: str, content: str) -> dict:
        """Route reporting requests to appropriate agent based on type and complexity"""
        try:
            if not self.team_members:
                return {"error": "No reporting agents available"}
            
            reporting_manager = next((agent for agent in self.team_members if "Reporting Manager" in agent.name), None)
            reporting_specialist = next((agent for agent in self.team_members if "Reporting Specialist" in agent.name), None)
            
            # Route based on request type and complexity
            if request_type in ["strategy", "roadmap", "planning", "stakeholder"]:
                return {
                    "routed_to": "BI Strategy and Management",
                    "agent": reporting_manager.name if reporting_manager else "Reporting Manager",
                    "content": content,
                    "specialization": "Strategic BI management and stakeholder reporting"
                }
            
            elif request_type in ["development", "technical", "sql", "dashboard"]:
                return {
                    "routed_to": "Technical Development",
                    "agent": reporting_specialist.name if reporting_specialist else "Reporting Specialist",
                    "content": content,
                    "specialization": "Technical report and dashboard development"
                }
            
            elif request_type in ["analytics", "data", "analysis"]:
                if complexity in ["complex", "advanced", "strategic"]:
                    return {
                        "routed_to": "Strategic Analytics",
                        "agent": reporting_manager.name if reporting_manager else "Reporting Manager",
                        "content": content,
                        "specialization": "Advanced analytics and strategic insights"
                    }
                else:
                    return {
                        "routed_to": "Data Analysis",
                        "agent": reporting_specialist.name if reporting_specialist else "Reporting Specialist",
                        "content": content,
                        "specialization": "Data analysis and visualization"
                    }
            
            elif request_type in ["automation", "pipeline", "etl"]:
                return {
                    "routed_to": "Automation Development",
                    "agent": reporting_specialist.name if reporting_specialist else "Reporting Specialist",
                    "content": content,
                    "specialization": "Automated reporting and data pipeline development"
                }
            
            else:
                # Default to reporting manager for general requests
                return {
                    "routed_to": "General Reporting",
                    "agent": reporting_manager.name if reporting_manager else "Reporting Manager",
                    "content": content,
                    "specialization": "General reporting coordination and management"
                }
                
        except Exception as e:
            logger.error(f"Error routing reporting request: {e}")
            return {"error": str(e)}
    
    def get_reporting_capabilities(self) -> dict:
        """Get comprehensive reporting team capabilities"""
        return {
            "team_size": len(self.team_members),
            "specializations": {
                "BI Strategy": "Business intelligence roadmap and strategic planning",
                "Dashboard Development": "Custom dashboard and visualization creation",
                "Data Analytics": "Advanced data analysis and insights generation",
                "Technical Development": "SQL optimization and automated reporting",
                "Stakeholder Communication": "Executive reporting and presentation"
            },
            "technical_skills": [
                "Advanced SQL and database querying",
                "Data visualization tools (Tableau, Power BI)",
                "Statistical analysis and modeling",
                "Automated reporting and ETL processes",
                "Dashboard design and user experience"
            ],
            "service_offerings": [
                "Strategic BI planning and roadmap development",
                "Custom dashboard and report creation",
                "Data analysis and insights generation",
                "Automated reporting solution implementation",
                "Executive and stakeholder reporting",
                "Data quality validation and optimization"
            ],
            "delivery_methods": [
                "Agile development methodology",
                "User-centered design approach",
                "Iterative feedback and refinement",
                "Quality assurance and testing",
                "Documentation and training"
            ],
            "status": "operational" if len(self.team_members) > 0 else "no_agents"
        }
    
    def prioritize_reporting_request(self, urgency: str, stakeholder_level: str, business_impact: str) -> dict:
        """Prioritize reporting requests based on multiple factors"""
        priority_matrix = {
            ("critical", "executive", "high"): 1,
            ("high", "executive", "high"): 2,
            ("critical", "management", "high"): 2,
            ("high", "management", "medium"): 3,
            ("medium", "executive", "medium"): 3,
            ("medium", "management", "low"): 4,
            ("low", "team", "low"): 5
        }
        
        priority_key = (urgency, stakeholder_level, business_impact)
        priority_score = priority_matrix.get(priority_key, 4)
        
        # Determine resource allocation
        if priority_score <= 2:
            assigned_agent = "Reporting Manager"
            resource_allocation = "Full team collaboration"
        elif priority_score == 3:
            assigned_agent = "Both agents coordination"
            resource_allocation = "Shared development approach"
        else:
            assigned_agent = "Reporting Specialist"
            resource_allocation = "Standard development process"
        
        return {
            "priority_score": priority_score,
            "priority_level": {
                1: "Critical - Immediate attention",
                2: "High - Priority development",
                3: "Medium - Scheduled development",
                4: "Low - Standard queue",
                5: "Deferred - Future consideration"
            }.get(priority_score, "Standard"),
            "assigned_agent": assigned_agent,
            "resource_allocation": resource_allocation,
            "estimated_timeline": {
                1: "Same day completion",
                2: "2-3 business days",
                3: "1 week",
                4: "2-3 weeks",
                5: "Future planning cycle"
            }.get(priority_score, "Standard timeline"),
            "stakeholder_communication": {
                1: "Hourly updates required",
                2: "Daily status updates",
                3: "Bi-weekly check-ins",
                4: "Weekly status reports",
                5: "Monthly progress review"
            }.get(priority_score, "Standard communication")
        } 