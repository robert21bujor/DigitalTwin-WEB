"""
Delivery Consultant EN Agent
============================

English delivery consulting agent responsible for:
- Project implementation and delivery for English-speaking clients
- International client training and adoption
- Technical configuration and setup support
- Global best practices implementation
- Documentation and knowledge transfer
- Quality assurance and testing

Focus: Deliver successful implementations for English-speaking clients globally.
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
logger = logging.getLogger("delivery_consultant_en")


class DeliveryConsultantENAgent(Agent):
    """
    Delivery Consultant EN Agent - Specialized in English-speaking market
    delivery consulting and international client support.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # EN delivery specific metrics
        self.english_projects_delivered = 0
        self.international_clients_served = 0
        self.training_sessions_conducted = 0
        self.best_practices_implemented = 0
        self.go_lives_supported = 0
        
        # International market tracking
        self.active_en_clients = {}
        self.global_implementations = {}
        self.training_materials_en = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Delivery Consultant EN Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized EN delivery consultant system prompt"""
        return f"""You are a Delivery Consultant specializing in English-speaking markets with deep expertise in international implementations, global best practices, and cross-cultural client support.

CORE COMPETENCIES:
- Project implementation and delivery management
- International client communication and support
- Global best practices and methodology implementation
- Client training and user adoption programs
- Technical configuration and system setup
- Quality assurance and testing coordination
- Documentation creation and knowledge transfer
- Go-live support and post-implementation optimization
- Cross-cultural stakeholder management and communication

INTERNATIONAL MARKET EXPERTISE:
- Global business practices and standards
- International regulatory and compliance awareness
- Cross-cultural communication and adaptation
- Multi-timezone project coordination
- International partner and vendor coordination
- Global methodology and best practice implementation
- Cultural sensitivity across diverse markets
- International business customs and communication styles

DELIVERY SPECIALIZATION:
- Complex international implementation management
- Requirements gathering across diverse markets
- System configuration for global deployments
- Multi-language training and enablement programs
- International data migration and integration
- Global testing coordination and quality assurance
- International go-live planning and execution
- Post-implementation optimization and support

LANGUAGE AND COMMUNICATION:
- Expert English language proficiency
- Technical documentation and communication
- International training delivery
- Cross-cultural client relationship building
- Global team coordination and collaboration

CURRENT METRICS:
- English Projects Delivered: {self.english_projects_delivered}
- International Clients Served: {self.international_clients_served}
- Training Sessions Conducted: {self.training_sessions_conducted}
- Best Practices Implemented: {self.best_practices_implemented}
- Go-Lives Supported: {self.go_lives_supported}

