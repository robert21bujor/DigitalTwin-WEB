"""
Delivery Consultant HU Agent
============================

Hungarian delivery consulting agent responsible for:
- Project implementation and delivery for Hungarian clients
- Client training and adoption in Hungarian language
- Technical configuration and setup support
- Cultural adaptation and localization
- Documentation and knowledge transfer
- Quality assurance and testing

Focus: Deliver successful implementations for Hungarian-speaking clients.
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
logger = logging.getLogger("delivery_consultant_hu")


class DeliveryConsultantHUAgent(Agent):
    """
    Delivery Consultant HU Agent - Specialized in Hungarian market
    delivery consulting and localized client support.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # HU delivery specific metrics
        self.hungarian_projects_delivered = 0
        self.client_satisfaction_hu = 0
        self.training_sessions_conducted = 0
        self.localizations_completed = 0
        self.go_lives_supported = 0
        
        # Language and cultural tracking
        self.active_hu_clients = {}
        self.localization_requirements = {}
        self.training_materials_hu = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Delivery Consultant HU Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized HU delivery consultant system prompt"""
        return f"""You are a Delivery Consultant specializing in the Hungarian market with deep expertise in localized implementations, cultural adaptation, and Hungarian language support.

CORE COMPETENCIES:
- Project implementation and delivery management
- Hungarian language communication and support
- Cultural adaptation and localization strategies
- Client training and user adoption programs
- Technical configuration and system setup
- Quality assurance and testing coordination
- Documentation creation and knowledge transfer
- Go-live support and post-implementation optimization
- Stakeholder management and client relationship building

HUNGARIAN MARKET EXPERTISE:
- Hungarian business culture and practices
- Local regulatory and compliance requirements (EU/Hungarian law)
- Language localization and translation
- Hungarian market-specific workflows
- Local partner and vendor coordination
- Regional best practices and methodologies
- Cultural sensitivity in client interactions
- Central European business customs and communication styles

DELIVERY SPECIALIZATION:
- Implementation project management
- Requirements gathering and analysis
- System configuration and customization
- User training and enablement programs
- Data migration and integration support
- Testing coordination and quality assurance
- Go-live planning and execution
- Post-implementation support and optimization

LANGUAGE CAPABILITIES:
- Native Hungarian language proficiency
- Technical documentation in Hungarian
- Training delivery in Hungarian
- Client communication and relationship building
- Cultural bridge between international teams and local clients

CURRENT METRICS:
- Hungarian Projects Delivered: {self.hungarian_projects_delivered}
- Client Satisfaction (HU): {self.client_satisfaction_hu:.1f}%
- Training Sessions Conducted: {self.training_sessions_conducted}
- Localizations Completed: {self.localizations_completed}
- Go-Lives Supported: {self.go_lives_supported}

