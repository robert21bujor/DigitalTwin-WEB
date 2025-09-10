"""
Presales Engineer Agent
======================

Specialized agent for technical presales and solution engineering:
- Solution architecture and design
- Technical demonstrations and proof of concepts
- Requirements gathering and analysis
- Technical proposal development
- Customer technical consultation
- Solution customization and integration planning

Focus: Bridge technical capabilities with customer needs through expert solution engineering.
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
logger = logging.getLogger("presales_engineer")


class PresalesEngineerAgent(Agent):
    """
    Presales Engineer Agent - Specializes in technical solution design,
    customer consultation, and presales engineering support.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # Presales engineering specific metrics
        self.demos_conducted = 0
        self.pocs_delivered = 0
        self.technical_proposals_created = 0
        self.requirements_gathered = 0
        self.solution_win_rate = 0
        
        # Technical tracking
        self.active_engagements = {}
        self.solution_templates = {}
        self.demo_environments = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Presales Engineer Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized presales engineering system prompt"""
        return f"""You are an expert Presales Engineer with deep expertise in solution architecture, technical consulting, and customer-facing technical sales support.

CORE COMPETENCIES:
- Solution architecture and technical design
- Requirements gathering and analysis
- Technical demonstration and presentation
- Proof of concept (POC) development and delivery
- Technical proposal writing and documentation
- Customer technical consultation and advisory
- Integration planning and feasibility assessment
- Technical objection handling and resolution
- Solution customization and configuration

TECHNICAL EXPERTISE:
- Enterprise software architecture and integration
- Cloud platform design (AWS, Azure, GCP)
- API design and integration patterns
- Database architecture and data modeling
- Security frameworks and compliance requirements
- Scalability and performance optimization
- DevOps and deployment strategies
- Technical documentation and specifications

SPECIALIZED SKILLS:
- Technical requirements discovery and documentation
- Solution mapping to customer business needs
- Technical risk assessment and mitigation
- Competitive technical differentiation
- Technical stakeholder management
- Demo environment setup and management
- POC scoping and execution
- Technical training and enablement

COMMUNICATION STYLE:
- Clear technical communication for diverse audiences
- Business value articulation for technical solutions
- Consultative problem-solving approach
- Evidence-based recommendations
- Technical credibility and expertise demonstration

CURRENT METRICS:
- Demos Conducted: {self.demos_conducted}
- POCs Delivered: {self.pocs_delivered}
- Technical Proposals: {self.technical_proposals_created}
- Requirements Gathered: {self.requirements_gathered}
- Solution Win Rate: {self.solution_win_rate:.1f}%

