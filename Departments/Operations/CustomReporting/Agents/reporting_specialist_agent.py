"""
Reporting Specialist Agent
==========================

Technical reporting and data analysis specialist responsible for:
- Dashboard and report development
- Data visualization and storytelling
- SQL query development and optimization
- Automated reporting solutions
- Data quality validation and testing
- Technical documentation and training

Focus: Deliver high-quality reports and dashboards through technical expertise and analytical skills.
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
logger = logging.getLogger("reporting_specialist")


class ReportingSpecialistAgent(Agent):
    """
    Reporting Specialist Agent - Technical report development
    and data analysis expertise.
    """
    
    def __init__(self, name: str, role: str, kernel: sk.Kernel):
        super().__init__(
            name=name,
            role=role,
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel
        )
        
        # Reporting specialist specific metrics
        self.reports_developed = 0
        self.dashboards_created = 0
        self.sql_queries_optimized = 0
        self.data_validations_performed = 0
        self.automated_solutions_implemented = 0
        
        # Technical tracking
        self.active_developments = {}
        self.technical_solutions = {}
        self.data_sources = {}
        
        # Set specialized system prompt
        self.system_prompt = self._create_system_prompt()
        
        logger.info(f"Reporting Specialist Agent initialized: {self.name}")
    
    def _create_system_prompt(self) -> str:
        """Create specialized Reporting Specialist system prompt"""
        return f"""You are a Reporting Specialist with deep expertise in technical report development, data analysis, and business intelligence implementation.

CORE COMPETENCIES:
- Dashboard and report development
- Data visualization and storytelling
- SQL query development and optimization
- Automated reporting solution implementation
- Data quality validation and testing
- Technical documentation and user training
- Database design and data modeling
- ETL processes and data pipeline development
- Business intelligence tool configuration

TECHNICAL EXPERTISE:
- Advanced SQL and database querying
- Data visualization tools (Tableau, Power BI, etc.)
- Reporting platforms and frameworks
- Data warehouse and analytics technologies
- Programming languages for data analysis (Python, R)
- Web technologies for dashboard development
- API integration and data connectivity
- Performance optimization and troubleshooting

ANALYTICAL SKILLS:
- Statistical analysis and data interpretation
- Data quality assessment and cleansing
- Business requirements translation to technical solutions
- KPI definition and measurement methodology
- Trend analysis and pattern recognition
- Data modeling and relationship analysis
- Automated alerting and monitoring setup
- User acceptance testing and validation

COMMUNICATION STYLE:
- Technical precision with business clarity
- User-focused documentation and training
- Problem-solving and troubleshooting approach
- Collaborative development methodology
- Quality-focused delivery standards

CURRENT METRICS:
- Reports Developed: {self.reports_developed}
- Dashboards Created: {self.dashboards_created}
- SQL Queries Optimized: {self.sql_queries_optimized}
- Data Validations Performed: {self.data_validations_performed}
- Automated Solutions: {self.automated_solutions_implemented}

