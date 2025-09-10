"""
Legal Agent
===========

Comprehensive legal support agent responsible for:
- Contract drafting and review
- Regulatory compliance monitoring
- Risk assessment and mitigation
- Intellectual property protection
- Dispute resolution and negotiation
- Legal documentation and governance
- Corporate law and business compliance
- Data protection and privacy compliance

Focus: Ensure legal compliance and protect organizational interests through expert legal guidance.
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
logger = logging.getLogger("legal_agent")


class LegalAgent(Agent):
    """
    Legal Agent - Comprehensive legal support and compliance management
    for organizational protection and regulatory adherence.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # Legal specific metrics
        self.contracts_reviewed = 0
        self.compliance_assessments_conducted = 0
        self.legal_risks_mitigated = 0
        self.intellectual_property_matters_handled = 0
        self.disputes_resolved = 0
        
        # Legal tracking
        self.active_legal_matters = {}
        self.compliance_frameworks = {}
        self.contract_templates = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Legal Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized Legal system prompt"""
        return f"""You are a Legal Agent with deep expertise in corporate law, contract management, regulatory compliance, and risk mitigation.

CORE COMPETENCIES:
- Contract drafting, review, and negotiation
- Regulatory compliance monitoring and assessment
- Corporate law and business structure guidance
- Risk assessment and legal mitigation strategies
- Intellectual property protection and management
- Dispute resolution and litigation support
- Data protection and privacy compliance (GDPR, CCPA, etc.)
- Employment law and HR compliance
- Commercial law and business transactions

LEGAL EXPERTISE:
- Contract law and commercial agreements
- Corporate governance and compliance frameworks
- Intellectual property law (patents, trademarks, copyrights)
- Data protection and privacy regulations
- Employment and labor law compliance
- International business law and cross-border transactions
- Regulatory compliance across multiple jurisdictions
- Dispute resolution and alternative dispute resolution
- Risk management and legal risk assessment

COMPLIANCE SPECIALIZATION:
- GDPR and international data protection laws
- Industry-specific regulatory compliance
- Corporate governance standards
- Anti-corruption and anti-bribery compliance
- Export control and trade compliance
- Financial services regulations
- Healthcare and medical device regulations
- Environmental and sustainability compliance

COMMUNICATION STYLE:
- Clear and precise legal communication
- Risk-focused analysis and recommendations
- Business-oriented legal guidance
- Proactive compliance monitoring
- Solution-oriented problem solving

CURRENT METRICS:
- Contracts Reviewed: {self.contracts_reviewed}
- Compliance Assessments: {self.compliance_assessments_conducted}
- Legal Risks Mitigated: {self.legal_risks_mitigated}
- IP Matters Handled: {self.intellectual_property_matters_handled}
- Disputes Resolved: {self.disputes_resolved}

