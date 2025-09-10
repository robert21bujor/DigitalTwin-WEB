"""
Senior Customer Success Manager Agent
====================================

Senior CSM agent responsible for:
- Enterprise client relationship management
- Strategic account planning and expansion
- Customer lifecycle optimization
- Escalation handling and resolution
- Team mentorship and guidance
- Customer health monitoring and improvement

Focus: Ensure enterprise customer success and drive strategic account growth.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import semantic_kernel as sk
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.prompt_template.prompt_template_config import PromptExecutionSettings

from Core.Agents.agent import Agent, AgentType
from Core.Tasks.task import Task, TaskStatus

# Configure logger
logger = logging.getLogger("senior_csm")


class SeniorCSMAgent(Agent):
    """
    Senior CSM Agent - Enterprise customer success management
    and strategic account development.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # CSM specific metrics
        self.enterprise_accounts_managed = 0
        self.customer_health_improvements = 0
        self.expansion_opportunities_identified = 0
        self.escalations_resolved = 0
        self.team_members_mentored = 0
        
        # Account tracking
        self.active_accounts = {}
        self.health_scores = {}
        self.expansion_pipeline = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Senior CSM Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized Senior CSM system prompt"""
        return f"""You are a Senior Customer Success Manager with deep expertise in enterprise client management, strategic account development, and customer lifecycle optimization.

CORE COMPETENCIES:
- Enterprise customer relationship management
- Strategic account planning and expansion
- Customer success methodology and best practices
- Customer health monitoring and intervention
- Escalation management and crisis resolution
- Cross-functional team coordination
- Customer advocacy and voice-of-customer programs
- Revenue retention and expansion strategies
- Team leadership and mentorship

CSM EXPERTISE:
- Customer lifecycle management from onboarding to renewal
- Customer health scoring and early warning systems
- Account planning and quarterly business reviews
- Expansion opportunity identification and development
- Customer success playbooks and methodologies
- Stakeholder mapping and relationship building
- Value realization and ROI demonstration
- Churn prevention and win-back strategies

SENIOR RESPONSIBILITIES:
- Enterprise and strategic account management
- Complex escalation resolution and crisis management
- Team mentorship and best practice sharing
- Cross-departmental collaboration and alignment
- Customer success strategy development
- Executive-level customer relationship management
- Thought leadership and customer advisory programs
- Process improvement and optimization

COMMUNICATION STYLE:
- Executive-level customer communication
- Strategic account planning and review facilitation
- Data-driven customer insights and recommendations
- Consultative problem-solving approach
- Empathetic customer advocacy

CURRENT METRICS:
- Enterprise Accounts: {self.enterprise_accounts_managed}
- Health Improvements: {self.customer_health_improvements}
- Expansion Opportunities: {self.expansion_opportunities_identified}
- Escalations Resolved: {self.escalations_resolved}
- Team Members Mentored: {self.team_members_mentored}