You excel at translating complex technical capabilities into clear business value, designing optimal solutions for customer needs, and providing technical leadership throughout the sales process. Your responses should be technically accurate, business-focused, and solution-oriented."""

    async def process_presales_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process presales engineering requests with specialized handling"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "requirements_discovery":
                return await self._handle_requirements_discovery(request, context)
            elif request_type == "solution_design":
                return await self._handle_solution_design(request, context)
            elif request_type == "demo_preparation":
                return await self._handle_demo_preparation(request, context)
            elif request_type == "poc_development":
                return await self._handle_poc_development(request, context)
            elif request_type == "technical_proposal":
                return await self._handle_technical_proposal(request, context)
            else:
                return await self._handle_general_presales_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing presales request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of presales engineering request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["requirements", "discovery", "needs", "analysis"]):
            return "requirements_discovery"
        elif any(term in request_lower for term in ["solution", "architecture", "design", "technical"]):
            return "solution_design"
        elif any(term in request_lower for term in ["demo", "demonstration", "presentation", "showcase"]):
            return "demo_preparation"
        elif any(term in request_lower for term in ["poc", "proof of concept", "pilot", "trial"]):
            return "poc_development"
        elif any(term in request_lower for term in ["proposal", "documentation", "specification", "rfi"]):
            return "technical_proposal"
        else:
            return "general_presales"
    
    async def _handle_requirements_discovery(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle technical requirements discovery and analysis"""
        discovery_framework = {
            "business_requirements": "Understand business objectives and success criteria",
            "functional_requirements": "Define specific functional capabilities needed",
            "technical_requirements": "Identify technical constraints and specifications",
            "integration_requirements": "Map existing systems and integration needs",
            "performance_requirements": "Define scalability, availability, and performance needs"
        }
        
        return {
            "success": True,
            "response_type": "requirements_discovery",
            "framework": discovery_framework,
            "discovery_areas": [
                "Current state assessment",
                "Future state vision",
                "Gap analysis",
                "Constraint identification",
                "Success metrics definition"
            ],
            "methodologies": [
                "Stakeholder interviews",
                "Technical workshops", 
                "System architecture review",
                "Process mapping sessions",
                "Requirements documentation"
            ],
            "agent": self.name
        }
    
    async def _handle_solution_design(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle solution architecture and design requests"""
        design_framework = {
            "solution_architecture": "Design high-level solution architecture",
            "component_design": "Define individual solution components",
            "integration_design": "Plan system integrations and data flows", 
            "security_design": "Implement security and compliance frameworks",
            "deployment_design": "Design deployment and operational approach"
        }
        
        return {
            "success": True,
            "response_type": "solution_design",
            "framework": design_framework,
            "design_principles": [
                "Modularity and scalability",
                "Security by design",
                "Performance optimization",
                "Maintainability and supportability",
                "Cost-effectiveness"
            ],
            "deliverables": [
                "Solution architecture diagram",
                "Technical specifications",
                "Integration requirements",
                "Security framework",
                "Implementation roadmap"
            ],
            "agent": self.name
        }
    
    async def _handle_demo_preparation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle demo preparation and presentation planning"""
        demo_framework = {
            "demo_strategy": "Develop customer-specific demo strategy",
            "scenario_design": "Create relevant business scenarios",
            "environment_setup": "Prepare and configure demo environment",
            "script_development": "Create demo script and talking points",
            "objection_preparation": "Anticipate and prepare for technical questions"
        }
        
        return {
            "success": True,
            "response_type": "demo_preparation",
            "framework": demo_framework,
            "demo_types": [
                "Discovery demos",
                "Feature-focused demos",
                "Integration demos",
                "Performance demos",
                "Executive overviews"
            ],
            "best_practices": [
                "Customer-specific scenarios",
                "Interactive engagement",
                "Value-focused messaging",
                "Technical depth appropriate to audience",
                "Clear next steps"
            ],
            "agent": self.name
        }
    
    async def _handle_poc_development(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle proof of concept development and execution"""
        poc_framework = {
            "poc_scoping": "Define POC objectives, scope, and success criteria",
            "environment_setup": "Configure POC environment and test data",
            "use_case_development": "Implement key use cases and scenarios",
            "testing_execution": "Execute comprehensive testing and validation",
            "results_documentation": "Document findings and recommendations"
        }
        
        return {
            "success": True,
            "response_type": "poc_development",
            "framework": poc_framework,
            "poc_phases": [
                "Planning and scoping",
                "Environment preparation",
                "Implementation and configuration",
                "Testing and validation",
                "Results presentation"
            ],
            "success_factors": [
                "Clear success criteria",
                "Realistic scope and timeline",
                "Customer stakeholder engagement",
                "Thorough testing and validation",
                "Comprehensive documentation"
            ],
            "agent": self.name
        }
    
    async def _handle_technical_proposal(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle technical proposal development and documentation"""
        proposal_framework = {
            "executive_summary": "Provide high-level solution overview and value",
            "technical_approach": "Detail technical solution and methodology",
            "implementation_plan": "Define implementation timeline and approach",
            "risk_mitigation": "Address technical risks and mitigation strategies",
            "support_model": "Outline ongoing support and maintenance"
        }
        
        return {
            "success": True,
            "response_type": "technical_proposal",
            "framework": proposal_framework,
            "proposal_sections": [
                "Requirements summary",
                "Proposed solution",
                "Technical architecture",
                "Implementation methodology",
                "Project timeline and milestones",
                "Resource requirements",
                "Risk analysis",
                "Success metrics"
            ],
            "differentiation_areas": [
                "Technical innovation",
                "Integration capabilities",
                "Scalability and performance",
                "Security and compliance",
                "Implementation expertise"
            ],
            "agent": self.name
        }
    
    async def _handle_general_presales_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general presales engineering queries"""
        # Use semantic kernel for general presales guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As an expert Presales Engineer, provide comprehensive technical guidance for this presales query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Technical solution recommendations
2. Implementation considerations
3. Integration requirements and approaches
4. Risk factors and mitigation strategies
5. Success metrics and validation criteria

Focus on practical, technically sound solutions that address customer needs while demonstrating competitive advantages."""

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
            logger.error(f"Error generating presales guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate presales guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_presales_metrics(self) -> Dict[str, Any]:
        """Get current presales engineering metrics"""
        return {
            "demos_conducted": self.demos_conducted,
            "pocs_delivered": self.pocs_delivered,
            "technical_proposals_created": self.technical_proposals_created,
            "requirements_gathered": self.requirements_gathered,
            "solution_win_rate": self.solution_win_rate,
            "active_engagements": list(self.active_engagements.keys()),
            "demo_environments": list(self.demo_environments.keys()),
            "agent": self.name
        } 