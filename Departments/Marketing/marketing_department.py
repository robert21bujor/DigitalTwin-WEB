"""
Marketing Department
Main entry point for the Marketing department with all sub-divisions
"""

import logging
from typing import Dict, Any

import semantic_kernel as sk
from Core.Departments.department_base import BaseDepartment

logger = logging.getLogger(__name__)


class MarketingDepartment(BaseDepartment):
    """
    Marketing Department with Content, Digital, and Product Marketing divisions
    """
    
    def __init__(self, kernel: sk.Kernel):
        super().__init__("Marketing", kernel)
        
        # Marketing-specific attributes
        self.divisions = {
            "content_marketing": [],
            "digital_marketing": [],
            "product_marketing": []
        }
        
    def setup_department(self) -> bool:
        """
        Marketing-specific setup logic
        """
        try:
            logger.info("Setting up Marketing department...")
            
            # Organize agents by division
            self._organize_agents_by_division()
            
            # Setup division-specific configurations
            self._setup_division_configs()
            
            # Initialize marketing workflows
            self._setup_marketing_workflows()
            
            logger.info("✅ Marketing department setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Marketing department setup failed: {e}")
            return False
    
    def _organize_agents_by_division(self):
        """Organize agents into their respective divisions"""
        for agent in self.agents:
            agent_name = agent.name.lower()
            
            # Content Marketing agents
            if any(keyword in agent_name for keyword in ['content', 'brand', 'social', 'community']):
                self.divisions["content_marketing"].append(agent)
                agent.division = "content_marketing"
                
            # Digital Marketing agents  
            elif any(keyword in agent_name for keyword in ['seo', 'sem', 'landing', 'analytics', 'funnel']):
                self.divisions["digital_marketing"].append(agent)
                agent.division = "digital_marketing"
                
            # Product Marketing agents
            elif any(keyword in agent_name for keyword in ['positioning', 'persona', 'gtm', 'competitor', 'launch']):
                self.divisions["product_marketing"].append(agent)
                agent.division = "product_marketing"
        
        # Log division organization
        for division, agents in self.divisions.items():
            logger.info(f"📊 {division.replace('_', ' ').title()}: {len(agents)} agents")
    
    def _setup_division_configs(self):
        """Setup configurations specific to each marketing division"""
        
        # Content Marketing config
        self.content_config = {
            "brand_guidelines": True,
            "content_calendar": True,
            "social_scheduling": True,
            "community_guidelines": True
        }
        
        # Digital Marketing config
        self.digital_config = {
            "tracking_setup": True,
            "conversion_goals": True,
            "ab_testing": True,
            "performance_monitoring": True
        }
        
        # Product Marketing config
        self.product_config = {
            "market_research": True,
            "competitive_intelligence": True,
            "launch_processes": True,
            "positioning_framework": True
        }
        
        logger.info("📋 Division configurations initialized")
    
    def _setup_marketing_workflows(self):
        """Setup marketing-specific workflows and processes"""
        
        # Define cross-division workflows
        self.workflows = {
            "product_launch": {
                "stages": ["research", "positioning", "content", "digital", "launch"],
                "agents_involved": ["competitor", "positioning", "content", "seo", "launch"]
            },
            "campaign_creation": {
                "stages": ["strategy", "content", "digital", "analytics"],
                "agents_involved": ["brand", "content", "sem", "analytics"]
            },
            "market_analysis": {
                "stages": ["research", "competitive", "positioning"],
                "agents_involved": ["persona", "competitor", "positioning"]
            }
        }
        
        logger.info("🔄 Marketing workflows configured")
    
    def get_division_agents(self, division: str) -> list:
        """Get agents for a specific division"""
        return self.divisions.get(division, [])
    
    def get_marketing_metrics(self) -> Dict[str, Any]:
        """Get marketing department metrics and status"""
        return {
            "total_agents": len(self.agents),
            "divisions": {
                division: len(agents) for division, agents in self.divisions.items()
            },
            "workflows_active": len(self.workflows),
            "specialized_skills": [
                "Content Creation", "Brand Strategy", "SEO/SEM", 
                "Analytics", "Product Positioning", "Market Research"
            ]
        }
    
    def health_check(self) -> bool:
        """Marketing department health check"""
        base_health = super().health_check()
        
        # Additional marketing-specific checks
        divisions_healthy = all(len(agents) > 0 for agents in self.divisions.values())
        workflows_configured = len(self.workflows) > 0
        
        return base_health and divisions_healthy and workflows_configured
    
    def get_info(self) -> Dict[str, Any]:
        """Enhanced info with marketing-specific details"""
        base_info = super().get_info()
        base_info.update({
            "divisions": {
                division: [agent.name for agent in agents] 
                for division, agents in self.divisions.items()
            },
            "workflows": list(self.workflows.keys()),
            "marketing_metrics": self.get_marketing_metrics()
        })
        return base_info 