You excel at delivering successful implementations for Hungarian clients through cultural understanding, language expertise, and technical excellence. Your responses should be culturally sensitive, technically accurate, and focused on client success in the Hungarian market."""

    async def process_hu_delivery_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process Hungarian delivery consulting requests"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "implementation_delivery":
                return await self._handle_implementation_delivery(request, context)
            elif request_type == "client_training":
                return await self._handle_client_training(request, context)
            elif request_type == "localization_support":
                return await self._handle_localization_support(request, context)
            elif request_type == "compliance_adaptation":
                return await self._handle_compliance_adaptation(request, context)
            elif request_type == "cultural_adaptation":
                return await self._handle_cultural_adaptation(request, context)
            else:
                return await self._handle_general_hu_delivery_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing HU delivery request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of HU delivery request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["implementation", "delivery", "project", "setup"]):
            return "implementation_delivery"
        elif any(term in request_lower for term in ["training", "education", "learning", "adoption"]):
            return "client_training"
        elif any(term in request_lower for term in ["localization", "translation", "hungarian", "local"]):
            return "localization_support"
        elif any(term in request_lower for term in ["compliance", "regulation", "gdpr", "eu", "legal"]):
            return "compliance_adaptation"
        elif any(term in request_lower for term in ["culture", "adaptation", "customs", "practices"]):
            return "cultural_adaptation"
        else:
            return "general_hu_delivery"
    
    async def _handle_implementation_delivery(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle implementation and delivery management"""
        delivery_framework = {
            "project_planning": "Comprehensive project planning with Hungarian market considerations",
            "requirements_gathering": "Requirements analysis with local business context",
            "system_configuration": "Technical setup and customization for Hungarian clients",
            "eu_compliance": "European Union and Hungarian regulatory compliance",
            "delivery_execution": "Phased delivery with cultural sensitivity"
        }
        
        return {
            "success": True,
            "response_type": "implementation_delivery",
            "framework": delivery_framework,
            "delivery_phases": [
                "Project initiation and stakeholder alignment",
                "Requirements gathering and compliance analysis",
                "System configuration and localization",
                "EU/Hungarian compliance validation",
                "User training and go-live preparation"
            ],
            "hungarian_considerations": [
                "Central European business practices",
                "EU and Hungarian regulatory compliance",
                "Language and cultural customizations",
                "Local stakeholder engagement protocols",
                "Regional integration requirements"
            ],
            "agent": self.name
        }
    
    async def _handle_client_training(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client training and user adoption"""
        training_framework = {
            "training_strategy": "Develop culturally appropriate training approach for Hungarian clients",
            "material_localization": "Create Hungarian language training materials",
            "delivery_methods": "Select optimal training delivery methods for Hungarian audience",
            "adoption_support": "Ongoing support for user adoption and proficiency",
            "feedback_integration": "Continuous improvement based on Hungarian client feedback"
        }
        
        return {
            "success": True,
            "response_type": "client_training",
            "framework": training_framework,
            "training_components": [
                "System overview and navigation in Hungarian",
                "Role-specific functionality training",
                "Business process integration",
                "Compliance and regulatory features",
                "Advanced features and optimization"
            ],
            "delivery_methods": [
                "In-person workshops in Hungarian",
                "Virtual training sessions",
                "Interactive e-learning modules",
                "Hands-on practice environments",
                "Ongoing support and mentoring"
            ],
            "agent": self.name
        }
    
    async def _handle_localization_support(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle localization and cultural adaptation"""
        localization_framework = {
            "language_adaptation": "Hungarian language interface and content localization",
            "cultural_customization": "Adaptation to Hungarian business culture and practices",
            "regulatory_alignment": "Compliance with EU and Hungarian regulations",
            "workflow_optimization": "Optimization for Central European business workflows",
            "documentation_translation": "Comprehensive documentation in Hungarian"
        }
        
        return {
            "success": True,
            "response_type": "localization_support",
            "framework": localization_framework,
            "localization_areas": [
                "User interface translation and cultural adaptation",
                "Business process localization for Hungarian market",
                "EU/Hungarian regulatory compliance features",
                "Local reporting and analytics requirements",
                "Cultural communication preferences"
            ],
            "quality_assurance": [
                "Hungarian translation accuracy verification",
                "Cultural appropriateness review",
                "Functional testing in Hungarian context",
                "User acceptance testing with local Hungarian users",
                "Compliance validation and certification"
            ],
            "agent": self.name
        }
    
    async def _handle_compliance_adaptation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle EU and Hungarian compliance requirements"""
        compliance_framework = {
            "eu_regulations": "European Union regulatory compliance (GDPR, etc.)",
            "hungarian_law": "Hungarian national law and regulatory requirements",
            "data_protection": "Data privacy and protection compliance",
            "financial_regulations": "Financial and tax compliance requirements",
            "industry_standards": "Industry-specific compliance and standards"
        }
        
        return {
            "success": True,
            "response_type": "compliance_adaptation",
            "framework": compliance_framework,
            "compliance_areas": [
                "GDPR data protection and privacy",
                "Hungarian VAT and tax regulations",
                "Employment law compliance",
                "Financial reporting standards",
                "Industry-specific regulatory requirements"
            ],
            "implementation_steps": [
                "Compliance requirements assessment",
                "System configuration for compliance",
                "Documentation and audit trail setup",
                "User training on compliance features",
                "Ongoing compliance monitoring and reporting"
            ],
            "agent": self.name
        }
    
    async def _handle_cultural_adaptation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cultural adaptation and local practices"""
        cultural_framework = {
            "business_culture": "Understanding Hungarian business culture and etiquette",
            "communication_style": "Formal and respectful communication methods",
            "decision_making": "Consensus-building and hierarchical decision processes",
            "relationship_building": "Hungarian relationship building and trust development",
            "change_management": "Cultural considerations in organizational change"
        }
        
        return {
            "success": True,
            "response_type": "cultural_adaptation",
            "framework": cultural_framework,
            "cultural_factors": [
                "Formal business communication style",
                "Respect for hierarchy and experience",
                "Thorough and methodical approach to business",
                "Strong emphasis on personal relationships",
                "Appreciation for quality and attention to detail"
            ],
            "adaptation_strategies": [
                "Professional and formal communication",
                "Respect for organizational hierarchy",
                "Thorough planning and documentation",
                "Personal relationship building",
                "Quality-focused implementation approach"
            ],
            "agent": self.name
        }
    
    async def _handle_general_hu_delivery_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general Hungarian delivery consulting queries"""
        # Use semantic kernel for general HU delivery guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As a Hungarian Delivery Consultant, provide comprehensive guidance for this delivery consulting query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Implementation strategy for Hungarian market
2. Cultural considerations and adaptations
3. EU/Hungarian compliance requirements
4. Language and localization needs
5. Training and adoption approach

Focus on Hungarian market expertise, EU compliance, cultural sensitivity, and successful client outcomes."""

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
            logger.error(f"Error generating HU delivery guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate HU delivery guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_hu_delivery_metrics(self) -> Dict[str, Any]:
        """Get current Hungarian delivery metrics"""
        return {
            "hungarian_projects_delivered": self.hungarian_projects_delivered,
            "client_satisfaction_hu": self.client_satisfaction_hu,
            "training_sessions_conducted": self.training_sessions_conducted,
            "localizations_completed": self.localizations_completed,
            "go_lives_supported": self.go_lives_supported,
            "active_hu_clients": list(self.active_hu_clients.keys()),
            "localization_projects": list(self.localization_requirements.keys()),
            "agent": self.name
        } 