You excel at delivering successful implementations for English-speaking clients globally through international expertise, cultural awareness, and technical excellence. Your responses should be professional, globally applicable, and focused on international client success."""

    async def process_en_delivery_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process English delivery consulting requests"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "implementation_delivery":
                return await self._handle_implementation_delivery(request, context)
            elif request_type == "international_training":
                return await self._handle_international_training(request, context)
            elif request_type == "global_best_practices":
                return await self._handle_global_best_practices(request, context)
            elif request_type == "cross_cultural_support":
                return await self._handle_cross_cultural_support(request, context)
            elif request_type == "global_compliance":
                return await self._handle_global_compliance(request, context)
            else:
                return await self._handle_general_en_delivery_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing EN delivery request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of EN delivery request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["implementation", "delivery", "project", "deployment"]):
            return "implementation_delivery"
        elif any(term in request_lower for term in ["training", "education", "learning", "adoption"]):
            return "international_training"
        elif any(term in request_lower for term in ["best practices", "methodology", "standards", "framework"]):
            return "global_best_practices"
        elif any(term in request_lower for term in ["cross-cultural", "international", "global", "multi-region"]):
            return "cross_cultural_support"
        elif any(term in request_lower for term in ["compliance", "regulation", "international law", "standards"]):
            return "global_compliance"
        else:
            return "general_en_delivery"
    
    async def _handle_implementation_delivery(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle implementation and delivery management"""
        delivery_framework = {
            "global_project_planning": "International project planning with multi-region considerations",
            "requirements_analysis": "Comprehensive requirements gathering across global markets",
            "system_configuration": "Scalable technical setup for international deployments",
            "quality_assurance": "Global testing and quality standards implementation",
            "delivery_execution": "Phased international delivery with best practice implementation"
        }
        
        return {
            "success": True,
            "response_type": "implementation_delivery",
            "framework": delivery_framework,
            "delivery_phases": [
                "Global project initiation and stakeholder alignment",
                "International requirements gathering and analysis",
                "Multi-region system configuration and setup",
                "Global testing and quality assurance",
                "International training and go-live coordination"
            ],
            "international_considerations": [
                "Multi-timezone project coordination",
                "Cross-cultural communication protocols",
                "International regulatory compliance",
                "Global scalability and performance",
                "Multi-language support requirements"
            ],
            "agent": self.name
        }
    
    async def _handle_international_training(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle international training and user adoption"""
        training_framework = {
            "global_training_strategy": "Develop internationally applicable training approach",
            "content_standardization": "Create standardized English training materials",
            "delivery_optimization": "Optimize training delivery for global audiences",
            "adoption_methodology": "International user adoption and change management",
            "continuous_improvement": "Global feedback integration and improvement"
        }
        
        return {
            "success": True,
            "response_type": "international_training",
            "framework": training_framework,
            "training_components": [
                "Global system overview and best practices",
                "Role-specific functionality training",
                "International business process integration",
                "Global compliance and regulatory features",
                "Advanced features and optimization techniques"
            ],
            "delivery_methods": [
                "Live virtual training sessions",
                "Interactive e-learning platforms",
                "Self-paced learning modules",
                "Global best practice workshops",
                "Ongoing mentoring and support programs"
            ],
            "agent": self.name
        }
    
    async def _handle_global_best_practices(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle global best practices implementation"""
        best_practices_framework = {
            "methodology_standardization": "Implement globally recognized methodologies",
            "process_optimization": "Apply international best practices and standards",
            "quality_frameworks": "Implement global quality assurance frameworks",
            "performance_standards": "Apply international performance benchmarks",
            "continuous_improvement": "Global methodology enhancement and evolution"
        }
        
        return {
            "success": True,
            "response_type": "global_best_practices",
            "framework": best_practices_framework,
            "best_practice_areas": [
                "International project management methodologies",
                "Global quality assurance standards",
                "Cross-cultural communication protocols",
                "International compliance frameworks",
                "Global performance optimization techniques"
            ],
            "implementation_approach": [
                "Best practice assessment and gap analysis",
                "Methodology customization for client needs",
                "Implementation planning and execution",
                "Training and knowledge transfer",
                "Ongoing monitoring and optimization"
            ],
            "agent": self.name
        }
    
    async def _handle_cross_cultural_support(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cross-cultural support and adaptation"""
        cultural_framework = {
            "cultural_assessment": "Understand diverse cultural contexts and requirements",
            "communication_adaptation": "Adapt communication styles for different cultures",
            "methodology_flexibility": "Flexible approach to accommodate cultural differences",
            "relationship_building": "Build trust across diverse cultural contexts",
            "change_management": "Culturally sensitive change management approaches"
        }
        
        return {
            "success": True,
            "response_type": "cross_cultural_support",
            "framework": cultural_framework,
            "cultural_considerations": [
                "Communication style preferences",
                "Decision-making processes and hierarchies",
                "Business relationship building approaches",
                "Time orientation and deadline management",
                "Conflict resolution and problem-solving styles"
            ],
            "adaptation_strategies": [
                "Flexible communication approaches",
                "Culturally appropriate relationship building",
                "Respectful methodology adaptation",
                "Inclusive decision-making processes",
                "Cultural sensitivity training and awareness"
            ],
            "agent": self.name
        }
    
    async def _handle_global_compliance(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle international compliance requirements"""
        compliance_framework = {
            "regulatory_mapping": "Map international regulatory requirements",
            "compliance_standards": "Implement global compliance standards",
            "data_governance": "International data protection and governance",
            "audit_frameworks": "Global audit and compliance reporting",
            "risk_management": "International risk assessment and mitigation"
        }
        
        return {
            "success": True,
            "response_type": "global_compliance",
            "framework": compliance_framework,
            "compliance_areas": [
                "International data protection regulations",
                "Global financial reporting standards",
                "Cross-border data transfer compliance",
                "International industry standards",
                "Multi-jurisdictional regulatory requirements"
            ],
            "implementation_steps": [
                "Global compliance requirements assessment",
                "System configuration for international compliance",
                "Cross-border data governance implementation",
                "International audit trail and reporting setup",
                "Ongoing compliance monitoring and reporting"
            ],
            "agent": self.name
        }
    
    async def _handle_general_en_delivery_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general English delivery consulting queries"""
        # Use semantic kernel for general EN delivery guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As an English Delivery Consultant with international expertise, provide comprehensive guidance for this delivery consulting query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. International implementation strategy
2. Global best practices and methodologies
3. Cross-cultural considerations
4. International compliance requirements
5. Training and adoption approach for global markets

Focus on international expertise, global best practices, cultural awareness, and successful outcomes across diverse markets."""

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
            logger.error(f"Error generating EN delivery guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate EN delivery guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_en_delivery_metrics(self) -> Dict[str, Any]:
        """Get current English delivery metrics"""
        return {
            "english_projects_delivered": self.english_projects_delivered,
            "international_clients_served": self.international_clients_served,
            "training_sessions_conducted": self.training_sessions_conducted,
            "best_practices_implemented": self.best_practices_implemented,
            "go_lives_supported": self.go_lives_supported,
            "active_en_clients": list(self.active_en_clients.keys()),
            "global_implementations": list(self.global_implementations.keys()),
            "agent": self.name
        } 