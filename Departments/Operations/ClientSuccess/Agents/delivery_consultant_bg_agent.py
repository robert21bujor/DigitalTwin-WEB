"""
Delivery Consultant BG Agent
============================

Bulgarian delivery consulting agent responsible for:
- Project implementation and delivery for Bulgarian clients
- Client training and adoption in Bulgarian language
- Technical configuration and setup support
- Cultural adaptation and localization
- Documentation and knowledge transfer
- Quality assurance and testing

Focus: Deliver successful implementations for Bulgarian-speaking clients.
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
logger = logging.getLogger("delivery_consultant_bg")


class DeliveryConsultantBGAgent(Agent):
    """
    Delivery Consultant BG Agent - Specialized in Bulgarian market
    delivery consulting and localized client support.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # BG delivery specific metrics
        self.bulgarian_projects_delivered = 0
        self.client_satisfaction_bg = 0
        self.training_sessions_conducted = 0
        self.localizations_completed = 0
        self.go_lives_supported = 0
        
        # Language and cultural tracking
        self.active_bg_clients = {}
        self.localization_requirements = {}
        self.training_materials_bg = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Delivery Consultant BG Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized BG delivery consultant system prompt"""
        return f"""You are a Delivery Consultant specializing in the Bulgarian market with deep expertise in localized implementations, cultural adaptation, and Bulgarian language support.

CORE COMPETENCIES:
- Project implementation and delivery management
- Bulgarian language communication and support
- Cultural adaptation and localization strategies
- Client training and user adoption programs
- Technical configuration and system setup
- Quality assurance and testing coordination
- Documentation creation and knowledge transfer
- Go-live support and post-implementation optimization
- Stakeholder management and client relationship building

BULGARIAN MARKET EXPERTISE:
- Bulgarian business culture and practices
- Local regulatory and compliance requirements
- Language localization and translation
- Bulgarian market-specific workflows
- Local partner and vendor coordination
- Regional best practices and methodologies
- Cultural sensitivity in client interactions
- Local business customs and communication styles

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
- Native Bulgarian language proficiency
- Technical documentation in Bulgarian
- Training delivery in Bulgarian
- Client communication and relationship building
- Cultural bridge between international teams and local clients

CURRENT METRICS:
- Bulgarian Projects Delivered: {self.bulgarian_projects_delivered}
- Client Satisfaction (BG): {self.client_satisfaction_bg:.1f}%
- Training Sessions Conducted: {self.training_sessions_conducted}
- Localizations Completed: {self.localizations_completed}
- Go-Lives Supported: {self.go_lives_supported}

