"""
Head of Operations Agent
=======================

Strategic operations management agent responsible for:
- Overall operations strategy and planning
- Cross-functional team leadership and coordination
- Process optimization and efficiency improvements
- Quality assurance and compliance oversight
- Stakeholder management and communication
- Performance monitoring and reporting

Focus: Ensure operational excellence across all client-facing activities.
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
logger = logging.getLogger("head_of_operations")


class HeadOfOperationsAgent(Agent):
    """
    Head of Operations Agent - Strategic operations oversight and management
    across all client success and delivery activities.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # Operations management specific metrics
        self.teams_managed = 0
        self.strategic_initiatives_led = 0
        self.process_improvements_implemented = 0
        self.client_escalations_resolved = 0
        self.operational_efficiency_score = 0
        
        # Leadership tracking
        self.active_initiatives = {}
        self.team_performance_metrics = {}
        self.operational_kpis = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Head of Operations Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized Head of Operations system prompt"""
        return f"""You are the Head of Operations with deep expertise in strategic operations management, team leadership, and organizational excellence.

CORE COMPETENCIES:
- Strategic operations planning and execution
- Cross-functional team leadership and development
- Process optimization and operational efficiency
- Quality assurance and compliance management
- Performance monitoring and KPI management
- Stakeholder communication and relationship management
- Change management and organizational transformation
- Resource allocation and capacity planning
- Risk management and mitigation strategies

OPERATIONAL EXPERTISE:
- Operations strategy development and implementation
- Team structure optimization and role definition
- Process standardization and automation
- Performance measurement and improvement
- Client success methodology and best practices
- Escalation management and resolution
- Vendor and partner relationship management
- Budget planning and cost optimization

LEADERSHIP SKILLS:
- Strategic vision development and communication
- Team motivation and performance coaching
- Conflict resolution and decision making
- Stakeholder alignment and consensus building
- Cultural transformation and change leadership
- Succession planning and talent development
- Cross-departmental collaboration
- Executive reporting and presentation

COMMUNICATION STYLE:
- Strategic and visionary leadership communication
- Clear operational directives and expectations
- Data-driven decision making and reporting
- Collaborative problem-solving approach
- Executive-level stakeholder management

CURRENT METRICS:
- Teams Managed: {self.teams_managed}
- Strategic Initiatives Led: {self.strategic_initiatives_led}
- Process Improvements: {self.process_improvements_implemented}
- Escalations Resolved: {self.client_escalations_resolved}
- Operational Efficiency: {self.operational_efficiency_score:.1f}%