You excel at protecting organizational interests through comprehensive legal guidance, ensuring regulatory compliance, and mitigating legal risks. Your responses should be legally sound, practical, and focused on business protection and compliance."""

    async def process_legal_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process legal support requests"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "contract_management":
                return await self._handle_contract_management(request, context)
            elif request_type == "compliance_assessment":
                return await self._handle_compliance_assessment(request, context)
            elif request_type == "risk_mitigation":
                return await self._handle_risk_mitigation(request, context)
            elif request_type == "intellectual_property":
                return await self._handle_intellectual_property(request, context)
            elif request_type == "dispute_resolution":
                return await self._handle_dispute_resolution(request, context)
            else:
                return await self._handle_general_legal_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing legal request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of legal request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["contract", "agreement", "terms", "negotiation"]):
            return "contract_management"
        elif any(term in request_lower for term in ["compliance", "regulation", "regulatory", "gdpr"]):
            return "compliance_assessment"
        elif any(term in request_lower for term in ["risk", "liability", "mitigation", "legal risk"]):
            return "risk_mitigation"
        elif any(term in request_lower for term in ["intellectual property", "patent", "trademark", "copyright", "ip"]):
            return "intellectual_property"
        elif any(term in request_lower for term in ["dispute", "litigation", "conflict", "resolution"]):
            return "dispute_resolution"
        else:
            return "general_legal"
    
    async def _handle_contract_management(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contract drafting, review, and management"""
        contract_framework = {
            "contract_analysis": "Comprehensive review and analysis of contract terms",
            "risk_assessment": "Identification and assessment of contractual risks",
            "negotiation_strategy": "Development of negotiation strategy and key points",
            "compliance_validation": "Ensure compliance with applicable laws and regulations",
            "template_development": "Create standardized contract templates and clauses"
        }
        
        return {
            "success": True,
            "response_type": "contract_management",
            "framework": contract_framework,
            "contract_types": [
                "Service agreements and professional services contracts",
                "Software licensing and technology agreements",
                "Employment contracts and consulting agreements",
                "Partnership and joint venture agreements",
                "Non-disclosure and confidentiality agreements"
            ],
            "review_checklist": [
                "Terms and conditions clarity and enforceability",
                "Liability limitations and indemnification clauses",
                "Intellectual property rights and ownership",
                "Termination conditions and dispute resolution",
                "Compliance with applicable laws and regulations"
            ],
            "agent": self.name
        }
    
    async def _handle_compliance_assessment(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle regulatory compliance assessment and monitoring"""
        compliance_framework = {
            "regulatory_mapping": "Identify applicable regulations and compliance requirements",
            "gap_analysis": "Assess current compliance status and identify gaps",
            "framework_development": "Develop compliance frameworks and procedures",
            "monitoring_setup": "Implement ongoing compliance monitoring and reporting",
            "training_programs": "Design compliance training and awareness programs"
        }
        
        return {
            "success": True,
            "response_type": "compliance_assessment",
            "framework": compliance_framework,
            "compliance_areas": [
                "Data protection and privacy (GDPR, CCPA, PIPEDA)",
                "Employment law and workplace regulations",
                "Industry-specific regulatory requirements",
                "International trade and export controls",
                "Anti-corruption and anti-bribery compliance"
            ],
            "assessment_process": [
                "Regulatory requirement identification and mapping",
                "Current state assessment and gap analysis",
                "Risk prioritization and impact assessment",
                "Compliance program design and implementation",
                "Ongoing monitoring and continuous improvement"
            ],
            "agent": self.name
        }
    
    async def _handle_risk_mitigation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle legal risk assessment and mitigation"""
        risk_framework = {
            "risk_identification": "Systematic identification of legal and regulatory risks",
            "impact_assessment": "Analysis of potential impact and likelihood",
            "mitigation_strategies": "Development of risk mitigation and control measures",
            "monitoring_controls": "Implementation of ongoing risk monitoring",
            "contingency_planning": "Preparation of legal contingency and response plans"
        }
        
        return {
            "success": True,
            "response_type": "risk_mitigation",
            "framework": risk_framework,
            "risk_categories": [
                "Contractual and commercial risks",
                "Regulatory and compliance risks",
                "Intellectual property and trade secret risks",
                "Employment and labor law risks",
                "Data protection and privacy risks"
            ],
            "mitigation_strategies": [
                "Legal structure optimization and protection",
                "Insurance coverage and risk transfer",
                "Contract terms and liability limitations",
                "Compliance program implementation",
                "Crisis management and response planning"
            ],
            "agent": self.name
        }
    
    async def _handle_intellectual_property(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle intellectual property protection and management"""
        ip_framework = {
            "ip_audit": "Comprehensive audit of intellectual property assets",
            "protection_strategy": "Development of IP protection and registration strategy",
            "licensing_management": "Management of IP licensing and commercialization",
            "infringement_monitoring": "Monitoring for IP infringement and enforcement",
            "portfolio_optimization": "Optimization of IP portfolio and maintenance"
        }
        
        return {
            "success": True,
            "response_type": "intellectual_property",
            "framework": ip_framework,
            "ip_types": [
                "Patents and patent applications",
                "Trademarks and service marks",
                "Copyrights and creative works",
                "Trade secrets and confidential information",
                "Domain names and digital assets"
            ],
            "protection_measures": [
                "Patent filing and prosecution strategies",
                "Trademark registration and enforcement",
                "Copyright protection and licensing",
                "Trade secret identification and protection",
                "IP licensing and commercialization agreements"
            ],
            "agent": self.name
        }
    
    async def _handle_dispute_resolution(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dispute resolution and litigation support"""
        dispute_framework = {
            "dispute_analysis": "Comprehensive analysis of dispute facts and legal issues",
            "strategy_development": "Development of dispute resolution strategy",
            "negotiation_management": "Management of settlement negotiations",
            "alternative_dispute_resolution": "Mediation and arbitration coordination",
            "litigation_support": "Litigation management and court proceedings support"
        }
        
        return {
            "success": True,
            "response_type": "dispute_resolution",
            "framework": dispute_framework,
            "resolution_methods": [
                "Direct negotiation and settlement discussions",
                "Mediation with neutral third-party mediator",
                "Arbitration proceedings and award enforcement",
                "Litigation in appropriate courts and jurisdictions",
                "Alternative dispute resolution mechanisms"
            ],
            "resolution_process": [
                "Dispute assessment and legal merit evaluation",
                "Strategy development and approach selection",
                "Evidence gathering and case preparation",
                "Resolution proceedings and advocacy",
                "Settlement implementation and enforcement"
            ],
            "agent": self.name
        }
    
    async def _handle_general_legal_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general legal queries and guidance"""
        # Use semantic kernel for general legal guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As a Legal Agent with comprehensive legal expertise, provide guidance for this legal query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Legal analysis and risk assessment
2. Applicable laws and regulations
3. Recommended actions and strategies
4. Compliance considerations
5. Risk mitigation measures

Focus on practical legal guidance, regulatory compliance, and organizational protection. Note: This is general guidance and not formal legal advice."""

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
                "disclaimer": "This guidance is for informational purposes and does not constitute formal legal advice",
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"Error generating legal guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate legal guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_legal_metrics(self) -> Dict[str, Any]:
        """Get current legal metrics"""
        return {
            "contracts_reviewed": self.contracts_reviewed,
            "compliance_assessments_conducted": self.compliance_assessments_conducted,
            "legal_risks_mitigated": self.legal_risks_mitigated,
            "intellectual_property_matters_handled": self.intellectual_property_matters_handled,
            "disputes_resolved": self.disputes_resolved,
            "active_legal_matters": list(self.active_legal_matters.keys()),
            "compliance_frameworks": list(self.compliance_frameworks.keys()),
            "agent": self.name
        } 