You excel at delivering successful implementations for Bulgarian clients through cultural understanding, language expertise, and technical excellence. Your responses should be culturally sensitive, technically accurate, and focused on client success in the Bulgarian market."""

    async def process_bg_delivery_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process Bulgarian delivery consulting requests"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "implementation_delivery":
                return await self._handle_implementation_delivery(request, context)
            elif request_type == "client_training":
                return await self._handle_client_training(request, context)
            elif request_type == "localization_support":
                return await self._handle_localization_support(request, context)
            elif request_type == "go_live_support":
                return await self._handle_go_live_support(request, context)
            elif request_type == "cultural_adaptation":
                return await self._handle_cultural_adaptation(request, context)
            else:
                return await self._handle_general_bg_delivery_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing BG delivery request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of BG delivery request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["implementation", "delivery", "project", "setup"]):
            return "implementation_delivery"
        elif any(term in request_lower for term in ["training", "education", "learning", "adoption"]):
            return "client_training"
        elif any(term in request_lower for term in ["localization", "translation", "bulgarian", "local"]):
            return "localization_support"
        elif any(term in request_lower for term in ["go-live", "launch", "deployment", "production"]):
            return "go_live_support"
        elif any(term in request_lower for term in ["culture", "adaptation", "customs", "practices"]):
            return "cultural_adaptation"
        else:
            return "general_bg_delivery"
    
    async def _handle_implementation_delivery(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle implementation and delivery management"""
        delivery_framework = {
            "project_planning": "Comprehensive project planning with Bulgarian market considerations",
            "requirements_gathering": "Requirements analysis with local business context",
            "system_configuration": "Technical setup and customization for Bulgarian clients",
            "testing_coordination": "Quality assurance with local testing scenarios",
            "delivery_execution": "Phased delivery with cultural sensitivity"
        }
        
        return {
            "success": True,
            "response_type": "implementation_delivery",
            "framework": delivery_framework,
            "delivery_phases": [
                "Project initiation and stakeholder alignment",
                "Requirements gathering and localization analysis",
                "System configuration and customization",
                "Testing and quality assurance",
                "User training and go-live preparation"
            ],
            "bulgarian_considerations": [
                "Local business process alignment",
                "Regulatory compliance requirements",
                "Language and cultural customizations",
                "Local stakeholder engagement",
                "Regional best practice integration"
            ],
            "agent": self.name
        }
    
    async def _handle_client_training(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client training and user adoption"""
        training_framework = {
            "training_strategy": "Develop culturally appropriate training approach",
            "material_localization": "Create Bulgarian language training materials",
            "delivery_methods": "Select optimal training delivery methods for Bulgarian audience",
            "adoption_support": "Ongoing support for user adoption and proficiency",
            "feedback_integration": "Continuous improvement based on Bulgarian client feedback"
        }
        
        return {
            "success": True,
            "response_type": "client_training",
            "framework": training_framework,
            "training_components": [
                "System overview and navigation",
                "Role-specific functionality training",
                "Business process integration",
                "Troubleshooting and support",
                "Advanced features and optimization"
            ],
            "delivery_methods": [
                "In-person workshops in Bulgarian",
                "Virtual training sessions",
                "Self-paced learning materials",
                "Hands-on practice environments",
                "Ongoing support and Q&A sessions"
            ],
            "agent": self.name
        }
    
    async def _handle_localization_support(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle localization and cultural adaptation"""
        localization_framework = {
            "language_adaptation": "Bulgarian language interface and content localization",
            "cultural_customization": "Adaptation to Bulgarian business culture and practices",
            "regulatory_alignment": "Compliance with Bulgarian regulations and standards",
            "workflow_optimization": "Optimization for local business workflows",
            "documentation_translation": "Comprehensive documentation in Bulgarian"
        }
        
        return {
            "success": True,
            "response_type": "localization_support",
            "framework": localization_framework,
            "localization_areas": [
                "User interface translation and adaptation",
                "Business process localization",
                "Regulatory compliance features",
                "Local reporting and analytics",
                "Cultural communication preferences"
            ],
            "quality_assurance": [
                "Translation accuracy verification",
                "Cultural appropriateness review",
                "Functional testing in Bulgarian context",
                "User acceptance testing with local users",
                "Feedback incorporation and refinement"
            ],
            "agent": self.name
        }
    
    async def _handle_go_live_support(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle go-live and launch support"""
        golive_framework = {
            "launch_planning": "Comprehensive go-live planning with Bulgarian considerations",
            "cutover_execution": "Smooth transition from legacy to new system",
            "support_readiness": "24/7 support availability during launch period",
            "issue_resolution": "Rapid resolution of launch-related issues",
            "stabilization_support": "Post-launch stabilization and optimization"
        }
        
        return {
            "success": True,
            "response_type": "go_live_support",
            "framework": golive_framework,
            "golive_phases": [
                "Pre-launch preparation and readiness verification",
                "System cutover and data migration",
                "User access provisioning and validation",
                "Initial user support and issue resolution",
                "Performance monitoring and optimization"
            ],
            "support_structure": [
                "Dedicated Bulgarian-speaking support team",
                "Extended hours coverage during launch",
                "Escalation procedures and issue tracking",
                "User communication and status updates",
                "Success criteria validation and sign-off"
            ],
            "agent": self.name
        }
    
    async def _handle_cultural_adaptation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cultural adaptation and local practices"""
        cultural_framework = {
            "business_culture": "Understanding and adapting to Bulgarian business culture",
            "communication_style": "Appropriate communication methods and etiquette",
            "decision_making": "Local decision-making processes and hierarchies",
            "relationship_building": "Bulgarian relationship building and trust development",
            "change_management": "Cultural considerations in change management"
        }
        
        return {
            "success": True,
            "response_type": "cultural_adaptation",
            "framework": cultural_framework,
            "cultural_factors": [
                "Hierarchical business structures",
                "Formal communication preferences",
                "Relationship-based business approach",
                "Traditional process respect",
                "Group consensus importance"
            ],
            "adaptation_strategies": [
                "Respectful and formal communication",
                "Relationship building before business",
                "Patient consensus building approach",
                "Cultural sensitivity in training",
                "Local success story integration"
            ],
            "agent": self.name
        }
    
    async def _handle_general_bg_delivery_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general Bulgarian delivery consulting queries"""
        # Use semantic kernel for general BG delivery guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As a Bulgarian Delivery Consultant, provide comprehensive guidance for this delivery consulting query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Implementation strategy for Bulgarian market
2. Cultural considerations and adaptations
3. Language and localization requirements
4. Training and adoption approach
5. Success measurement and optimization

Focus on Bulgarian market expertise, cultural sensitivity, and successful client outcomes."""

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
            logger.error(f"Error generating BG delivery guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate BG delivery guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_bg_delivery_metrics(self) -> Dict[str, Any]:
        """Get current Bulgarian delivery metrics"""
        return {
            "bulgarian_projects_delivered": self.bulgarian_projects_delivered,
            "client_satisfaction_bg": self.client_satisfaction_bg,
            "training_sessions_conducted": self.training_sessions_conducted,
            "localizations_completed": self.localizations_completed,
            "go_lives_supported": self.go_lives_supported,
            "active_bg_clients": list(self.active_bg_clients.keys()),
            "localization_projects": list(self.localization_requirements.keys()),
            "agent": self.name
        } 