You excel at driving operational excellence, leading high-performing teams, and ensuring seamless client experiences through strategic planning and execution. Your responses should be strategic, leadership-focused, and oriented toward long-term operational success."""

    async def process_operations_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process strategic operations requests with executive-level handling"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "strategic_planning":
                return await self._handle_strategic_planning(request, context)
            elif request_type == "team_management":
                return await self._handle_team_management(request, context)
            elif request_type == "process_optimization":
                return await self._handle_process_optimization(request, context)
            elif request_type == "performance_management":
                return await self._handle_performance_management(request, context)
            elif request_type == "escalation_resolution":
                return await self._handle_escalation_resolution(request, context)
            else:
                return await self._handle_general_operations_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing operations request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of operations request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["strategy", "planning", "vision", "roadmap"]):
            return "strategic_planning"
        elif any(term in request_lower for term in ["team", "management", "leadership", "staff"]):
            return "team_management"
        elif any(term in request_lower for term in ["process", "optimization", "efficiency", "workflow"]):
            return "process_optimization"
        elif any(term in request_lower for term in ["performance", "metrics", "kpi", "measurement"]):
            return "performance_management"
        elif any(term in request_lower for term in ["escalation", "issue", "problem", "crisis"]):
            return "escalation_resolution"
        else:
            return "general_operations"
    
    async def _handle_strategic_planning(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle strategic planning and vision development"""
        planning_framework = {
            "vision_development": "Define clear operational vision and strategic direction",
            "goal_setting": "Establish SMART operational objectives and KPIs",
            "resource_planning": "Allocate resources to support strategic initiatives",
            "timeline_development": "Create implementation roadmaps with milestones",
            "risk_assessment": "Identify strategic risks and mitigation plans"
        }
        
        return {
            "success": True,
            "response_type": "strategic_planning",
            "framework": planning_framework,
            "strategic_pillars": [
                "Operational Excellence",
                "Customer Success",
                "Team Development",
                "Process Innovation",
                "Quality Assurance"
            ],
            "implementation_phases": [
                "Assessment and baseline establishment",
                "Strategy formulation and approval",
                "Resource allocation and team alignment",
                "Execution and monitoring",
                "Evaluation and optimization"
            ],
            "agent": self.name
        }
    
    async def _handle_team_management(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle team leadership and management requests"""
        management_framework = {
            "team_structure": "Optimize team organization and role definitions",
            "performance_coaching": "Provide leadership and performance guidance",
            "skill_development": "Plan training and capability building initiatives",
            "motivation_strategies": "Implement team engagement and retention programs",
            "succession_planning": "Develop leadership pipeline and knowledge transfer"
        }
        
        return {
            "success": True,
            "response_type": "team_management",
            "framework": management_framework,
            "leadership_areas": [
                "Team structure and role clarity",
                "Performance management and coaching",
                "Professional development planning",
                "Communication and collaboration",
                "Recognition and reward systems"
            ],
            "management_tools": [
                "Regular one-on-one meetings",
                "Team performance reviews",
                "Skills assessment and training plans",
                "Goal setting and tracking",
                "Cross-functional collaboration"
            ],
            "agent": self.name
        }
    
    async def _handle_process_optimization(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process improvement and optimization initiatives"""
        optimization_framework = {
            "process_analysis": "Analyze current processes and identify improvement opportunities",
            "workflow_design": "Design optimized workflows and procedures",
            "automation_opportunities": "Identify and implement process automation",
            "quality_standards": "Establish quality assurance and compliance protocols",
            "continuous_improvement": "Implement ongoing optimization and feedback loops"
        }
        
        return {
            "success": True,
            "response_type": "process_optimization",
            "framework": optimization_framework,
            "optimization_areas": [
                "Client onboarding and implementation",
                "Delivery methodology and execution",
                "Communication and reporting",
                "Quality assurance and testing",
                "Knowledge management and documentation"
            ],
            "improvement_methods": [
                "Process mapping and analysis",
                "Lean methodology application",
                "Automation and digitization",
                "Standardization and documentation",
                "Performance measurement and feedback"
            ],
            "agent": self.name
        }
    
    async def _handle_performance_management(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle performance monitoring and KPI management"""
        performance_framework = {
            "kpi_development": "Define and implement operational KPIs and metrics",
            "performance_monitoring": "Establish real-time performance dashboards",
            "benchmarking": "Compare performance against industry standards",
            "improvement_planning": "Develop action plans for performance enhancement",
            "reporting_communication": "Communicate performance insights to stakeholders"
        }
        
        return {
            "success": True,
            "response_type": "performance_management",
            "framework": performance_framework,
            "key_metrics": [
                "Client satisfaction and NPS scores",
                "Implementation success rates",
                "Time to value and adoption metrics",
                "Team productivity and efficiency",
                "Quality and compliance indicators"
            ],
            "monitoring_tools": [
                "Real-time performance dashboards",
                "Regular performance reviews",
                "Client feedback and surveys",
                "Team performance analytics",
                "Compliance audit results"
            ],
            "agent": self.name
        }
    
    async def _handle_escalation_resolution(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle critical escalations and issue resolution"""
        resolution_framework = {
            "escalation_assessment": "Rapidly assess escalation severity and impact",
            "stakeholder_coordination": "Coordinate response across teams and stakeholders",
            "resolution_planning": "Develop comprehensive resolution strategy",
            "communication_management": "Manage client and internal communications",
            "post_resolution_analysis": "Conduct lessons learned and process improvements"
        }
        
        return {
            "success": True,
            "response_type": "escalation_resolution",
            "framework": resolution_framework,
            "escalation_levels": [
                "Level 1: Team-level resolution",
                "Level 2: Manager escalation",
                "Level 3: Operations head involvement",
                "Level 4: Executive escalation"
            ],
            "resolution_process": [
                "Immediate acknowledgment and assessment",
                "Stakeholder notification and coordination",
                "Resolution plan development and approval",
                "Implementation and monitoring",
                "Client communication and closure"
            ],
            "agent": self.name
        }
    
    async def _handle_general_operations_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general operations management queries"""
        # Use semantic kernel for general operations guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As the Head of Operations, provide comprehensive strategic guidance for this operations query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Strategic operations recommendations
2. Implementation approach and timeline
3. Resource requirements and team coordination
4. Success metrics and measurement
5. Risk factors and mitigation strategies

Focus on strategic, executive-level guidance that drives operational excellence and business success."""

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
            logger.error(f"Error generating operations guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate operations guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_operations_metrics(self) -> Dict[str, Any]:
        """Get current operations management metrics"""
        return {
            "teams_managed": self.teams_managed,
            "strategic_initiatives_led": self.strategic_initiatives_led,
            "process_improvements_implemented": self.process_improvements_implemented,
            "client_escalations_resolved": self.client_escalations_resolved,
            "operational_efficiency_score": self.operational_efficiency_score,
            "active_initiatives": list(self.active_initiatives.keys()),
            "performance_metrics": self.team_performance_metrics,
            "agent": self.name
        } 