You excel at transforming business requirements into technical reporting solutions, ensuring data accuracy and quality, and delivering user-friendly analytics tools. Your responses should be technically accurate, detail-oriented, and focused on practical implementation."""

    async def process_specialist_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process reporting specialist requests"""
        try:
            # Analyze request type
            request_type = self._analyze_request_type(request)
            
            if request_type == "report_development":
                return await self._handle_report_development(request, context)
            elif request_type == "dashboard_creation":
                return await self._handle_dashboard_creation(request, context)
            elif request_type == "data_analysis":
                return await self._handle_data_analysis(request, context)
            elif request_type == "automation_development":
                return await self._handle_automation_development(request, context)
            elif request_type == "data_quality":
                return await self._handle_data_quality(request, context)
            else:
                return await self._handle_general_specialist_query(request, context)
                
        except Exception as e:
            logger.error(f"Error processing specialist request: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _analyze_request_type(self, request: str) -> str:
        """Analyze the type of specialist request"""
        request_lower = request.lower()
        
        if any(term in request_lower for term in ["report", "development", "create", "build"]):
            return "report_development"
        elif any(term in request_lower for term in ["dashboard", "visualization", "chart", "graph"]):
            return "dashboard_creation"
        elif any(term in request_lower for term in ["analysis", "data", "sql", "query"]):
            return "data_analysis"
        elif any(term in request_lower for term in ["automation", "automated", "schedule", "pipeline"]):
            return "automation_development"
        elif any(term in request_lower for term in ["quality", "validation", "testing", "accuracy"]):
            return "data_quality"
        else:
            return "general_specialist"
    
    async def _handle_report_development(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom report development"""
        development_framework = {
            "requirements_analysis": "Analyze business requirements and specifications",
            "data_source_mapping": "Identify and map required data sources",
            "query_development": "Develop optimized SQL queries and data logic",
            "report_design": "Create user-friendly report layout and formatting",
            "testing_validation": "Perform comprehensive testing and validation"
        }
        
        return {
            "success": True,
            "response_type": "report_development",
            "framework": development_framework,
            "development_phases": [
                "Requirements gathering and analysis",
                "Data source identification and mapping",
                "Query development and optimization",
                "Report layout and formatting design",
                "Testing, validation, and user acceptance"
            ],
            "technical_considerations": [
                "Data accuracy and integrity",
                "Performance and query optimization",
                "User experience and usability",
                "Scalability and maintainability",
                "Security and access controls"
            ],
            "agent": self.name
        }
    
    async def _handle_dashboard_creation(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dashboard creation and visualization"""
        creation_framework = {
            "design_planning": "Plan dashboard layout and visualization strategy",
            "data_preparation": "Prepare and structure data for visualization",
            "visualization_development": "Create charts, graphs, and interactive elements",
            "interactivity_implementation": "Implement filters, drill-downs, and navigation",
            "performance_optimization": "Optimize loading speed and responsiveness"
        }
        
        return {
            "success": True,
            "response_type": "dashboard_creation",
            "framework": creation_framework,
            "visualization_types": [
                "KPI scorecards and metrics displays",
                "Trend analysis and time-series charts",
                "Comparative analysis and benchmarking",
                "Geographic and spatial visualizations",
                "Interactive filters and drill-down capabilities"
            ],
            "best_practices": [
                "Choose appropriate chart types for data",
                "Maintain consistent color schemes and styling",
                "Optimize for different screen sizes",
                "Implement intuitive navigation and interactions",
                "Ensure fast loading and responsive performance"
            ],
            "agent": self.name
        }
    
    async def _handle_data_analysis(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data analysis and SQL development"""
        analysis_framework = {
            "data_exploration": "Explore and understand data structure and relationships",
            "query_development": "Develop complex SQL queries for analysis",
            "statistical_analysis": "Perform statistical analysis and calculations",
            "pattern_identification": "Identify trends, patterns, and anomalies",
            "insights_documentation": "Document findings and analytical insights"
        }
        
        return {
            "success": True,
            "response_type": "data_analysis",
            "framework": analysis_framework,
            "analysis_types": [
                "Descriptive statistics and summary analysis",
                "Trend analysis and time-series evaluation",
                "Comparative analysis and benchmarking",
                "Correlation and relationship analysis",
                "Anomaly detection and outlier identification"
            ],
            "technical_methods": [
                "Advanced SQL queries and joins",
                "Window functions and analytical queries",
                "Statistical functions and calculations",
                "Data aggregation and grouping",
                "Performance optimization techniques"
            ],
            "agent": self.name
        }
    
    async def _handle_automation_development(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle automation and scheduling development"""
        automation_framework = {
            "process_analysis": "Analyze manual processes for automation opportunities",
            "solution_design": "Design automated workflow and scheduling",
            "implementation": "Implement automated data pipelines and reports",
            "monitoring_setup": "Set up monitoring and error handling",
            "maintenance_planning": "Plan ongoing maintenance and updates"
        }
        
        return {
            "success": True,
            "response_type": "automation_development",
            "framework": automation_framework,
            "automation_areas": [
                "Scheduled report generation and distribution",
                "Data refresh and update processes",
                "Automated alerting and notifications",
                "Data validation and quality checks",
                "Performance monitoring and optimization"
            ],
            "implementation_steps": [
                "Identify automation requirements and scope",
                "Design automated workflow and dependencies",
                "Develop and test automation scripts",
                "Implement scheduling and monitoring",
                "Document processes and maintenance procedures"
            ],
            "agent": self.name
        }
    
    async def _handle_data_quality(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data quality validation and testing"""
        quality_framework = {
            "quality_assessment": "Assess current data quality and identify issues",
            "validation_rules": "Define data validation rules and standards",
            "testing_procedures": "Implement comprehensive testing procedures",
            "monitoring_setup": "Set up ongoing data quality monitoring",
            "improvement_planning": "Plan data quality improvement initiatives"
        }
        
        return {
            "success": True,
            "response_type": "data_quality",
            "framework": quality_framework,
            "quality_dimensions": [
                "Accuracy: Data correctness and precision",
                "Completeness: Data availability and coverage",
                "Consistency: Data uniformity across sources",
                "Timeliness: Data freshness and currency",
                "Validity: Data conformance to business rules"
            ],
            "validation_methods": [
                "Automated data validation rules",
                "Statistical analysis and outlier detection",
                "Cross-reference and reconciliation checks",
                "Business rule validation and testing",
                "User acceptance testing and feedback"
            ],
            "agent": self.name
        }
    
    async def _handle_general_specialist_query(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general reporting specialist queries"""
        # Use semantic kernel for general specialist guidance
        settings = PromptExecutionSettings(
            service_id="default",
            max_tokens=1000,
            temperature=0.7
        )
        
        prompt = f"""As a Reporting Specialist with technical expertise, provide comprehensive guidance for this reporting query:

Query: {request}

Context: {context if context else 'No additional context provided'}

Please provide:
1. Technical solution recommendations
2. Implementation approach and methodology
3. Data requirements and considerations
4. Quality assurance and testing strategies
5. Performance optimization techniques

Focus on technical accuracy, practical implementation, and high-quality deliverables."""

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
            logger.error(f"Error generating specialist guidance: {e}")
            return {
                "success": False,
                "error": f"Could not generate specialist guidance: {str(e)}",
                "agent": self.name
            }
    
    def get_specialist_metrics(self) -> Dict[str, Any]:
        """Get current reporting specialist metrics"""
        return {
            "reports_developed": self.reports_developed,
            "dashboards_created": self.dashboards_created,
            "sql_queries_optimized": self.sql_queries_optimized,
            "data_validations_performed": self.data_validations_performed,
            "automated_solutions_implemented": self.automated_solutions_implemented,
            "active_developments": list(self.active_developments.keys()),
            "technical_solutions": list(self.technical_solutions.keys()),
            "agent": self.name
        } 