You excel at building strategic customer relationships, driving account growth, and ensuring exceptional customer experiences throughout the entire lifecycle. Your responses should be customer-focused, strategic, and oriented toward long-term success."""

    async def process_csm_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process customer success management requests"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "account_management":
                return await self._handle_account_management(request, context)
            elif request_type == "health_monitoring":
                return await self._handle_health_monitoring(request, context)
            elif request_type == "expansion_planning":
                return await self._handle_expansion_planning(request, context)
            elif request_type == "escalation_resolution":
                return await self._handle_escalation_resolution(request, context)
            elif request_type == "team_mentorship":
                return await self._handle_team_mentorship(request, context)
            else:
                return await self._handle_general_csm_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing CSM request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of CSM request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["account", "client", "customer", "relationship"]):
            return "account_management"
        elif any(term in request_lower for term in ["health", "score", "monitoring", "intervention"]):
            return "health_monitoring"
        elif any(term in request_lower for term in ["expansion", "upsell", "growth", "opportunity"]):
            return "expansion_planning"
        elif any(term in request_lower for term in ["escalation", "crisis", "issue", "problem"]):
            return "escalation_resolution"
        elif any(term in request_lower for term in ["mentor", "training", "coaching", "team"]):
            return "team_mentorship"
        else:
            return "general_csm"
    
    async def _handle_account_management(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle strategic account management and planning"""
        management_framework = {
            "account_assessment": "Comprehensive account analysis and opportunity mapping",
            "stakeholder_mapping": "Identify and engage key stakeholders across the organization",
            "success_planning": "Develop customer success plans aligned with business objectives",
            "relationship_building": "Strengthen relationships at all organizational levels",
            "value_demonstration": "Continuously demonstrate and communicate value delivered"
        }
        
        return {
            "success": True,
            "response_type": "account_management",
            "framework": management_framework,
            "account_activities": [
                "Quarterly business reviews and planning",
                "Executive relationship building",
                "Success milestone tracking and celebration",
                "Feedback collection and action planning",
                "Risk assessment and mitigation"
            ],
            "engagement_strategies": [
                "Executive advisory board participation",
                "Industry events and networking",
                "Customer success community building",
                "Thought leadership and content sharing",
                "Strategic planning collaboration"
            ],
            "agent": self.name
        }
    
    async def _handle_health_monitoring(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle customer health monitoring and intervention"""
        monitoring_framework = {
            "health_assessment": "Multi-dimensional customer health evaluation",
            "early_warning_systems": "Proactive identification of at-risk accounts",
            "intervention_planning": "Develop targeted intervention strategies",
            "success_measurement": "Track health improvements and outcomes",
            "predictive_analytics": "Leverage data for predictive health insights"
        }
        
        return {
            "success": True,
            "response_type": "health_monitoring",
            "framework": monitoring_framework,
            "health_dimensions": [
                "Product adoption and usage patterns",
                "Stakeholder engagement levels",
                "Support ticket trends and sentiment",
                "Business outcome achievement",
                "Relationship strength indicators"
            ],
            "intervention_strategies": [
                "Proactive outreach and check-ins",
                "Additional training and enablement",
                "Executive escalation and support",
                "Process optimization and improvement",
                "Success plan adjustment and realignment"
            ],
            "agent": self.name
        }
    
    async def _handle_expansion_planning(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle expansion opportunity identification and development"""
        expansion_framework = {
            "opportunity_assessment": "Systematic evaluation of expansion potential",
            "stakeholder_alignment": "Ensure internal and customer stakeholder buy-in",
            "value_proposition": "Develop compelling expansion business case",
            "implementation_planning": "Plan expansion rollout and success criteria",
            "success_tracking": "Monitor expansion outcomes and optimization"
        }
        
        return {
            "success": True,
            "response_type": "expansion_planning",
            "framework": expansion_framework,
            "expansion_types": [
                "Additional user licenses and seats",
                "New product modules and features",
                "Extended service packages",
                "Multi-department implementations",
                "Enterprise-wide deployments"
            ],
            "development_process": [
                "Opportunity identification and qualification",
                "Business case development and approval",
                "Stakeholder engagement and buy-in",
                "Implementation planning and execution",
                "Success measurement and optimization"
            ],
            "agent": self.name
        }
    
    async def _handle_escalation_resolution(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complex escalations and crisis management"""
        resolution_framework = {
            "escalation_assessment": "Rapid assessment of escalation scope and impact",
            "stakeholder_coordination": "Coordinate internal and external stakeholder response",
            "resolution_strategy": "Develop comprehensive resolution approach",
            "communication_management": "Manage customer and internal communications",
            "relationship_recovery": "Focus on relationship repair and strengthening"
        }
        
        return {
            "success": True,
            "response_type": "escalation_resolution",
            "framework": resolution_framework,
            "escalation_types": [
                "Product or service performance issues",
                "Implementation delays or challenges",
                "Contract or billing disputes",
                "Stakeholder relationship conflicts",
                "Strategic misalignment concerns"
            ],
            "resolution_approach": [
                "Immediate acknowledgment and ownership",
                "Thorough investigation and root cause analysis",
                "Collaborative solution development",
                "Clear communication and expectation setting",
                "Follow-up and relationship strengthening"
            ],
            "agent": self.name
        }
    
    async def _handle_team_mentorship(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team mentorship and development"""
        mentorship_framework = {
            "skill_assessment": "Evaluate team member capabilities and development needs",
            "coaching_planning": "Develop individualized coaching and development plans",
            "knowledge_sharing": "Facilitate best practice sharing and learning",
            "performance_support": "Provide ongoing support and guidance",
            "career_development": "Support professional growth and advancement"
        }
        
        return {
            "success": True,
            "response_type": "team_mentorship",
            "framework": mentorship_framework,
            "mentorship_areas": [
                "Customer relationship building",
                "Account planning and strategy",
                "Escalation handling and resolution",
                "Expansion opportunity development",
                "Communication and presentation skills"
            ],
            "development_methods": [
                "One-on-one coaching sessions",
                "Joint customer calls and meetings",
                "Case study reviews and learning",
                "Skill-building workshops and training",
                "Stretch assignments and challenges"
            ],
            "agent": self.name
        }
    
    async def _handle_general_csm_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general customer success management queries"""
        # Use semantic kernel for general CSM guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As a Senior Customer Success Manager, provide comprehensive guidance for this customer success query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Customer success strategy and best practices
2. Account management recommendations
3. Risk mitigation and opportunity identification
4. Implementation approach and timeline
5. Success measurement and optimization

Focus on strategic, customer-centric guidance that drives long-term success and growth."""

        try:
            result = await self.kernel.invoke_stream(
                function_name="chat",
                plugin_name="ChatPlugin", 
                prompt=prompt,
                settings=settings
            )
            
            response_text = ""
            async for content in result:
                response_text += str(content)
            
            return {
                "success": True,
                "response_type": "general_guidance",
                "guidance": response_text,
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"Error generating CSM guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate CSM guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_csm_metrics(self) -> Dict[str, Any]:
        """Get current CSM metrics"""
        return {
            "enterprise_accounts_managed": self.enterprise_accounts_managed,
            "customer_health_improvements": self.customer_health_improvements,
            "expansion_opportunities_identified": self.expansion_opportunities_identified,
            "escalations_resolved": self.escalations_resolved,
            "team_members_mentored": self.team_members_mentored,
            "active_accounts": list(self.active_accounts.keys()),
            "health_scores": self.health_scores,
            "agent": self.name
        } 